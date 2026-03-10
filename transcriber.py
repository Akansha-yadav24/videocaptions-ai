"""
transcriber.py — Whisper-based transcription + Hindi→English translation

Supports:
  - Hindi audio → English text  (Whisper translate task)
  - English audio → English text (Whisper transcribe task)
  - Auto language detection
"""

import os
import whisper
import warnings
warnings.filterwarnings("ignore")

# Optional: deep-translator fallback for post-processing
try:
    from deep_translator import GoogleTranslator
    HAS_DEEP_TRANSLATOR = True
except ImportError:
    HAS_DEEP_TRANSLATOR = False


def transcribe_and_translate(
    audio_path: str,
    model_size: str = "base",
) -> tuple[list[dict], str, str]:
    """
    Transcribe and translate audio to English.

    Args:
        audio_path:  Path to input video/audio file (MP4, MOV, WAV, etc.)
        model_size:  Whisper model: tiny | base | small | medium | large

    Returns:
        segments    : list of dicts with keys: start, end, text (in English)
        detected_lang: ISO-639-1 language code (e.g. 'hi', 'en')
        full_text   : concatenated English transcript
    """
    print(f"[Whisper] Loading '{model_size}' model…")
    model = whisper.load_model(model_size)

    # Step 1: detect language from first 30s
    print("[Whisper] Detecting language…")
    audio = whisper.load_audio(audio_path)
    audio_clip = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio_clip).to(model.device)
    _, probs = model.detect_language(mel)
    detected_lang = max(probs, key=probs.get)
    print(f"[Whisper] Detected language: {detected_lang} (confidence: {probs[detected_lang]:.2%})")

    # Step 2: Transcribe / Translate
    # Using "translate" task forces Whisper to output English regardless of source language.
    # This works best for Hindi, as Whisper was trained on multilingual translation.
    task = "translate"   # always produce English output

    print(f"[Whisper] Running '{task}' task on full audio…")
    result = model.transcribe(
        audio_path,
        task=task,
        language=detected_lang if detected_lang != "en" else None,
        verbose=False,
        word_timestamps=False,
        condition_on_previous_text=True,
        fp16=False,  # use fp32 for CPU compatibility
    )

    raw_segments = result.get("segments", [])

    # Step 3: Build clean segment list
    segments = []
    for seg in raw_segments:
        text = seg["text"].strip()
        if not text:
            continue

        # Optional: run through deep_translator for a second-pass cleanup
        # (useful when Whisper's built-in translation is rough)
        if HAS_DEEP_TRANSLATOR and detected_lang not in ("en", "english"):
            try:
                text = GoogleTranslator(source="auto", target="en").translate(text) or text
            except Exception:
                pass  # keep Whisper translation

        segments.append({
            "start": seg["start"],
            "end":   seg["end"],
            "text":  text,
        })

    full_text = " ".join(s["text"] for s in segments)
    print(f"[Whisper] Done. {len(segments)} segments, ~{len(full_text.split())} words.")
    return segments, detected_lang, full_text
