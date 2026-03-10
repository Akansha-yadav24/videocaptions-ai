# VideoCaptions AI — Docker Image
# Supports Streamlit web app + CLI
#
# Build:  docker build -t videocaptions-ai .
# Run:    docker run -p 8501:8501 videocaptions-ai
# CLI:    docker run --rm -v $(pwd):/data videocaptions-ai python cli.py /data/video.mp4 --output /data/out.mp4

FROM python:3.11-slim

# System deps: ffmpeg + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-ubuntu \
    fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Whisper model cache dir
ENV WHISPER_CACHE=/root/.cache/whisper
RUN mkdir -p $WHISPER_CACHE

# Pre-download the 'base' model (optional — remove to save image size)
# RUN python -c "import whisper; whisper.load_model('base')"

EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Default: launch Streamlit
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.maxUploadSize=500", \
     "--browser.gatherUsageStats=false"]
