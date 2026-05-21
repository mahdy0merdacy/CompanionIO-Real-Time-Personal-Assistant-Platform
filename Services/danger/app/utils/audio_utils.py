"""
Audio preprocessing utilities.

Handles:
- Loading audio from bytes (wav, mp3, ogg, flac, webm)
- Resampling to the target sample rate
- Mono conversion
- Duration validation
- Returning a float32 numpy array ready for models
"""
import io
import logging
import numpy as np
from typing import Tuple

logger = logging.getLogger(__name__)


def load_audio(
    audio_bytes: bytes,
    target_sr: int = 16_000,
    max_duration_s: float = 30.0,
    min_duration_s: float = 0.5,
) -> Tuple[np.ndarray, int]:
    """
    Decode any audio format → mono float32 numpy array at `target_sr`.

    Returns:
        (waveform, sample_rate)

    Raises:
        ValueError: if the audio is too short or too long.
    """
    try:
        import soundfile as sf
    except ImportError:
        raise RuntimeError("soundfile is required: pip install soundfile")

    try:
        waveform, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=False)
    except Exception:
        # soundfile can't handle mp3 / webm – fall back to librosa
        try:
            import librosa
            waveform, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True, dtype=np.float32)
        except Exception as e:
            raise ValueError(f"Could not decode audio: {e}") from e

    # Ensure mono
    if waveform.ndim == 2:
        waveform = waveform.mean(axis=1)

    # Resample if needed
    if sr != target_sr:
        try:
            import librosa
            waveform = librosa.resample(waveform, orig_sr=sr, target_sr=target_sr)
            sr = target_sr
        except ImportError:
            raise RuntimeError("librosa is required for resampling: pip install librosa")

    duration = len(waveform) / sr
    if duration < min_duration_s:
        raise ValueError(f"Audio too short: {duration:.2f}s (min {min_duration_s}s)")
    if duration > max_duration_s:
        logger.warning(f"Audio {duration:.1f}s exceeds max {max_duration_s}s – truncating.")
        waveform = waveform[: int(max_duration_s * sr)]

    # Normalise amplitude to [-1, 1]
    peak = np.abs(waveform).max()
    if peak > 0:
        waveform = waveform / peak

    return waveform.astype(np.float32), sr


def split_into_chunks(
    waveform: np.ndarray,
    sr: int,
    chunk_duration_s: float = 3.0,
    overlap_s: float = 0.5,
) -> list[np.ndarray]:
    """
    Split a waveform into overlapping chunks.
    Useful for long recordings – each chunk is analysed independently.
    """
    chunk_len = int(chunk_duration_s * sr)
    hop_len = int((chunk_duration_s - overlap_s) * sr)
    chunks = []
    start = 0
    while start < len(waveform):
        end = min(start + chunk_len, len(waveform))
        chunk = waveform[start:end]
        # Pad last chunk if shorter than chunk_len
        if len(chunk) < chunk_len:
            chunk = np.pad(chunk, (0, chunk_len - len(chunk)))
        chunks.append(chunk)
        start += hop_len
        if end == len(waveform):
            break
    return chunks
