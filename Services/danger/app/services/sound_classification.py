"""
Sound Classification Service – wraps YAMNet.

YAMNet outputs per-frame class probabilities for 521 AudioSet classes.
We aggregate with mean pooling and look for dangerous sound classes.
"""
import logging
import numpy as np
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Pre-computed set for O(1) lookup
_DANGEROUS_SET = {s.lower() for s in settings.DANGEROUS_SOUND_CLASSES}


class SoundClassificationService:

    async def analyse(self, waveform: np.ndarray) -> Dict[str, Any]:
        """
        Returns:
            {
                "score": float,          # 0–1 danger contribution
                "top_classes": [...],    # highest probability classes overall
                "danger_classes": [...], # dangerous classes that fired
                "triggers": [...]        # human-readable trigger strings
            }
        """
        registry = ModelRegistry.get_instance()
        if registry.yamnet is None:
            logger.warning("YAMNet not loaded – skipping sound classification.")
            return self._empty_result()

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._run_inference, waveform, registry
            )
            return result
        except Exception as e:
            logger.error(f"Sound classification error: {e}")
            return self._empty_result()

    def _run_inference(self, waveform: np.ndarray, registry: ModelRegistry) -> Dict[str, Any]:
        import tensorflow as tf

        # YAMNet expects a 1-D float32 tensor
        wav_tensor = tf.constant(waveform, dtype=tf.float32)
        scores, embeddings, spectrogram = registry.yamnet(wav_tensor)

        # scores shape: (num_frames, 521) – mean-pool over time
        mean_scores = tf.reduce_mean(scores, axis=0).numpy()  # (521,)

        # Map class names
        class_names = registry.yamnet_class_names
        indexed = sorted(
            enumerate(mean_scores), key=lambda x: x[1], reverse=True
        )

        top_classes = [class_names[i] for i, _ in indexed[:5]]
        danger_classes = []
        danger_score = 0.0

        for idx, prob in indexed[:30]:          # check top-30 classes
            name = class_names[idx]
            if name.lower() in _DANGEROUS_SET:
                danger_classes.append({"class": name, "confidence": float(prob)})
                danger_score = max(danger_score, float(prob))

        triggers = [self._class_to_trigger(d["class"]) for d in danger_classes]

        return {
            "score": danger_score,
            "top_classes": top_classes,
            "danger_classes": danger_classes,
            "triggers": list(set(triggers)),
        }

    @staticmethod
    def _class_to_trigger(class_name: str) -> str:
        mapping = {
            "screaming": "screaming_detected",
            "shout": "screaming_detected",
            "crying, sobbing": "crying_detected",
            "glass": "breaking_glass_detected",
            "breaking": "breaking_glass_detected",
            "explosion": "explosion_detected",
            "gunshot, gunfire": "gunshot_detected",
            "alarm": "alarm_detected",
            "smoke detector, smoke alarm": "alarm_detected",
            "siren": "siren_detected",
            "emergency vehicle": "siren_detected",
        }
        return mapping.get(class_name.lower(), "dangerous_sound_detected")

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {"score": 0.0, "top_classes": [], "danger_classes": [], "triggers": []}
