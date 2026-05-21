"""
API Routes for the Danger Detection Service.

Endpoints:
  POST /api/v1/detect          – multipart audio upload (+ optional transcript)
  POST /api/v1/detect/text     – text-only analysis
  WS   /api/v1/ws/detect       – real-time streaming (chunk-by-chunk)
"""
import logging
import asyncio
import json
from typing import Optional

from fastapi import (
    APIRouter, UploadFile, File, Form, HTTPException,
    WebSocket, WebSocketDisconnect, status,
)
from fastapi.responses import JSONResponse

from app.models.schemas import DangerResponse, TextAnalysisRequest
from app.services.danger_engine import DangerDetectionEngine
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# One engine instance, reused across requests (stateless)
_engine = DangerDetectionEngine()


# ── REST: audio upload ─────────────────────────────────────────────────────────

@router.post(
    "/detect",
    response_model=DangerResponse,
    summary="Detect danger from an audio file",
    responses={
        400: {"description": "Invalid or too-short audio"},
        503: {"description": "Models not yet loaded"},
    },
)
async def detect_from_audio(
    audio: UploadFile = File(..., description="Audio file (wav/mp3/ogg/flac/webm)"),
    transcript: Optional[str] = Form(None, description="STT transcript (optional, speeds up text analysis)"),
    language: str = Form("en", description="Language of the transcript"),
    chunked: bool = Form(False, description="Use chunk-based analysis for long recordings"),
):
    """
    Primary endpoint consumed by the CompanionIO orchestrator.

    - Accepts any common audio format
    - Optionally accepts the STT transcript from the upstream STT service
    - Returns a DangerResponse JSON
    """
    from app.core.model_registry import ModelRegistry
    if not ModelRegistry.get_instance().all_loaded():
        raise HTTPException(status_code=503, detail="Models not yet loaded")

    audio_bytes = await audio.read()
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio payload too small")

    try:
        if chunked:
            result = await _engine.analyse_audio_chunked(audio_bytes, transcript, language)
        else:
            result = await _engine.analyse_audio(audio_bytes, transcript, language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


# ── REST: text-only ────────────────────────────────────────────────────────────

@router.post(
    "/detect/text",
    response_model=DangerResponse,
    summary="Detect danger from transcript text only",
)
async def detect_from_text(body: TextAnalysisRequest):
    """
    Lightweight endpoint for scenarios where only the STT transcript is available.
    Useful for the orchestrator's fallback path or keyword-based pre-screening.
    """
    result = await _engine.analyse_text_only(body.text, body.language)
    return result


# ── WebSocket: real-time streaming ────────────────────────────────────────────

@router.websocket("/ws/detect")
async def websocket_detect(websocket: WebSocket):
    """
    Real-time danger detection over WebSocket.

    Protocol (client → server):
      Each message is either:
      a) Raw audio bytes  → engine analyses the chunk
      b) JSON string:  {"type": "transcript", "text": "...", "language": "en"}
      c) JSON string:  {"type": "close"}

    Protocol (server → client):
      JSON DangerResponse after each audio chunk, e.g.:
      {"danger": false, "score": 0.12, "triggers": [], "details": {...}}

      On danger=True an extra field is added:
      {"danger": true, ..., "alert": "DANGER_DETECTED"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: {websocket.client}")

    current_transcript: Optional[str] = None
    current_language: str = "en"

    try:
        while True:
            # Use a receive timeout so we can detect stale connections
            try:
                raw = await asyncio.wait_for(websocket.receive(), timeout=60.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            # Control message (JSON text)
            if "text" in raw:
                try:
                    msg = json.loads(raw["text"])
                    if msg.get("type") == "transcript":
                        current_transcript = msg.get("text")
                        current_language = msg.get("language", "en")
                    elif msg.get("type") == "close":
                        break
                except json.JSONDecodeError:
                    pass
                continue

            # Audio chunk (binary)
            if "bytes" in raw and raw["bytes"]:
                audio_chunk = raw["bytes"]
                try:
                    result = await _engine.analyse_audio(
                        audio_chunk, current_transcript, current_language
                    )
                    payload = result.model_dump()
                    if result.danger:
                        payload["alert"] = "DANGER_DETECTED"
                    await websocket.send_json(payload)
                except ValueError as e:
                    await websocket.send_json({"error": str(e)})
                except Exception as e:
                    logger.error(f"WS analysis error: {e}")
                    await websocket.send_json({"error": "Internal analysis error"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
