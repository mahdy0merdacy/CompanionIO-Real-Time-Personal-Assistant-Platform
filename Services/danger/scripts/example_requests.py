#!/usr/bin/env python3
"""
Example requests for the Danger Detection Service.

Usage:
  python scripts/example_requests.py
"""
import io
import wave
import struct
import math
import asyncio
import httpx

BASE_URL = "http://localhost:8004/api/v1"


# ── Audio generator ────────────────────────────────────────────────────────────

def generate_test_wav(duration: float = 2.0, sr: int = 16_000) -> bytes:
    n = int(sr * duration)
    samples = [int(0.4 * 32767 * math.sin(2 * math.pi * 440 * t / sr)) for t in range(n)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n}h", *samples))
    return buf.getvalue()


# ── Example 1: health check ────────────────────────────────────────────────────

def ex1_health():
    print("\n── Example 1: Health check ──")
    r = httpx.get("http://localhost:8004/health")
    print(r.json())


# ── Example 2: audio upload ────────────────────────────────────────────────────

def ex2_audio_upload():
    print("\n── Example 2: Audio upload (with transcript) ──")
    wav = generate_test_wav()
    r = httpx.post(
        f"{BASE_URL}/detect",
        files={"audio": ("test.wav", wav, "audio/wav")},
        data={"transcript": "help me please", "language": "en"},
        timeout=30.0,
    )
    print(r.json())


# ── Example 3: text only ───────────────────────────────────────────────────────

def ex3_text_only():
    print("\n── Example 3: Text-only analysis ──")
    r = httpx.post(
        f"{BASE_URL}/detect/text",
        json={"text": "Au secours! Aidez-moi!", "language": "fr"},
    )
    print(r.json())


def ex3b_text_safe():
    print("\n── Example 3b: Safe transcript ──")
    r = httpx.post(
        f"{BASE_URL}/detect/text",
        json={"text": "Can you recommend a good restaurant?", "language": "en"},
    )
    print(r.json())


# ── Example 4: WebSocket streaming ────────────────────────────────────────────

async def ex4_websocket():
    print("\n── Example 4: WebSocket streaming ──")
    import json, websockets
    wav = generate_test_wav(duration=1.0)

    async with websockets.connect("ws://localhost:8004/api/v1/ws/detect") as ws:
        # Send transcript metadata
        await ws.send(json.dumps({
            "type": "transcript",
            "text": "help help please",
            "language": "en",
        }))
        # Send audio chunk
        await ws.send(wav)
        # Read response
        msg = await ws.recv()
        print(json.loads(msg))
        await ws.send(json.dumps({"type": "close"}))


if __name__ == "__main__":
    ex1_health()
    ex2_audio_upload()
    ex3_text_only()
    ex3b_text_safe()
    # asyncio.run(ex4_websocket())   # requires: pip install websockets

    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EQUIVALENT CURL COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Health check
curl http://localhost:8004/health

# Audio upload
curl -X POST http://localhost:8004/api/v1/detect \\
  -F "audio=@/path/to/audio.wav;type=audio/wav" \\
  -F "transcript=help me please" \\
  -F "language=en"

# Text-only
curl -X POST http://localhost:8004/api/v1/detect/text \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Au secours!", "language": "fr"}'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
