"""
Core configuration – driven by environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8004
    WORKERS: int = 1          # Keep at 1: GPU models are not fork-safe
    ALLOWED_ORIGINS: List[str] = ["*"]

    # ── Audio ─────────────────────────────────────────────────────────────────
    TARGET_SAMPLE_RATE: int = 16_000   # All models expect 16 kHz
    MAX_AUDIO_DURATION_S: float = 30.0
    MIN_AUDIO_DURATION_S: float = 0.5

    # ── Model paths / names ───────────────────────────────────────────────────
    # YAMNet is downloaded automatically via TensorFlow Hub
    YAMNET_MODEL_URL: str = "https://tfhub.dev/google/yamnet/1"

    # HuBERT-based emotion model from HuggingFace
    EMOTION_MODEL_NAME: str = "superb/hubert-large-superb-er"

    # Danger keywords – extend to support multiple languages
    DANGER_KEYWORDS: List[str] = [
        # English
        "help", "fire", "danger", "emergency", "stop", "no", "please stop",
        # French
        "au secours", "à l'aide", "aidez-moi", "danger", "feu", "arrêtez",
        # Arabic (transliterated)
        "najda", "musa3ada",
    ]

    # ── Scoring weights (must sum to 1.0) ────────────────────────────────────
    WEIGHT_SOUND: float = 0.40
    WEIGHT_EMOTION: float = 0.35
    WEIGHT_TEXT: float = 0.25

    # ── Thresholds ────────────────────────────────────────────────────────────
    DANGER_THRESHOLD: float = 0.45   # score ≥ threshold → danger=True

    # ── Sound classes to flag as dangerous ───────────────────────────────────
    DANGEROUS_SOUND_CLASSES: List[str] = [
        "Screaming", "Crying, sobbing", "Shout",
        "Glass", "Breaking", "Explosion", "Gunshot, gunfire",
        "Alarm", "Smoke detector, smoke alarm",
        "Emergency vehicle", "Siren",
    ]

    # ── Emotion classes to flag as dangerous ─────────────────────────────────
    DANGEROUS_EMOTION_CLASSES: List[str] = ["ang", "fea", "sad"]
    # Labels used by superb/hubert-large-superb-er:
    # ang=anger, fea=fear, hap=happiness, neu=neutral, sad=sadness, dis=disgust, sur=surprise

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
