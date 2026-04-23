import asyncio
from core.actor import SessionActor
from clients.stt_client import STTClient
from clients.llm_client import LLMClient
from clients.tts_client import TTSClient
from core.settings import settings

class SessionSupervisor:
      
    def __init__(self):
        self._actors = {}


    """
    kima l master fl hadoop, khedmtou anou yspawni w yetracki kol actor.
    kol actor = utilisateur fl front(presque).
    kol utilistateur= andou connection mtaou ll STT wl LLM
    """

    async def spawn(self,session_id:str) -> SessionActor:
        #naffectiow lkol session services connections mtaeha
        stt=STTClient(settings.stt_url)
        llm=LLMClient(settings.llm_url)
        tts=TTSClient(settings.tts_url)
        
        await stt.connect()  
        await llm.connect()  
        await tts.connect()

        actor =SessionActor(session_id,stt,llm,tts)
        await actor.start()
        self._actors[session_id]=actor
        return actor 
    
    
    async def get(self,session_id:str) -> SessionActor | None:
        return self._actors.get(session_id)
    

    
    
    async def terminate(self, session_id:str):
        actor=self._actors.pop(session_id,None)
        if actor:
            await actor.stop()
            await actor.stt.close()
            await actor.llm.close()
            await actor.tts.close()
    
    @property
    def active_sessions(self) -> int:
        return len(self._actors)
    