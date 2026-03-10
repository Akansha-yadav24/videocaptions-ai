"""
captioner.py — Burns styled captions into video using FFmpeg.

Strategy:
  1. Write segments to a temp SRT file
  2. Convert SRT → ASS (Advanced SubStation Alpha) with custom styling
  3. Use FFmpeg's `subtitles` filter to burn ASS into video

This approach is far more robust on Windows than the drawtext filter chain:
  - No filter-string length limits
  - No Windows backslash path issues in filter strings
  - Full font/color/position control via ASS style header
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
    """00:00:01,234  →  0:00:01.23"""
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


# ── ASS style ──────────────────────────────────────────────────────────────────

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


def _srt_to_ass(srt_path, ass_path, font_name, font_size, hex_color, bg_ffmpeg, position):
    alignment = {"Bottom": 2, "Middle": 5, "Top": 8}.get(position, 2)
    primary   = _hex_to_ass(hex_color)
    back      = _box_ass(bg_ffmpeg)
    margin_v  = 30

    header = f"""[Script Info]
ScriptType: v4.00+
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary},&H00FFFFFF,&H00000000,{back},-1,0,0,0,100,100,0,0,3,2,0,{alignment},20,20,{margin_v},1

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
            s_ass, e_ass = _srt_to_ass_time(s_str), _srt_to_ass_time(e_str)
        except Exception:
            continue
        text = r"\N".join(rows[2:])
        lines.append(f"Dialogue: 0,{s_ass},{e_ass},Default,,0,0,0,,{text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Main ───────────────────────────────────────────────────────────────────────

def burn_captions_to_video(
    input_path: str,
    output_path: str,
    segments: list,
    font_name: str,
    font_path,
    color_info: dict,
    position: str = "Bottom",
    typewriter: bool = False,
    typewriter_speed: int = 20,
    font_size: int = 38,
):
    if not segments:
        shutil.copy(input_path, output_path)
        return

    # Clean up font name for ASS (Arial-Bold → Arial Bold)
    ass_font = font_name.replace("-", " ")

    hex_color  = color_info.get("hex", "#FFFFFF")
    bg_ffmpeg  = color_info.get("bg_ffmpeg", "black@0.65")

    tmp_dir  = tempfile.mkdtemp()
    srt_path = os.path.join(tmp_dir, "caps.srt")
    ass_path = os.path.join(tmp_dir, "caps.ass")

    try:
        # 1. Write SRT
        if typewriter:
            _write_typewriter_srt(segments, srt_path, typewriter_speed)
        else:
            _write_srt(segments, srt_path)

        # 2. Convert to styled ASS
        _srt_to_ass(srt_path, ass_path, ass_font, font_size,
                    hex_color, bg_ffmpeg, position)

        # 3. Build FFmpeg subtitles filter path (Windows-safe)
        #    Forward slashes; escape the colon after drive letter  C:/path → C\:/path
        ass_fwd = ass_path.replace("\\", "/")
        # Escape colon in drive letter for FFmpeg filter syntax  (e.g. C:/ → C\:/)
        if len(ass_fwd) > 1 and ass_fwd[1] == ":":
            ass_fwd = ass_fwd[0] + "\\:" + ass_fwd[2:]

        vf = f"subtitles='{ass_fwd}'"

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

        print(f"[Captioner] Burning {len(segments)} segments | font={ass_font} | pos={position}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("[Captioner] FFmpeg stderr:\n", result.stderr[-3000:])
            raise RuntimeError(
                f"FFmpeg failed (exit {result.returncode}).\n\n"
                "Tip: Make sure your FFmpeg build includes libass.\n"
                "Download a full build from https://www.gyan.dev/ffmpeg/builds/ "
                "(choose ffmpeg-release-full.7z, not essentials)."
            )

        print(f"[Captioner] Done → {output_path}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
