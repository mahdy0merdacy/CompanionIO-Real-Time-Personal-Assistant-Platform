"""
orchestrator_integration.py
───────────────────────────
Example showing exactly how to integrate the Danger Detection Service
into your existing CompanionIO orchestrator.

This file is NOT part of the danger-detection-service itself – it lives
in your orchestrator codebase.
"""
import asyncio
import logging
import httpx
from typing import Optional

logger = logging.getLogger("orchestrator")

DANGER_DETECTION_URL = "http://danger-detection-service:8004/api/v1"


# ── Helper client (reuse a single httpx.AsyncClient per orchestrator instance) ─

class DangerDetectionClient:
    def __init__(self, base_url: str = DANGER_DETECTION_URL, timeout: float = 3.0):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def check_audio(
        self,
        audio_bytes: bytes,
        stt_transcript: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Call /detect with the raw audio chunk and (optionally) the STT transcript.
        Returns the DangerResponse dict.
        """
        files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"language": language}
        if stt_transcript:
            data["transcript"] = stt_transcript

        resp = await self._client.post(
            f"{self.base_url}/detect",
            files=files,
            data=data,
        )
        resp.raise_for_status()
        return resp.json()

    async def check_text(self, text: str, language: str = "en") -> dict:
        """Faster text-only screening (call before STT audio is ready)."""
        resp = await self._client.post(
            f"{self.base_url}/detect/text",
            json={"text": text, "language": language},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._client.aclose()


# ── Where to call it in your pipeline ─────────────────────────────────────────

danger_client = DangerDetectionClient()


async def orchestrator_pipeline(audio_chunk: bytes, session_id: str):
    """
    Simplified version of your existing orchestrator pipeline,
    showing exactly where danger detection is inserted.

    Pipeline order:
      1. STT  (speech-to-text)
      2. DANGER CHECK  ← inserted here, runs concurrently with LLM
      3. LLM  (language model response)
      4. TTS  (text-to-speech)
    """

    # ── Step 1: STT ───────────────────────────────────────────────────────────
    transcript = await call_stt_service(audio_chunk)
    logger.info(f"[{session_id}] STT: {transcript!r}")

    # ── Step 2: Danger detection (concurrent with LLM for zero added latency) ─
    danger_task = asyncio.create_task(
        danger_client.check_audio(
            audio_chunk,
            stt_transcript=transcript,
            language="en",
        )
    )

    # ── Step 3: LLM (runs while danger detection is in flight) ────────────────
    llm_response_task = asyncio.create_task(
        call_llm_service(transcript)
    )

    # Await both; danger check is typically much faster than LLM
    danger_result, llm_response = await asyncio.gather(danger_task, llm_response_task)

    # ── Handle danger signal ───────────────────────────────────────────────────
    if danger_result["danger"]:
        score = danger_result["score"]
        triggers = danger_result["triggers"]
        logger.warning(
            f"[{session_id}] ⚠️  DANGER – score={score:.2f} triggers={triggers}"
        )
        await handle_danger_alert(session_id, danger_result)
        # Optionally override LLM response with a safety message
        llm_response = build_safety_response(danger_result)

    # ── Step 4: TTS ───────────────────────────────────────────────────────────
    audio_response = await call_tts_service(llm_response)
    return audio_response


# ── Alert handler ──────────────────────────────────────────────────────────────

async def handle_danger_alert(session_id: str, danger_result: dict):
    """
    Examples of what you might do when danger is detected:
      - Notify a human operator via Slack/PagerDuty
      - Log to an incident database
      - Send an in-app alert to the frontend via WebSocket
      - Trigger an automated emergency callback
    """
    logger.critical(
        f"DANGER ALERT | session={session_id} | "
        f"score={danger_result['score']} | triggers={danger_result['triggers']}"
    )
    # await notify_operator(session_id, danger_result)
    # await push_alert_to_frontend(session_id, danger_result)


def build_safety_response(danger_result: dict) -> str:
    return (
        "I've detected that you might be in distress. "
        "If you're in danger, please call emergency services immediately (112 / 911). "
        "Help is available."
    )


# ── Stub functions (replace with your real service calls) ─────────────────────

async def call_stt_service(audio_bytes: bytes) -> str:
    await asyncio.sleep(0.05)   # simulate STT latency
    return "help me please"


async def call_llm_service(transcript: str) -> str:
    await asyncio.sleep(0.2)    # simulate LLM latency
    return f"I heard: {transcript}"


async def call_tts_service(text: str) -> bytes:
    await asyncio.sleep(0.05)   # simulate TTS latency
    return b"<audio bytes>"


# ── Quick demo ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import struct, wave, io, math

    def make_wav(duration=2.0, sr=16000):
        n = int(sr * duration)
        samples = [int(0.3 * 32767 * math.sin(2 * math.pi * 440 * t / sr)) for t in range(n)]
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{n}h", *samples))
        return buf.getvalue()

    audio = make_wav()
    result = asyncio.run(orchestrator_pipeline(audio, session_id="demo-001"))
    print("Pipeline complete.")
