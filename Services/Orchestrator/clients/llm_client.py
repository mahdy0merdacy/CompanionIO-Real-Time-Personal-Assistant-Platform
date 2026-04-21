import websockets
from typing import AsyncGenerator

class LLMClient:
    """
    interface ll LLM service:
    -yabaath: string (transcript mtaa LSTT)
    -yrajaa:token string (reponse) lli tousel "<END>" 
    """
    def __init__(self, url:str):
        self.url = url
        self._ws=None
    
    async def connect(self):
        self._ws=await websockets.connect(self.url)
    
    async def generate(self,prompt:str)->AsyncGenerator[str,None]:
        await self._ws.send(prompt)


        async for token in self._ws:
            if token =="<END>":
                break
            yield token
        
    async def close(self):
        if self._ws:
            await self._ws.close()
            
