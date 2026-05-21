"""
Emotion Detection Service – wraps a HuBERT-based speech-emotion classifier.

Model: superb/hubert-large-superb-er (HuggingFace)
Labels: ang, dis, fea, hap, neu, sad, sur

We compute a danger score as the sum of probabilities for
dangerous emotion classes (anger, fear, sadness).
"""
import logging
import numpy as np
from typing import Dict, Any, List

from app.core.config import settings
from app.core.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

_DANGEROUS_EMOTIONS = set(settings.DANGEROUS_EMOTION_CLASSES)

# Weight multipliers per emotion (fear is the strongest signal)
_EMOTION_WEIGHTS = {
    "fea": 1.0,   # fear
    "ang": 0.75,  # anger
    "sad": 0.50,  # sadness
    "dis": 0.30,  # disgust
}

_HUMAN_LABELS = {
    "ang": "anger",
    "dis": "disgust",
    "fea": "fear",
    "hap": "happiness",
    "neu": "neutral",
    "sad": "sadness",
    "sur": "surprise",
}


class EmotionDetectionService:

    async def analyse(self, waveform: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Returns:
            {
                "score": float,          # 0–1 danger contribution
                "top_emotion": str,      # dominant emotion label
                "all_emotions": dict,    # label → probability
                "triggers": list[str]
            }
        """
        registry = ModelRegistry.get_instance()
        if registry.emotion_pipeline is None:
            logger.warning("Emotion model not loaded – skipping emotion detection.")
            return self._empty_result()

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._run_inference, waveform, sr, registry
            )
            return result
        except Exception as e:
            logger.error(f"Emotion detection error: {e}")
            return self._empty_result()

    def _run_inference(
        self, waveform: np.ndarray, sr: int, registry: ModelRegistry
    ) -> Dict[str, Any]:
        # HuggingFace pipeline accepts a dict with array + sampling_rate
        inputs = {"array": waveform, "sampling_rate": sr}
        predictions: List[Dict] = registry.emotion_pipeline(inputs)
        # predictions = [{"label": "fea", "score": 0.82}, ...]

        all_emotions = {p["label"]: p["score"] for p in predictions}
        top = max(predictions, key=lambda x: x["score"])

        # Weighted danger score across dangerous emotions
        danger_score = 0.0
        triggers = []
        for label, prob in all_emotions.items():
            if label in _DANGEROUS_EMOTIONS:
                w = _EMOTION_WEIGHTS.get(label, 0.5)
                danger_score += prob * w
                if prob > 0.25:
                    triggers.append(f"{_HUMAN_LABELS.get(label, label)}_detected")

        # Clamp to [0, 1]
        danger_score = min(danger_score, 1.0)

        return {
            "score": danger_score,
            "top_emotion": top["label"],
            "top_emotion_label": _HUMAN_LABELS.get(top["label"], top["label"]),
            "all_emotions": all_emotions,
            "triggers": triggers,
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "score": 0.0,
            "top_emotion": "unknown",
            "top_emotion_label": "unknown",
            "all_emotions": {},
            "triggers": [],
        }
