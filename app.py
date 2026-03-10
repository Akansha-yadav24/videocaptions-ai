"""
VideoCaptions AI — Hindi/English Video Transcription & Caption Tool
Streamlit App Entry Point
"""

import streamlit as st
import os
import tempfile
import time
from pathlib import Path

from transcriber import transcribe_and_translate
from captioner import burn_captions_to_video
from caption_styles import FONT_OPTIONS, COLOR_OPTIONS


# ── Helper functions (defined here so they're available throughout) ────────────

def segments_to_srt(segments):
    """Convert Whisper segments to SRT format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = format_srt_time(seg["start"])
        end = format_srt_time(seg["end"])
        lines.append(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n")
    return "\n".join(lines)


def format_srt_time(seconds):
    """Convert seconds to SRT timestamp HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VideoCaptions AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

  .main-title {
    font-size: 3rem; font-weight: 700; letter-spacing: -2px;
    background: linear-gradient(135deg, #6366f1, #ec4899);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
  }
  .subtitle { color: #94a3b8; font-size: 1.1rem; margin-bottom: 2rem; }

  .step-badge {
    display: inline-block; background: #6366f1; color: white;
    border-radius: 50%; width: 28px; height: 28px; line-height: 28px;
    text-align: center; font-weight: 700; font-size: 0.85rem; margin-right: 8px;
  }

  .preview-box {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 12px;
    padding: 1.5rem; font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem; color: #94a3b8; max-height: 280px; overflow-y: auto;
  }

  .caption-preview {
    background: #000; color: #fff; padding: 1rem 1.5rem;
    border-radius: 8px; text-align: center; font-size: 1.2rem;
    margin: 0.5rem 0; min-height: 60px; display: flex;
    align-items: center; justify-content: center;
    border: 2px solid #1e293b;
  }

  .stat-card {
    background: #1e293b; border-radius: 10px; padding: 1rem 1.5rem;
    text-align: center; border: 1px solid #334155;
  }
  .stat-value { font-size: 1.8rem; font-weight: 700; color: #6366f1; }
  .stat-label { color: #94a3b8; font-size: 0.85rem; }

  div[data-testid="stProgress"] > div { background: #6366f1 !important; }
  .stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; border: none; border-radius: 8px;
    font-weight: 600; padding: 0.6rem 2rem; font-size: 1rem;
    transition: all 0.2s;
  }
  .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 25px rgba(99,102,241,0.4); }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🎬 VideoCaptions AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Transcribe Hindi & English videos · Translate · Burn styled captions</div>', unsafe_allow_html=True)

# ── Sidebar — Settings ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Caption Settings")

    st.markdown('<span class="step-badge">1</span>**Font Style**', unsafe_allow_html=True)
    font_choice = st.selectbox(
        "Choose font", list(FONT_OPTIONS.keys()), label_visibility="collapsed"
    )

    st.markdown('<span class="step-badge">2</span>**Caption Color**', unsafe_allow_html=True)
    color_choice = st.selectbox(
        "Choose color", list(COLOR_OPTIONS.keys()), label_visibility="collapsed"
    )

    st.markdown('<span class="step-badge">3</span>**Caption Style**', unsafe_allow_html=True)
    caption_style = st.radio(
        "Style", ["Standard Burn-In", "Typewriter Animation"],
        label_visibility="collapsed"
    )

    if caption_style == "Typewriter Animation":
        typewriter_speed = st.slider(
            "Typewriter Speed (chars/sec)", min_value=5, max_value=60,
            value=20, step=5,
            help="Higher = faster text reveal"
        )
    else:
        typewriter_speed = 20

    st.markdown('<span class="step-badge">4</span>**Position**', unsafe_allow_html=True)
    caption_position = st.select_slider(
        "Vertical position", options=["Top", "Middle", "Bottom"],
        value="Bottom", label_visibility="collapsed"
    )

    st.markdown('<span class="step-badge">5</span>**Whisper Model**', unsafe_allow_html=True)
    whisper_model = st.select_slider(
        "Model size (larger = more accurate, slower)",
        options=["tiny", "base", "small", "medium", "large"],
        value="base", label_visibility="collapsed"
    )

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Font:** `{font_choice}`")
    with col_b:
        color_hex = COLOR_OPTIONS[color_choice]["hex"]
        st.markdown(f"**Color:** <span style='color:{color_hex}'>■</span> {color_choice}", unsafe_allow_html=True)

    # Live caption preview
    st.markdown("#### Caption Preview")
    sample_text = "नमस्ते! Hello world."
    color_info = COLOR_OPTIONS[color_choice]
    st.markdown(
        f'<div class="caption-preview" style="color:{color_info["hex"]};'
        f'background:{color_info.get("bg","#000000")};'
        f'font-family:{FONT_OPTIONS[font_choice]["css_fallback"]}">'
        f'{sample_text}</div>',
        unsafe_allow_html=True
    )

# ── Main Area ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("### 📁 Upload Video")
    uploaded = st.file_uploader(
        "Drop an MP4 or MOV file here",
        type=["mp4", "mov", "m4v"],
        help="Supports iPhone MOV files and standard MP4. Max recommended: 500MB"
    )

    if uploaded:
        # Show file info
        file_size_mb = uploaded.size / (1024 * 1024)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{file_size_mb:.1f}</div><div class="stat-label">MB</div></div>', unsafe_allow_html=True)
        with c2:
            ext = Path(uploaded.name).suffix.upper()
            st.markdown(f'<div class="stat-card"><div class="stat-value">{ext}</div><div class="stat-label">Format</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-value">EN</div><div class="stat-label">Output Lang</div></div>', unsafe_allow_html=True)

        st.markdown("#### 🎥 Original Video")
        st.video(uploaded)

with col2:
    st.markdown("### 📝 Transcription")

    if not uploaded:
        st.info("Upload a video on the left to get started.")
    else:
        run_btn = st.button("🚀 Transcribe & Add Captions", use_container_width=True)

        if run_btn:
            # Save upload to temp file
            suffix = Path(uploaded.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
                tmp_in.write(uploaded.read())
                input_path = tmp_in.name

            output_path = input_path.replace(suffix, "_captioned.mp4")

            # ── Step 1: Transcribe ──────────────────────────────────────────
            progress = st.progress(0, text="🎙️ Loading Whisper model…")
            status = st.empty()

            try:
                status.markdown("**Step 1/3** — Transcribing audio with Whisper…")
                segments, detected_lang, full_text = transcribe_and_translate(
                    input_path,
                    model_size=whisper_model
                )
                progress.progress(40, text="✅ Transcription complete")

                # Show detected language
                lang_display = "Hindi 🇮🇳" if detected_lang == "hi" else f"{detected_lang.upper()} 🌐"
                st.success(f"Detected language: **{lang_display}** → Translated to English")

                # Show transcript
                st.markdown("#### 📄 English Transcript")
                st.markdown(f'<div class="preview-box">{full_text}</div>', unsafe_allow_html=True)

                # Segment count
                st.markdown(f"**{len(segments)} caption segments** detected")

                # ── Step 2: Download SRT ────────────────────────────────────
                srt_content = segments_to_srt(segments)
                st.download_button(
                    "⬇️ Download SRT Subtitles",
                    data=srt_content,
                    file_name=f"{Path(uploaded.name).stem}_captions.srt",
                    mime="text/plain",
                    use_container_width=True
                )

                # ── Step 3: Burn Captions ───────────────────────────────────
                status.markdown("**Step 2/3** — Burning captions into video…")
                progress.progress(60, text="🎨 Rendering captions…")

                burn_captions_to_video(
                    input_path=input_path,
                    output_path=output_path,
                    segments=segments,
                    font_name=FONT_OPTIONS[font_choice]["ffmpeg_name"],
                    font_path=FONT_OPTIONS[font_choice].get("path"),
                    color_info=COLOR_OPTIONS[color_choice],
                    position=caption_position,
                    typewriter=caption_style == "Typewriter Animation",
                    typewriter_speed=typewriter_speed,
                )

                progress.progress(100, text="✅ Done!")
                status.markdown("**Step 3/3** — Complete! 🎉")

                # ── Output Video ────────────────────────────────────────────
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
                # Cleanup temp files
                for p in [input_path, output_path]:
                    try:
                        os.unlink(p)
                    except Exception:
                        pass


