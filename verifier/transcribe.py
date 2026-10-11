"""Downloads/loads Whisper only on first transcription, never at API import."""
import os
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel
    return WhisperModel(os.getenv("NOCAP_WHISPER_MODEL", "base.en"), device="cpu", compute_type="int8")

def transcribe(wav_path: str) -> str:
    path = Path(wav_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    segments, _ = _model().transcribe(str(path), language="en", vad_filter=True)
    return " ".join(s.text.strip() for s in segments)
