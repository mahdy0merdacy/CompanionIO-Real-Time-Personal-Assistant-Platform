from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
import asyncio

from .tts_service import TTSService

load_dotenv()

app = FastAPI()
tts_service = TTSService()


@app.websocket("/tts")
async def tts_socket(ws: WebSocket):
    await ws.accept()
    print("[TTS] 🔌 client connected")

    loop = asyncio.get_running_loop()

    try:
        while True:
            text = await ws.receive_text()
            print(f"[TTS] 📝 received text: {text}")

            # queue to send audio chunks back
            audio_queue = asyncio.Queue()

            # Azure callback (runs in separate thread)
           
            class AudioStreamCallback:
                def __init__(self, queue, loop):
                    self.queue = queue
                    self.loop = loop

                def write(self, data: memoryview):
                    chunk = bytes(data)

                    print(f"[TTS CALLBACK] 🎵 chunk: {len(chunk)} bytes")

                    asyncio.run_coroutine_threadsafe(
                        self.queue.put(chunk),
                        self.loop
                    )

                    return len(data)

                def close(self):
                    print("[TTS CALLBACK] 🔒 stream closed")
                    
            audio_callback = AudioStreamCallback(audio_queue, loop)        

            synthesizer = tts_service.create_synthesizer(audio_callback)

            # trigger synthesis (non-blocking)
            result=synthesizer.speak_text_async(text).get()

            print("[TTS] ▶️ synthesis started",result.reason)

            # stream audio chunks back
            while True:
                try:
                    chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                    await ws.send_bytes(chunk)
                except asyncio.TimeoutError:
                    print("[TTS] ⏹️ synthesis finished")
                    break

    except Exception as e:
        print("[TTS] ❌ error:", e)

    finally:
        print("[TTS] 🔴 client disconnected")

















































































































































