"""
ModelRegistry – thread-safe singleton that owns all ML model instances.
Models are loaded once at startup and reused across requests.

Fixes applied:
- Thread-safe double-checked locking for get_instance()
- Separate threading.Lock (sync) and asyncio.Lock (async) to avoid deadlocks
"""
import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None
    _cls_lock = threading.Lock()   # sync lock for singleton creation

    def __init__(self):
        self.yamnet = None
        self.yamnet_class_names = None
        self.emotion_pipeline = None
        self._loaded = False
        self._async_lock: Optional[asyncio.Lock] = None   # created lazily in async ctx

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        # Double-checked locking pattern – safe across threads
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def load_all(self):
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        async with self._async_lock:
            if self._loaded:
                return
            await asyncio.gather(
                self._load_yamnet(),
                self._load_emotion_model(),
            )
            self._loaded = True

    async def unload_all(self):
        """Release GPU/CPU memory."""
        self.yamnet = None
        self.yamnet_class_names = None
        self.emotion_pipeline = None
        self._loaded = False

    def all_loaded(self) -> bool:
        return self._loaded

    # ── Loaders ───────────────────────────────────────────────────────────────

    async def _load_yamnet(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_yamnet_sync)

    def _load_yamnet_sync(self):
        try:
            import tensorflow_hub as hub
            import tensorflow as tf
            from app.core.config import settings

            logger.info("Loading YAMNet from TF Hub…")
            self.yamnet = hub.load(settings.YAMNET_MODEL_URL)

            # Load class map bundled with the SavedModel
            class_map_path = self.yamnet.class_map_path().numpy().decode()
            import csv
            with tf.io.gfile.GFile(class_map_path) as f:
                reader = csv.DictReader(f)
                self.yamnet_class_names = [r["display_name"] for r in reader]

            logger.info(f"YAMNet loaded – {len(self.yamnet_class_names)} sound classes.")
        except Exception as e:
            logger.error(f"YAMNet load failed: {e}")
            self.yamnet = None
            self.yamnet_class_names = []

    async def _load_emotion_model(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._load_emotion_model_sync)

    def _load_emotion_model_sync(self):
        try:
            from transformers import pipeline
            from app.core.config import settings

            logger.info(f"Loading emotion model: {settings.EMOTION_MODEL_NAME}…")
            self.emotion_pipeline = pipeline(
                "audio-classification",
                model=settings.EMOTION_MODEL_NAME,
                device=-1,      # CPU; set to 0 for GPU
                top_k=7,
            )
            logger.info("Emotion model loaded.")
        except Exception as e:
            logger.error(f"Emotion model load failed: {e}")
            self.emotion_pipeline = None
