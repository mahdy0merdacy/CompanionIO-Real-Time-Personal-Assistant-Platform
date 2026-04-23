from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    stt_url: str = "ws://localhost:8001/stt"
    llm_url: str = "ws://localhost:8002/llm"
    tts_url: str = "ws://localhost:8003/tts"  

settings = Settings()