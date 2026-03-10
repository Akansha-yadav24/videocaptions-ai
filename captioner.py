"""
captioner.py — Burns styled captions into video using FFmpeg + ASS subtitles.
Supports precise X/Y percentage positioning, font size, color, and typewriter effect.
"""

import os
import shutil
import tempfile
import subprocess
from caption_styles import POSITION_MAP


# ── Time helpers ───────────────────────────────────────────────────────────────

def _fmt_srt(s: float) -> str:
    h = int(s // 3600); m = int((s % 3600) // 60)
    sec = int(s % 60);  ms = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def _srt_to_ass_time(t: str) -> str:
    t = t.strip().replace(",", ".")
    h, m, rest = t.split(":")
    s, frac = rest.split(".")
    cs = frac[:2].ljust(2, "0")
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs}"


# ── SRT writers ────────────────────────────────────────────────────────────────

def _write_srt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{_fmt_srt(seg['start'])} --> {_fmt_srt(seg['end'])}\n{seg['text'].strip()}\n\n")


def _write_typewriter_srt(segments, path, chars_per_sec):
    entries = []
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        start, end = seg["start"], seg["end"]
        total = len(text)
        step  = max(1, total // 60)
        prev_t = start
        for i in range(step, total + step, step):
            i = min(i, total)
            t_end = min(start + i / chars_per_sec, end)
            if t_end <= prev_t:
                t_end = prev_t + 0.05
            entries.append({"start": prev_t, "end": t_end, "text": text[:i]})
            prev_t = t_end
        if entries and entries[-1]["end"] < end:
            entries.append({"start": entries[-1]["end"], "end": end, "text": text})
    with open(path, "w", encoding="utf-8") as f:
        for i, e in enumerate(entries, 1):
            f.write(f"{i}\n{_fmt_srt(e['start'])} --> {_fmt_srt(e['end'])}\n{e['text']}\n\n")


# ── ASS color helpers ──────────────────────────────────────────────────────────

def _hex_to_ass(color: str) -> str:
    named = {"white":"FFFFFF","yellow":"FFFF00","black":"000000",
             "red":"FF0000","green":"00FF00","blue":"0000FF"}
    c = named.get(color.lower().lstrip("#"), color.lstrip("#").lstrip("0x"))
    if len(c) == 6:
        return f"&H00{c[4:6]}{c[2:4]}{c[0:2]}"
    return "&H00FFFFFF"


def _box_ass(bg: str) -> str:
    raw = bg.split("@")[0].replace("0x","").replace("#","").lstrip("0x")
    named = {"black":"000000","white":"FFFFFF"}
    raw = named.get(raw.lower(), raw)
    if len(raw) == 6:
        return f"&H99{raw[4:6]}{raw[2:4]}{raw[0:2]}"
    return "&H99000000"


# ── ASS builder ────────────────────────────────────────────────────────────────

def _srt_to_ass(srt_path, ass_path, font_name, font_size,
                hex_color, bg_ffmpeg, pos_x_pct, pos_y_pct):
    """
    Convert SRT → ASS with custom positioning.

    pos_x_pct / pos_y_pct: 0–100 percentages from top-left.
    We use ASS \an5 (center anchor) + \pos(x,y) override tags
    so the caption center lands exactly at the specified coordinates.

    PlayRes is fixed at 1920x1080; FFmpeg scales the ASS to fit any video.
    """
    PLAY_W, PLAY_H = 1920, 1080
    primary = _hex_to_ass(hex_color)
    back    = _box_ass(bg_ffmpeg)

    # Compute absolute position in PlayRes space
    abs_x = int(PLAY_W * pos_x_pct / 100)
    abs_y = int(PLAY_H * pos_y_pct / 100)

    # ASS alignment: \an5 = center-center anchor (makes x,y the center of the box)
    # This gives pixel-perfect control matching the preview
    pos_tag = f"{{\\an5\\pos({abs_x},{abs_y})}}"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PLAY_W}
PlayResY: {PLAY_H}
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary},&H00FFFFFF,&H00000000,{back},-1,0,0,0,100,100,0,0,3,2,0,5,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()

    lines = [header]
    for block in content.strip().split("\n\n"):
        rows = [r for r in block.strip().split("\n") if r]
        if len(rows) < 3:
            continue
        try:
            s_str, e_str = [x.strip() for x in rows[1].split("-->")]
            s_ass = _srt_to_ass_time(s_str)
            e_ass = _srt_to_ass_time(e_str)
        except Exception:
            continue
        text = r"\N".join(rows[2:])
        lines.append(f"Dialogue: 0,{s_ass},{e_ass},Default,,0,0,0,,{pos_tag}{text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Windows path fix ───────────────────────────────────────────────────────────

def _ffmpeg_filter_path(p: str) -> str:
    """Convert path to FFmpeg filter-safe format (forward slashes, escaped drive colon)."""
    p = p.replace("\\", "/")
    if len(p) > 1 and p[1] == ":":          # Windows drive letter  C:/...
        p = p[0] + "\\:" + p[2:]            # → C\:/...
    return p


# ── Main ───────────────────────────────────────────────────────────────────────

def burn_captions_to_video(
    input_path: str,
    output_path: str,
    segments: list,
    font_name: str,
    font_path,
    color_info: dict,
    position: str = "Bottom",      # kept for CLI / legacy callers
    pos_x_pct: float = 50.0,       # NEW: horizontal %
    pos_y_pct: float = 88.0,       # NEW: vertical %
    typewriter: bool = False,
    typewriter_speed: int = 20,
    font_size: int = 38,
):
    if not segments:
        shutil.copy(input_path, output_path)
        return

    # If called from CLI with position label, convert to pct
    if pos_x_pct == 50.0 and pos_y_pct == 88.0:
        label_to_y = {"Top": 8.0, "Middle": 50.0, "Bottom": 88.0}
        pos_y_pct = label_to_y.get(position, 88.0)

    ass_font   = font_name.replace("-", " ")
    hex_color  = color_info.get("hex", "#FFFFFF")
    bg_ffmpeg  = color_info.get("bg_ffmpeg", "black@0.65")

    tmp_dir  = tempfile.mkdtemp()
    srt_path = os.path.join(tmp_dir, "caps.srt")
    ass_path = os.path.join(tmp_dir, "caps.ass")

    try:
        if typewriter:
            _write_typewriter_srt(segments, srt_path, typewriter_speed)
        else:
            _write_srt(segments, srt_path)

        _srt_to_ass(
            srt_path, ass_path,
            font_name=ass_font,
            font_size=font_size,
            hex_color=hex_color,
            bg_ffmpeg=bg_ffmpeg,
            pos_x_pct=pos_x_pct,
            pos_y_pct=pos_y_pct,
        )

        ass_filter = _ffmpeg_filter_path(ass_path)
        vf = f"subtitles='{ass_filter}'"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]

        print(f"[Captioner] {len(segments)} segments | font={ass_font} {font_size}px | X={pos_x_pct}% Y={pos_y_pct}%")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("[Captioner] FFmpeg stderr:\n", result.stderr[-3000:])
            raise RuntimeError(
                f"FFmpeg failed (exit {result.returncode}).\n\n"
                "Make sure you're using the FULL FFmpeg build (with libass):\n"
                "https://www.gyan.dev/ffmpeg/builds/  →  ffmpeg-release-full.7z"
            )

        print(f"[Captioner] Done → {output_path}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
