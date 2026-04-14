from fastapi import FastAPI, WebSocket
from .speech_service import SpeechService
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

app = FastAPI()
speech_service = SpeechService()

@app.websocket("/stt")
async def stt_socket(ws: WebSocket):
    await ws.accept()

    text_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()  # get the loop running this websocket

    recognizer, stream = speech_service.create_recognizer()

    def recognized(evt):
        if evt.result.text:
            # schedule putting text into queue in the correct running loop
            asyncio.run_coroutine_threadsafe(text_queue.put(evt.result.text), loop)

    recognizer.recognized.connect(recognized)
    recognizer.start_continuous_recognition()

    try:
        while True:
            audio_chunk = await ws.receive_bytes()
            stream.write(audio_chunk)

            while not text_queue.empty():
                text = await text_queue.get()
                await ws.send_text(text)

    except Exception as e:
        print("WebSocket closed while receiving audio:", e)

    finally:
        recognizer.stop_continuous_recognition()