"""
Test suite for the Danger Detection Service.

Run with:  pytest tests/ -v --asyncio-mode=auto
"""
import io
import json
import struct
import wave
import math
import pytest
import numpy as np
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


# ── Audio helpers ─────────────────────────────────────────────────────────────

def make_sine_wav(
    frequency: float = 440.0,
    duration: float = 2.0,
    sr: int = 16_000,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a synthetic WAV file (pure sine wave) as bytes."""
    n_samples = int(sr * duration)
    samples = [
        int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t / sr))
        for t in range(n_samples)
    ]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n_samples}h", *samples))
    return buf.getvalue()


SILENCE_WAV = make_sine_wav(frequency=0, amplitude=0.0)
SINE_WAV = make_sine_wav(frequency=440.0)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_registry():
    """Patch ModelRegistry so tests don't need real GPU models."""
    with patch("app.core.model_registry.ModelRegistry.get_instance") as mock_get:
        registry = MagicMock()
        registry.all_loaded.return_value = True
        registry.yamnet = None          # disable YAMNet – tests sound_svc path
        registry.yamnet_class_names = []
        registry.emotion_pipeline = None  # disable emotion – tests emotion_svc path
        mock_get.return_value = registry
        yield registry


@pytest.fixture
async def client(mock_registry):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ── Audio preprocessing ───────────────────────────────────────────────────────

def test_load_audio_basic():
    from app.utils.audio_utils import load_audio
    wav = make_sine_wav(duration=2.0, sr=16_000)
    waveform, sr = load_audio(wav, target_sr=16_000)
    assert sr == 16_000
    assert waveform.dtype == np.float32
    assert waveform.ndim == 1
    assert abs(len(waveform) / sr - 2.0) < 0.1


def test_load_audio_resamples():
    from app.utils.audio_utils import load_audio
    wav = make_sine_wav(duration=2.0, sr=44_100)
    waveform, sr = load_audio(wav, target_sr=16_000)
    assert sr == 16_000


def test_load_audio_too_short():
    from app.utils.audio_utils import load_audio
    import pytest
    wav = make_sine_wav(duration=0.1, sr=16_000)
    with pytest.raises(ValueError, match="too short"):
        load_audio(wav, target_sr=16_000, min_duration_s=0.5)


def test_split_into_chunks():
    from app.utils.audio_utils import split_into_chunks
    waveform = np.zeros(16_000 * 10, dtype=np.float32)  # 10s
    chunks = split_into_chunks(waveform, sr=16_000, chunk_duration_s=3.0, overlap_s=0.5)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) == 3 * 16_000


# ── Text analysis ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_text_danger_keywords():
    from app.services.text_analysis import TextAnalysisService
    svc = TextAnalysisService()
    result = await svc.analyse("Please help me I'm scared", language="en")
    assert result["score"] > 0
    assert "help" in result["matched_keywords"]
    assert result["triggers"]


@pytest.mark.asyncio
async def test_text_french_keyword():
    from app.services.text_analysis import TextAnalysisService
    svc = TextAnalysisService()
    result = await svc.analyse("Au secours quelqu'un m'attaque", language="fr")
    assert result["score"] > 0


@pytest.mark.asyncio
async def test_text_safe():
    from app.services.text_analysis import TextAnalysisService
    svc = TextAnalysisService()
    result = await svc.analyse("What's the weather like today?", language="en")
    assert result["score"] == 0.0
    assert result["triggers"] == []


@pytest.mark.asyncio
async def test_text_empty():
    from app.services.text_analysis import TextAnalysisService
    svc = TextAnalysisService()
    result = await svc.analyse("", language="en")
    assert result["score"] == 0.0


# ── Danger engine – fuse logic ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_text_only():
    from app.services.danger_engine import DangerDetectionEngine
    engine = DangerDetectionEngine()
    result = await engine.analyse_text_only("Help! Someone is attacking me", language="en")
    # Text alone should produce a non-zero score
    assert result.score > 0


@pytest.mark.asyncio
async def test_engine_safe_audio(mock_registry):
    from app.services.danger_engine import DangerDetectionEngine
    engine = DangerDetectionEngine()
    result = await engine.analyse_audio(SINE_WAV, stt_transcript=None)
    # With models disabled, scores default to 0
    assert result.score == 0.0
    assert result.danger is False


@pytest.mark.asyncio
async def test_engine_danger_via_text(mock_registry):
    from app.services.danger_engine import DangerDetectionEngine
    engine = DangerDetectionEngine()
    result = await engine.analyse_audio(SINE_WAV, stt_transcript="au secours aidez-moi")
    assert result.score > 0
    assert "help_detected" in result.triggers


# ── REST endpoints ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_endpoint(client):
    resp = await client.post(
        "/api/v1/detect",
        files={"audio": ("test.wav", SINE_WAV, "audio/wav")},
        data={"transcript": "everything is fine"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "danger" in data
    assert "score" in data
    assert "triggers" in data
    assert 0.0 <= data["score"] <= 1.0


@pytest.mark.asyncio
async def test_detect_text_endpoint(client):
    resp = await client.post(
        "/api/v1/detect/text",
        json={"text": "Help! I can't breathe!", "language": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["danger"] is True
    assert data["score"] > 0


@pytest.mark.asyncio
async def test_detect_empty_audio(client):
    resp = await client.post(
        "/api/v1/detect",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 400


# ── Test dataset format ───────────────────────────────────────────────────────

EXAMPLE_TEST_DATASET = [
    {
        "id": "safe_001",
        "transcript": "I'd like to order a pizza please",
        "expected_danger": False,
        "expected_score_max": 0.30,
        "tags": ["safe", "normal_conversation"],
    },
    {
        "id": "danger_text_001",
        "transcript": "Help! Someone is breaking into my house!",
        "expected_danger": True,
        "expected_score_min": 0.45,
        "tags": ["danger", "english", "break_in"],
    },
    {
        "id": "danger_text_002",
        "transcript": "Au secours, laissez-moi partir",
        "expected_danger": True,
        "expected_score_min": 0.45,
        "tags": ["danger", "french"],
    },
    {
        "id": "ambiguous_001",
        "transcript": "Stop it, that's not funny",
        "expected_danger": False,   # Low confidence without audio
        "tags": ["ambiguous"],
    },
]


def test_dataset_format():
    """Validate the example dataset schema."""
    for item in EXAMPLE_TEST_DATASET:
        assert "id" in item
        assert "transcript" in item
        assert "expected_danger" in item
