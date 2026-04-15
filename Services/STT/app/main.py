from fastapi import FastAPI, WebSocket
from .speech_service import SpeechService
from dotenv import load_dotenv
import asyncio
import websockets
import time

load_dotenv()

app = FastAPI()
speech_service = SpeechService()

LLM_URL = "ws://127.0.0.1:8002/llm"


@app.websocket("/stt")
async def stt_socket(ws: WebSocket):
    await ws.accept()

    loop = asyncio.get_running_loop()

    # queue for Azure callback → async world
    text_queue = asyncio.Queue()

    # connect to LLM
    llm_ws = await websockets.connect(LLM_URL)

    recognizer, stream = speech_service.create_recognizer()

    # ---------------------------
    # Azure callback (THREAD)
    # ---------------------------
    def recognized(evt):
        if evt.result.text:
            asyncio.run_coroutine_threadsafe(
                text_queue.put(evt.result.text),
                loop
            )

    recognizer.recognized.connect(recognized)
    recognizer.start_continuous_recognition()
    
    # ---------------------------
    # main loop
    # ---------------------------
    try:
        while True:
         audio_chunk = await ws.receive_bytes()
         stream.write(audio_chunk)

         while not text_queue.empty():
            text = await text_queue.get()

            await llm_ws.send(text)
            await ws.send_text(text)

            response = ""
  
            while True:
              token = await llm_ws.recv()
              if token == "<END>":
                  break

            response += token
            await ws.send_text(token)

    except Exception as e:
        print("WebSocket closed:", e)

    finally:
        recognizer.stop_continuous_recognition()
        await llm_ws.close()