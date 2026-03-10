# 🎬 VideoCaptions AI

> **Transcribe Hindi & English videos → Translate to English → Burn styled captions**

A full-featured video captioning tool powered by OpenAI Whisper. Upload an MP4 or iPhone MOV file, get an English transcript, pick your caption style, and download the captioned video.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎙️ **Transcription** | OpenAI Whisper (tiny → large models) |
| 🌐 **Languages** | Hindi & English (auto-detected); outputs English |
| 📝 **Translation** | Whisper built-in translate task + deep-translator fallback |
| 🎨 **5 Caption Fonts** | Arial Bold, DejaVu Sans, Courier, Liberation Serif, Ubuntu |
| 🌈 **5 Color Themes** | White, Yellow, Cyan, Orange, Lime — all with dark box |
| ⌨️ **Typewriter Effect** | Reveal text character-by-character at custom speed |
| 📍 **Caption Position** | Top / Middle / Bottom |
| 📄 **SRT Export** | Download subtitle file for use in any player |
| 🖥️ **Streamlit UI** | Drag-and-drop browser interface |
| 💻 **CLI** | Script-friendly command-line interface |
| 🐳 **Docker** | One-command containerised deployment |

---

## 🚀 Quick Start (Local)

### 1. Prerequisites

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg fonts-dejavu-core fonts-liberation fonts-ubuntu

# Windows — download from https://ffmpeg.org/download.html
```

### 2. Install Python dependencies

```bash
git clone <your-repo>
cd video_caption_app

pip install -r requirements.txt
```

> **GPU users (optional):** Replace `torch` in requirements.txt with `torch --index-url https://download.pytorch.org/whl/cu118` for CUDA 11.8 — speeds up Whisper significantly.

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser. That's it!

---

## 💻 CLI Usage

```bash
# Basic usage (auto-detects Hindi/English, outputs English captions)
python cli.py my_video.mp4

# Full options
python cli.py my_video.mov \
  --output captioned.mp4 \
  --model medium \
  --font "Yellow on Black" \
  --color "Yellow on Black" \
  --position Bottom \
  --typewriter \
  --speed 25 \
  --srt

# Transcript only (no video rendering)
python cli.py lecture.mp4 --transcript-only --model large
```

### CLI Options

```
positional:
  input                Input video file (MP4 or MOV)

optional:
  -o, --output         Output path (default: <input>_captioned.mp4)
  -m, --model          Whisper model: tiny|base|small|medium|large (default: base)
  -f, --font           Caption font (see caption_styles.py for options)
  -c, --color          Caption color theme
  -p, --position       Top | Middle | Bottom  (default: Bottom)
  -t, --typewriter     Enable typewriter animation
  -s, --speed          Typewriter chars/sec (default: 20)
  --font-size          Font size in pixels (default: 36)
  --srt                Also save SRT subtitle file
  --transcript-only    Only transcribe; skip video rendering
```

---

## 🐳 Docker Deployment

### Build & Run Locally

```bash
docker build -t videocaptions-ai .
docker run -p 8501:8501 videocaptions-ai
# Visit http://localhost:8501
```

### Process a local file via CLI in Docker

```bash
docker run --rm \
  -v $(pwd):/data \
  videocaptions-ai \
  python cli.py /data/input.mp4 \
    --output /data/output_captioned.mp4 \
    --model base
```

---

## ☁️ Cloud Deployment Options

### Option A — Streamlit Community Cloud (Free, Easiest)

1. Push this project to a **public GitHub repo**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo → select `app.py` → Deploy

> ⚠️ Free tier has CPU-only, 1GB RAM — use `tiny` or `base` Whisper model.

### Option B — Hugging Face Spaces (Free, GPU available)

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose **Streamlit** as the SDK
3. Upload all project files
4. Add a `packages.txt` file containing: `ffmpeg`
5. Done — public URL provided automatically

### Option C — Railway / Render (Free tier available)

```bash
# railway.app
railway login
railway init
railway up
```

Or on **Render**: connect your GitHub repo, set Start Command to:
```
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

### Option D — Self-hosted VPS (Full control)

```bash
# On Ubuntu server
sudo apt install docker.io
docker build -t videocaptions-ai .
docker run -d -p 8501:8501 --restart unless-stopped videocaptions-ai

# With nginx reverse proxy + HTTPS (recommended)
# Point nginx to localhost:8501
```

---

## ⚙️ Whisper Model Guide

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|---------|
| `tiny` | 39 MB | ⚡⚡⚡⚡ | ★★☆☆ | Quick tests |
| `base` | 74 MB | ⚡⚡⚡ | ★★★☆ | **Default — good balance** |
| `small` | 244 MB | ⚡⚡ | ★★★★ | Better Hindi |
| `medium` | 769 MB | ⚡ | ★★★★ | Long lectures |
| `large` | 1.5 GB | 🐢 | ★★★★★ | Best quality |

---

## 📁 Project Structure

```
video_caption_app/
├── app.py              ← Streamlit web UI
├── cli.py              ← Command-line interface
├── transcriber.py      ← Whisper transcription + translation
├── captioner.py        ← FFmpeg caption burning engine
├── caption_styles.py   ← Font & color palette definitions
├── requirements.txt    ← Python dependencies
├── Dockerfile          ← Container build
└── README.md
```

---

## 🛠 Customisation

### Add a new font

In `caption_styles.py`, add an entry to `FONT_OPTIONS`:

```python
"My Custom Font": {
    "ffmpeg_name": "MyFont-Bold",
    "css_fallback": "MyFont, sans-serif",
    "path": "/path/to/MyFont-Bold.ttf",  # None to use system font
},
```

### Add a new color theme

```python
"Purple Pop": {
    "hex":        "#C084FC",
    "ffmpeg":     "0xC084FC",
    "bg":         "#1A0030",
    "bg_ffmpeg":  "0x1A0030@0.75",
},
```

---

## 🔧 Troubleshooting

**FFmpeg not found:**
```bash
which ffmpeg   # should print a path
sudo apt install ffmpeg   # Ubuntu
brew install ffmpeg       # macOS
```

**CUDA/GPU issues:**
```bash
# Force CPU mode
CUDA_VISIBLE_DEVICES="" python cli.py input.mp4
```

**Font not rendering correctly:**
- Install system fonts: `sudo apt install fonts-dejavu-core fonts-liberation`
- Or provide an absolute `path` in `FONT_OPTIONS`

**Hindi not being detected:**
- Try `--model small` or higher (tiny model struggles with Hindi)
- Ensure audio is clear and not heavily compressed

---

## 📄 License

MIT — free to use, modify, and deploy.
