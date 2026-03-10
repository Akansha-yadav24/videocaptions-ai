"""
VideoCaptions AI — Hindi/English Video Transcription & Caption Tool
Streamlit App with Live Caption Placement Preview
"""

import streamlit as st
import os
import base64
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

from transcriber import transcribe_and_translate
from captioner import burn_captions_to_video
from caption_styles import FONT_OPTIONS, COLOR_OPTIONS


# ── Helpers ────────────────────────────────────────────────────────────────────

def segments_to_srt(segments):
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(f"{i}\n{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}\n{seg['text'].strip()}\n")
    return "\n".join(lines)


def fmt_time(s):
    h = int(s // 3600); m = int((s % 3600) // 60)
    sec = int(s % 60);  ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def hex_to_rgb(hex_color: str):
    named = {"white": (255,255,255), "yellow": (255,255,0), "black": (0,0,0),
             "red": (255,0,0), "green": (0,255,0), "blue": (0,0,255)}
    h = hex_color.lower()
    if h in named:
        return named[h]
    h = h.lstrip("#").lstrip("0x")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def build_preview_image(
    sample_text: str,
    font_css: str,
    font_size: int,
    text_color_hex: str,
    bg_color_hex: str,
    position_x_pct: float,   # 0–100 horizontal anchor
    position_y_pct: float,   # 0–100 vertical anchor
    canvas_w: int = 640,
    canvas_h: int = 360,
) -> str:
    """
    Render a PNG preview of caption placement on a simulated video frame.
    Returns base64-encoded PNG.
    """
    # Canvas — dark video-like background
    img = Image.new("RGB", (canvas_w, canvas_h), color=(15, 15, 20))
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw fake "video frame" grid lines
    for y in range(0, canvas_h, 60):
        draw.line([(0, y), (canvas_w, y)], fill=(30, 30, 40), width=1)
    for x in range(0, canvas_w, 80):
        draw.line([(x, 0), (x, canvas_h)], fill=(30, 30, 40), width=1)

    # Center crosshair
    draw.line([(canvas_w//2 - 20, canvas_h//2), (canvas_w//2 + 20, canvas_h//2)], fill=(60,60,80), width=1)
    draw.line([(canvas_w//2, canvas_h//2 - 20), (canvas_w//2, canvas_h//2 + 20)], fill=(60,60,80), width=1)

    # Try to load a real font, fall back to default
    pil_font = None
    try:
        # Try system fonts by size
        from PIL import ImageFont
        # Common Windows font paths
        win_fonts = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/verdana.ttf",
        ]
        linux_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        ]
        for fp in win_fonts + linux_fonts:
            if os.path.isfile(fp):
                pil_font = ImageFont.truetype(fp, size=font_size)
                break
    except Exception:
        pass

    if pil_font is None:
        pil_font = ImageFont.load_default()

    # Measure text
    wrap_chars = max(20, int(canvas_w / (font_size * 0.6)))
    words = sample_text.split()
    lines_out, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > wrap_chars and cur:
            lines_out.append(cur.strip()); cur = w + " "
        else:
            cur += w + " "
    if cur.strip():
        lines_out.append(cur.strip())
    display_text = "\n".join(lines_out)

    # Get bounding box
    bbox = draw.multiline_textbbox((0, 0), display_text, font=pil_font, spacing=4)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Compute position from percentages
    # x_pct=50 → centered, 0=left edge, 100=right edge
    x = int((position_x_pct / 100) * canvas_w - text_w / 2)
    y = int((position_y_pct / 100) * canvas_h - text_h / 2)

    # Clamp to canvas
    pad = 8
    x = max(pad, min(x, canvas_w - text_w - pad))
    y = max(pad, min(y, canvas_h - text_h - pad))

    # Draw background box
    bg_rgb = hex_to_rgb(bg_color_hex)
    draw.rounded_rectangle(
        [x - pad, y - pad, x + text_w + pad, y + text_h + pad],
        radius=6,
        fill=(*bg_rgb, 180)
    )

    # Draw text
    text_rgb = hex_to_rgb(text_color_hex)
    draw.multiline_text((x, y), display_text, font=pil_font,
                        fill=text_rgb, spacing=4, align="center")

    # Draw a red anchor dot at the exact position point
    ax = int((position_x_pct / 100) * canvas_w)
    ay = int((position_y_pct / 100) * canvas_h)
    draw.ellipse([ax-5, ay-5, ax+5, ay+5], fill=(255, 80, 80, 220))

    # Draw position % labels
    small = ImageFont.load_default()
    draw.text((4, 2), f"X:{position_x_pct:.0f}%  Y:{position_y_pct:.0f}%  Size:{font_size}px",
              font=small, fill=(120, 120, 160))
    draw.text((4, canvas_h - 14), "▶ Preview Frame", font=small, fill=(80, 80, 100))

    # Encode to base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VideoCaptions AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
  html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

  .main-title {
    font-size: 2.8rem; font-weight: 700; letter-spacing: -2px;
    background: linear-gradient(135deg, #6366f1, #ec4899);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
  }
  .subtitle { color: #94a3b8; font-size: 1rem; margin-bottom: 1.5rem; }
  .step-badge {
    display: inline-block; background: #6366f1; color: white;
    border-radius: 50%; width: 24px; height: 24px; line-height: 24px;
    text-align: center; font-weight: 700; font-size: 0.8rem; margin-right: 6px;
  }
  .preview-box {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 10px;
    padding: 1rem; font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem; color: #94a3b8; max-height: 200px; overflow-y: auto;
  }
  .stat-card {
    background: #1e293b; border-radius: 10px; padding: 0.8rem 1rem;
    text-align: center; border: 1px solid #334155;
  }
  .stat-value { font-size: 1.5rem; font-weight: 700; color: #6366f1; }
  .stat-label { color: #94a3b8; font-size: 0.8rem; }
  .preview-label {
    font-size: 0.75rem; color: #64748b; text-align: center; margin-top: 4px;
  }
  .stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; border: none; border-radius: 8px;
    font-weight: 600; padding: 0.6rem 1.5rem; font-size: 1rem; transition: all 0.2s;
  }
  .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 25px rgba(99,102,241,0.4); }
  div[data-testid="stProgress"] > div { background: #6366f1 !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🎬 VideoCaptions AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Transcribe Hindi & English · Translate · Burn styled captions with live placement preview</div>', unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Caption Settings")

    # 1. Font
    st.markdown('<span class="step-badge">1</span>**Font Style**', unsafe_allow_html=True)
    font_choice = st.selectbox("Font", list(FONT_OPTIONS.keys()), label_visibility="collapsed")

    # 2. Font Size
    st.markdown('<span class="step-badge">2</span>**Font Size**', unsafe_allow_html=True)
    font_size = st.slider("Font size (px)", min_value=16, max_value=80, value=38, step=2,
                          label_visibility="collapsed",
                          help="Pixel size — scales with video resolution")

    # 3. Color
    st.markdown('<span class="step-badge">3</span>**Caption Color**', unsafe_allow_html=True)
    color_choice = st.selectbox("Color", list(COLOR_OPTIONS.keys()), label_visibility="collapsed")

    # 4. Caption Style
    st.markdown('<span class="step-badge">4</span>**Caption Style**', unsafe_allow_html=True)
    caption_style = st.radio("Style", ["Standard Burn-In", "Typewriter Animation"],
                             label_visibility="collapsed")
    if caption_style == "Typewriter Animation":
        typewriter_speed = st.slider("Typewriter Speed (chars/sec)", 5, 60, 20, 5,
                                     help="Higher = faster text reveal")
    else:
        typewriter_speed = 20

    st.divider()

    # 5. Placement — X/Y sliders
    st.markdown("## 📍 Caption Placement")
    st.caption("Drag sliders to position. Watch the live preview update instantly.")

    pos_x = st.slider("↔ Horizontal (X)", min_value=0, max_value=100, value=50, step=1,
                      help="0 = left edge · 50 = center · 100 = right edge",
                      format="%d%%")
    pos_y = st.slider("↕ Vertical (Y)", min_value=0, max_value=100, value=88, step=1,
                      help="0 = top · 50 = middle · 88 = near bottom · 100 = bottom",
                      format="%d%%")

    # Quick-position presets
    st.caption("Quick presets:")
    qc1, qc2, qc3 = st.columns(3)
    with qc1:
        if st.button("⬆ Top", use_container_width=True):
            pos_x, pos_y = 50, 8
    with qc2:
        if st.button("⬛ Mid", use_container_width=True):
            pos_x, pos_y = 50, 50
    with qc3:
        if st.button("⬇ Bot", use_container_width=True):
            pos_x, pos_y = 50, 88

    st.divider()

    # 6. Whisper model
    st.markdown("## 🎙️ Transcription Model")
    whisper_model = st.select_slider(
        "Whisper model size",
        options=["tiny", "base", "small", "medium", "large"],
        value="base", label_visibility="collapsed"
    )
    st.caption("larger = more accurate but slower")

    # 7. Preview text override
    st.divider()
    st.markdown("## 🔤 Preview Text")
    preview_text = st.text_input("Sample caption text", value="Hello! यह एक उदाहरण है।",
                                 help="This text is shown in the placement preview below")


# ── Compute position string for captioner (from X/Y pct) ──────────────────────
# Convert X/Y percentages → "Top" / "Middle" / "Bottom" for ASS alignment
# AND pass raw pct values for the fine-grained ASS MarginV override
def pct_to_position_label(y_pct):
    if y_pct <= 25:
        return "Top"
    elif y_pct <= 65:
        return "Middle"
    else:
        return "Bottom"

caption_position = pct_to_position_label(pos_y)

# ── Live Placement Preview ─────────────────────────────────────────────────────
st.markdown("### 🖼️ Live Caption Placement Preview")
st.caption("This updates instantly as you move the sliders — no video needed.")

color_info = COLOR_OPTIONS[color_choice]
preview_b64 = build_preview_image(
    sample_text=preview_text,
    font_css=FONT_OPTIONS[font_choice]["css_fallback"],
    font_size=max(10, font_size // 2),   # scale down for 640px canvas
    text_color_hex=color_info["hex"],
    bg_color_hex=color_info.get("bg", "#000000"),
    position_x_pct=pos_x,
    position_y_pct=pos_y,
    canvas_w=640,
    canvas_h=360,
)

st.markdown(
    f'<div style="border:2px solid #1e293b; border-radius:12px; overflow:hidden; '
    f'box-shadow: 0 4px 24px rgba(0,0,0,0.5);">'
    f'<img src="data:image/png;base64,{preview_b64}" style="width:100%;display:block;" />'
    f'</div>'
    f'<p class="preview-label">🔴 Red dot = anchor point &nbsp;|&nbsp; '
    f'X: <b>{pos_x}%</b> &nbsp; Y: <b>{pos_y}%</b> &nbsp; Size: <b>{font_size}px</b> &nbsp; '
    f'Position zone: <b>{caption_position}</b></p>',
    unsafe_allow_html=True
)

st.divider()

# ── Main Upload + Process Area ─────────────────────────────────────────────────
col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("### 📁 Upload Video")
    uploaded = st.file_uploader(
        "Drop an MP4 or MOV file here",
        type=["mp4", "mov", "m4v"],
        help="Supports iPhone MOV and MP4. Recommended max: 500MB"
    )

    if uploaded:
        file_size_mb = uploaded.size / (1024 * 1024)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{file_size_mb:.1f}</div><div class="stat-label">MB</div></div>', unsafe_allow_html=True)
        with c2:
            ext = Path(uploaded.name).suffix.upper()
            st.markdown(f'<div class="stat-card"><div class="stat-value">{ext}</div><div class="stat-label">Format</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-value">EN</div><div class="stat-label">Output</div></div>', unsafe_allow_html=True)

        st.markdown("#### 🎥 Original Video")
        st.video(uploaded)

with col2:
    st.markdown("### 📝 Transcription & Render")

    if not uploaded:
        st.info("⬅️ Upload a video to get started.")
    else:
        # Settings summary before running
        st.markdown(f"""
        **Ready to render with:**
        - Font: `{font_choice}` at **{font_size}px**
        - Color: {color_info['hex']} — {color_choice}
        - Position: X **{pos_x}%** · Y **{pos_y}%** ({caption_position})
        - Style: {caption_style}
        - Whisper: `{whisper_model}`
        """)

        run_btn = st.button("🚀 Transcribe & Add Captions", use_container_width=True)

        if run_btn:
            suffix = Path(uploaded.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
                tmp_in.write(uploaded.read())
                input_path = tmp_in.name

            output_path = input_path.replace(suffix, "_captioned.mp4")
            progress = st.progress(0, text="🎙️ Loading Whisper model…")
            status = st.empty()

            try:
                status.markdown("**Step 1/3** — Transcribing with Whisper…")
                segments, detected_lang, full_text = transcribe_and_translate(
                    input_path, model_size=whisper_model
                )
                progress.progress(40, text="✅ Transcription complete")

                lang_display = "Hindi 🇮🇳" if detected_lang == "hi" else f"{detected_lang.upper()} 🌐"
                st.success(f"Detected: **{lang_display}** → English")

                st.markdown("#### 📄 English Transcript")
                st.markdown(f'<div class="preview-box">{full_text}</div>', unsafe_allow_html=True)
                st.markdown(f"**{len(segments)} caption segments**")

                srt_content = segments_to_srt(segments)
                st.download_button("⬇️ Download SRT", data=srt_content,
                                   file_name=f"{Path(uploaded.name).stem}_captions.srt",
                                   mime="text/plain", use_container_width=True)

                status.markdown("**Step 2/3** — Burning captions…")
                progress.progress(60, text="🎨 Rendering captions…")

                burn_captions_to_video(
                    input_path=input_path,
                    output_path=output_path,
                    segments=segments,
                    font_name=FONT_OPTIONS[font_choice]["ffmpeg_name"],
                    font_path=FONT_OPTIONS[font_choice].get("path"),
                    color_info=color_info,
                    position=caption_position,
                    pos_x_pct=pos_x,
                    pos_y_pct=pos_y,
                    typewriter=caption_style == "Typewriter Animation",
                    typewriter_speed=typewriter_speed,
                    font_size=font_size,
                )

                progress.progress(100, text="✅ Done!")
                status.markdown("**Step 3/3** — Complete! 🎉")

                st.markdown("### 🎬 Captioned Output")
                with open(output_path, "rb") as f:
                    video_bytes = f.read()

                st.video(video_bytes)
                st.download_button(
                    "⬇️ Download Captioned Video",
                    data=video_bytes,
                    file_name=f"{Path(uploaded.name).stem}_captioned.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.exception(e)
            finally:
                for p in [input_path, output_path]:
                    try: os.unlink(p)
                    except Exception: pass
