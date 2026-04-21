import asyncio
from core.mailbox import Mailbox
from core.pipeline import run_pipeline
from clients.stt_client import STTClient
from clients.llm_client import LLMClient



class SessionActor:
    """
    one actor l kol utilisateur,
    owns: conversation history, pipeline state lkol session.
    yahki maa l websocket bl output_queue{redis streaming later}
    """

    def __init__(self,session_id:str,stt:STTClient,llm:LLMClient):
        self.session_id=session_id
        self.stt=stt
        self.llm=llm
        self.history:list[dict]=[]
        self.mailbox=Mailbox()
        self.output_queue:asyncio.Queue=asyncio.Queue()
        self._task:asyncio.Task | None=None
        self._stt_task:asyncio.Task | None=None
        self.full_transcript = ""

    async def start(self):
        await self.stt.connect()
        self._stt_task = asyncio.create_task(self._stt_loop())
        self._task=asyncio.create_task(self._run())
    
    async def send(self,msg:dict):
        """websocket endpoint testaamel hedhy bsh tabeeth message ll
          actor

        """
        await self.mailbox.enqueue(msg)
    
    async def recv(self) -> str | bytes:
        """websocket endpoint kif kif testaamel hedhy
            bsh tabeeth output ll client
        """
        return await self.output_queue.get()
     
     
     # ── internal
    async def _run(self):
        """loop actor: process kol message mara"""
        while True:
            msg = await self.mailbox.dequeue()
            if msg["type"]=="audio":
                await self._handle_audio(msg["data"])
            elif msg["type"]=="turn_end":
                await self._handle_turn_end()  # NEW: handle explicit turn boundaries
            elif msg["type"]=="stop":
                await self._handle_close()
                break
    
    async def _stt_loop(self):
        """Background task to receive transcripts from STT and accumulate them"""
        while True:
            try:
                transcript = await self.stt.recv_text()
                if transcript:
                    print(f"[ACTOR] Received transcript: {transcript}")
                    # Azure's Recognized event is already an utterance boundary.
                    # Treat each received transcript as a final utterance and
                    # trigger LLM processing without trying to detect silence here.
                    self.full_transcript = transcript.strip()
                    await self.output_queue.put({"type": "transcript", "data": transcript})
                    self.history.append({"role": "user", "content": transcript})
                    # Launch LLM handling in background so STT loop keeps receiving
                    asyncio.create_task(self._handle_turn_end(self.full_transcript))
            except Exception as e:
                print(f"[ACTOR] STT loop error: {e}")
                break

    async def _handle_turn_end(self, prompt: str | None = None):
        """Process end of user's utterance: send transcript to LLM and stream response.

        If `prompt` is provided we use that snapshot; otherwise we fall back
        to `self.full_transcript` (used for session-close flashing).
        """
        if prompt is None:
            prompt = self.full_transcript.strip()

        if not prompt:
            print(f"[ACTOR] Turn ended but no transcript to process")
            return

        print(f"[ACTOR] Turn complete. Processing: {prompt}")
        try:
            # Get fresh LLM connection for this utterance
            await self.llm.connect()
            print(f"[ACTOR] Sending to LLM and streaming response...")
            async for token in self.llm.generate(prompt):
                await self.output_queue.put({"type": "token", "data": token})
            # Signal end of LLM turn (non-terminal marker)
            await self.output_queue.put({"type": "turn_complete"})
        except Exception as e:
            print(f"[ACTOR] LLM error: {e}")
            await self.output_queue.put({"type": "error", "data": str(e)})
        finally:
            # Only reset the accumulated transcript if we consumed the internal buffer
            # (i.e. prompt was taken from self.full_transcript). If a prompt was
            # explicitly supplied, leave self.full_transcript alone.
            if prompt == self.full_transcript.strip():
                self.full_transcript = ""

    async def _handle_audio(self,audio:bytes):
        await self.stt.send_audio(audio)
    
    async def _handle_close(self):
        """Clean up when session ends"""
        # Stop STT loop
        if self._stt_task:
            self._stt_task.cancel()
            try:
                await self._stt_task
            except asyncio.CancelledError:
                pass
        
        # If there's a pending transcript when session closes, send it to LLM
        if self.full_transcript.strip():
            print(f"[ACTOR] Session ending with pending transcript. Sending to LLM: {self.full_transcript.strip()}")
            if not self.llm._ws:
                await self.llm.connect()
            async for token in self.llm.generate(self.full_transcript.strip()):
                await self.output_queue.put({"type": "token", "data": token})
        
        await self.output_queue.put({"type": "turn_end"})
    
    async def stop(self):  # ✅ ADD THIS
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            
            

            
