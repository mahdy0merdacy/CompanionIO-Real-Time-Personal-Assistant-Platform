import websockets
import asyncio
import re
from typing import AsyncGenerator, Callable
from clients.llm_client import LLMClient
from clients.stt_client import STTClient


SENTENCE_END = re.compile(r'[.!?]\s*$')

async def run_pipeline(
        audio_chunk:bytes,
        stt:STTClient,
        llm:LLMClient,
        on_transcript:callable[[str],None]=None,
) -> AsyncGenerator[str,None]:
    print(f"🎤 [PIPELINE] Received {len(audio_chunk)} bytes")  # ✅ ADD THIS
    """
    phase1: audio->transcript via STT
    phase2: transcript->token via LLM
    phase3: token->voice via STT"""
    
    #phase 1
    await stt.send_audio(audio_chunk)
    print("🎤 [PIPELINE] Sent to STT, waiting for transcripts...")

    transcript = ""
    try:
        while True:
            text = await stt.recv_text()
            if text is None:
                break
            print(f"🎤 [PIPELINE] Received transcript: '{text}'")
            transcript += text + " "
    except Exception as e:
        print(f"🎤 [PIPELINE] STT connection closed: {e}")
    
    if not transcript:
        print("🎤 [PIPELINE] No transcript received - returning empty")
        return
    
    transcript = transcript.strip()
    print(f"🎤 [PIPELINE] Final transcript: '{transcript}'")
    if on_transcript:
        on_transcript(transcript)

    #phase 2
    async for token in llm.generate(transcript):
        yield token     




        
'''
class Pipeline:
    def __init__(self, llm_url: str):
        self.llm_url = LLMClient(llm_url)

    async def handle_text(self, text: str, client_ws):
        print("[PIPELINE → LLM]:", text)

        async with websockets.connect(self.llm_url) as llm_ws:
            await llm_ws.send(text)

            async for token in llm_ws:
                if token == "<END>":
                    break

                print("[LLM TOKEN]:", token)
                await client_ws.send_text(token)'''