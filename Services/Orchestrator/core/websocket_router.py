from fastapi import APIRouter, WebSocket, Depends, HTTPException
from typing import Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Import auth dependencies from main
from main import get_user_context

@router.websocket("/session/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user: Dict[str, Any] = Depends(get_user_context)
):
    """
    WebSocket endpoint with authentication.
    """
    await websocket.accept()

    try:
        # Verify session ownership
        if not session_id.startswith(f"session_{user['user_id']}_"):
            await websocket.send_json({"error": "Access denied"})
            await websocket.close()
            return

        # Your existing WebSocket logic here
        while True:
            data = await websocket.receive_text()
            # Process voice/text data
            response = f"Echo: {data}"
            await websocket.send_text(response)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()