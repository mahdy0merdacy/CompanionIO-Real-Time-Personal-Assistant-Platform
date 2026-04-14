import asyncio
import sounddevice as sd
import websockets
import numpy as np

SERVER_URL = "ws://127.0.0.1:8000/stt"

SAMPLE_RATE = 16000
CHUNK_SIZE = 3200  # ~0.2s of audio at 16kHz

async def stream_mic():
    loop = asyncio.get_running_loop()

    async with websockets.connect(SERVER_URL) as ws:
        print("Connected to STT server")
        print("Speak into your microphone...\n")

        # Callback runs in a separate thread for audio streaming
        def callback(indata, frames, time, status):
            if status:
                print("Audio callback status:", status)

            # Convert float32 [-1,1] to int16 PCM
            audio_bytes = (indata * 32767).astype(np.int16).tobytes()

            # Schedule async send on the main event loop
            asyncio.run_coroutine_threadsafe(ws.send(audio_bytes), loop)

        # Start streaming audio from microphone
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=callback,
        ):
            try:
                while True:
                    # Wait for server to send transcribed text
                    transcript = await ws.recv()
                    print("\rTranscript: " + transcript, end="")
            except websockets.ConnectionClosed:
                print("\nConnection closed by server.")
            except Exception as e:
                print("\nError:", e)

if __name__ == "__main__":
    asyncio.run(stream_mic())