from fastapi import APIRouter, WebSocket
from app.pipeline import Pipeline

router = APIRouter()

@router.websocket("/chat")
async def orchestrator_ws(ws: WebSocket):
    await ws.accept()
    print("Client connected to orchestrator")

    pipeline = Pipeline(LLM_WS_URL)

    try:
        while True:
            message = await ws.receive_text()
            print("[CLIENT]:", message)

            await pipeline.handle_text(message, ws)

    except Exception as e:
        print("Connection closed:", e)