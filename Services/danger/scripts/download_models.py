"""
Pre-download all models so they're baked into the Docker image.
Run during docker build or first-run setup.
"""
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_yamnet():
    logger.info("Downloading YAMNet…")
    import tensorflow_hub as hub
    model = hub.load("https://tfhub.dev/google/yamnet/1")
    logger.info("YAMNet cached.")


def download_emotion_model():
    logger.info("Downloading emotion model…")
    from transformers import pipeline
    pipe = pipeline("audio-classification", model="superb/hubert-large-superb-er", device=-1)
    logger.info("Emotion model cached.")


if __name__ == "__main__":
    download_yamnet()
    download_emotion_model()
    logger.info("✅ All models downloaded and cached.")
