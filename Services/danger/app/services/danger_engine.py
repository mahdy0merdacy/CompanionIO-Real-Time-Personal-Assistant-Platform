"""
Danger Detection Engine – fuses signals from all three sub-services.

Fusion strategy:
  composite = W_sound * sound_score + W_emotion * emotion_score + W_text * text_score

A hard override is applied when any single signal is extremely strong (≥ 0.90),
ensuring that an obvious crisis (e.g., clear gunshot + transcript "help") is
never suppressed by low scores in the other channels.
"""
import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional

from app.core.config import settings
from app.models.schemas import DangerResponse
from app.services.sound_classification import SoundClassificationService
from app.services.emotion_detection import EmotionDetectionService
from app.services.text_analysis import TextAnalysisService
from app.utils.audio_utils import load_audio, split_into_chunks

logger = logging.getLogger(__name__)


class DangerDetectionEngine:
    """Orchestrates all sub-services and returns a final DangerResponse."""

    def __init__(self):
        self.sound_svc = SoundClassificationService()
        self.emotion_svc = EmotionDetectionService()
        self.text_svc = TextAnalysisService()

    # ── Public API ────────────────────────────────────────────────────────────

    async def analyse_audio(
        self,
        audio_bytes: bytes,
        stt_transcript: Optional[str] = None,
        language: str = "en",
    ) -> DangerResponse:
        """Full pipeline: audio + optional pre-computed transcript."""
        waveform, sr = load_audio(
            audio_bytes,
            target_sr=settings.TARGET_SAMPLE_RATE,
            max_duration_s=settings.MAX_AUDIO_DURATION_S,
            min_duration_s=settings.MIN_AUDIO_DURATION_S,
        )

        # Run all three analyses concurrently
        sound_task = self.sound_svc.analyse(waveform)
        emotion_task = self.emotion_svc.analyse(waveform, sr)
        text_task = self.text_svc.analyse(stt_transcript, language)

        sound_result, emotion_result, text_result = await asyncio.gather(
            sound_task, emotion_task, text_task
        )

        return self._fuse(sound_result, emotion_result, text_result)

    async def analyse_audio_chunked(
        self,
        audio_bytes: bytes,
        stt_transcript: Optional[str] = None,
        language: str = "en",
    ) -> DangerResponse:
        """
        For longer recordings: split into chunks, analyse each, return
        the worst-case result across all chunks.
        """
        waveform, sr = load_audio(
            audio_bytes,
            target_sr=settings.TARGET_SAMPLE_RATE,
            max_duration_s=settings.MAX_AUDIO_DURATION_S,
        )
        chunks = split_into_chunks(waveform, sr, chunk_duration_s=3.0)

        # Text analysis runs once for the full transcript
        text_result = await self.text_svc.analyse(stt_transcript, language)

        responses = await asyncio.gather(
            *[
                self._analyse_chunk(chunk, sr, text_result)
                for chunk in chunks
            ]
        )

        # Return the most dangerous chunk result
        return max(responses, key=lambda r: r.score)

    async def analyse_text_only(
        self, text: str, language: str = "en"
    ) -> DangerResponse:
        """Text-only path – used when orchestrator passes only the transcript."""
        text_result = await self.text_svc.analyse(text, language)
        return self._fuse(
            sound_result={"score": 0.0, "top_classes": [], "danger_classes": [], "triggers": []},
            emotion_result={"score": 0.0, "top_emotion": "unknown", "top_emotion_label": "unknown", "all_emotions": {}, "triggers": []},
            text_result=text_result,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _analyse_chunk(
        self,
        chunk: np.ndarray,
        sr: int,
        text_result: Dict[str, Any],
    ) -> DangerResponse:
        sound_result, emotion_result = await asyncio.gather(
            self.sound_svc.analyse(chunk),
            self.emotion_svc.analyse(chunk, sr),
        )
        return self._fuse(sound_result, emotion_result, text_result)

    def _fuse(
        self,
        sound_result: Dict[str, Any],
        emotion_result: Dict[str, Any],
        text_result: Dict[str, Any],
    ) -> DangerResponse:
        s_score = sound_result.get("score", 0.0)
        e_score = emotion_result.get("score", 0.0)
        t_score = text_result.get("score", 0.0)

        # Weighted composite score
        composite = (
            settings.WEIGHT_SOUND * s_score
            + settings.WEIGHT_EMOTION * e_score
            + settings.WEIGHT_TEXT * t_score
        )

        # Hard override: if any signal is extremely strong, raise composite floor
        max_single = max(s_score, e_score, t_score)
        if max_single >= 0.90:
            composite = max(composite, 0.70)

        # Aggregate triggers
        all_triggers = (
            sound_result.get("triggers", [])
            + emotion_result.get("triggers", [])
            + text_result.get("triggers", [])
        )
        triggers = list(dict.fromkeys(all_triggers))  # deduplicate, preserve order

        danger = composite >= settings.DANGER_THRESHOLD

        if danger:
            logger.warning(
                f"⚠️  DANGER DETECTED – score={composite:.3f} triggers={triggers}"
            )

        return DangerResponse(
            danger=danger,
            score=round(composite, 4),
            triggers=triggers,
            details={
                "sound_score": round(s_score, 4),
                "emotion_score": round(e_score, 4),
                "text_score": round(t_score, 4),
                "top_sounds": sound_result.get("top_classes", [])[:3],
                "top_emotion": emotion_result.get("top_emotion_label", "unknown"),
                "matched_keywords": text_result.get("matched_keywords", []),
            },
        )
