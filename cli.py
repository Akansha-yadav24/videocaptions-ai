#!/usr/bin/env python3
"""
cli.py — Command-line interface for VideoCaptions AI

Usage examples:
  python cli.py input.mp4 --output out.mp4
  python cli.py video.mov --model medium --font "Yellow on Black" --color "Yellow on Black"
  python cli.py clip.mp4 --typewriter --speed 25 --position Bottom
"""

import argparse
import sys
from pathlib import Path

from transcriber import transcribe_and_translate
from captioner import burn_captions_to_video
from caption_styles import FONT_OPTIONS, COLOR_OPTIONS


def segments_to_srt(segments):
    lines = []
    for i, seg in enumerate(segments, 1):
        start = fmt_time(seg["start"])
        end   = fmt_time(seg["end"])
        lines.append(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n")
    return "\n".join(lines)


def fmt_time(s):
    h = int(s // 3600); m = int((s % 3600) // 60)
    sec = int(s % 60);  ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def main():
    parser = argparse.ArgumentParser(
        description="🎬 VideoCaptions AI — Transcribe & caption Hindi/English videos"
    )
    parser.add_argument("input",  help="Input video file (MP4 or MOV)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output video path (default: <input>_captioned.mp4)")
    parser.add_argument("--model", "-m", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--font", "-f", default="Bold & Clean (Arial Bold)",
                        choices=list(FONT_OPTIONS.keys()),
                        help="Caption font style")
    parser.add_argument("--color", "-c", default="White on Black",
                        choices=list(COLOR_OPTIONS.keys()),
                        help="Caption color theme")
    parser.add_argument("--position", "-p", default="Bottom",
                        choices=["Top", "Middle", "Bottom"],
                        help="Caption vertical position")
    parser.add_argument("--typewriter", "-t", action="store_true",
                        help="Use typewriter animation effect")
    parser.add_argument("--speed", "-s", type=int, default=20,
                        help="Typewriter speed in chars/sec (default: 20)")
    parser.add_argument("--font-size", type=int, default=36,
                        help="Font size in pixels (default: 36)")
    parser.add_argument("--srt", action="store_true",
                        help="Also save an SRT subtitle file")
    parser.add_argument("--transcript-only", action="store_true",
                        help="Only transcribe; skip video rendering")

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix.lower() not in (".mp4", ".mov", ".m4v", ".mkv"):
        print("⚠️  Warning: file extension not recognised. Proceeding anyway…")

    output_path = args.output or str(input_path.with_suffix("")) + "_captioned.mp4"

    print(f"\n🎬 VideoCaptions AI")
    print(f"   Input  : {input_path}")
    print(f"   Output : {output_path}")
    print(f"   Model  : {args.model}")
    print(f"   Effect : {'Typewriter' if args.typewriter else 'Standard'}")
    print()

    # ── Transcribe ──────────────────────────────────────────────────────────────
    print("🎙️  Transcribing…")
    segments, detected_lang, full_text = transcribe_and_translate(
        str(input_path),
        model_size=args.model,
    )

    lang_label = "Hindi" if detected_lang == "hi" else detected_lang.upper()
    print(f"\n✅ Detected: {lang_label} → English")
    print(f"   Segments : {len(segments)}")
    print(f"   Words    : {len(full_text.split())}")
    print()
    print("── Transcript ──────────────────────────────────────")
    print(full_text[:1200] + ("…" if len(full_text) > 1200 else ""))
    print("────────────────────────────────────────────────────\n")

    if args.srt:
        srt_path = str(input_path.with_suffix("")) + "_captions.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(segments_to_srt(segments))
        print(f"📄 SRT saved: {srt_path}")

    if args.transcript_only:
        print("✅ Transcript-only mode — skipping video render.")
        return

    # ── Burn Captions ───────────────────────────────────────────────────────────
    print("🎨 Burning captions into video…")
    burn_captions_to_video(
        input_path=str(input_path),
        output_path=output_path,
        segments=segments,
        font_name=FONT_OPTIONS[args.font]["ffmpeg_name"],
        font_path=FONT_OPTIONS[args.font].get("path"),
        color_info=COLOR_OPTIONS[args.color],
        position=args.position,
        typewriter=args.typewriter,
        typewriter_speed=args.speed,
        font_size=args.font_size,
    )

    print(f"\n🎉 Done! Output saved to: {output_path}")


if __name__ == "__main__":
    main()
