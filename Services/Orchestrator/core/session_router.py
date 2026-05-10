from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Import auth dependencies from main
from main import get_user_context, require_admin

@router.post("/create")
async def create_session(user: Dict[str, Any] = Depends(get_user_context)):
    """
    Create a new session for the authenticated user.
    """
    try:
        # Your existing session creation logic
        session_id = f"session_{user['user_id']}_{hash(str(user))}"

        logger.info(f"Created session {session_id} for user {user['email']}")

        return {
            "session_id": session_id,
            "user_id": user["user_id"],
            "status": "created"
        }

    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Session creation failed")

@router.get("/{session_id}")
async def get_session(session_id: str, user: Dict[str, Any] = Depends(get_user_context)):
    """
    Get session information (only for session owner).
    """
    # Verify session ownership (implement your logic)
    if not session_id.startswith(f"session_{user['user_id']}_"):
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "session_id": session_id,
        "user_id": user["user_id"],
        "status": "active"
    }

@router.delete("/{session_id}")
async def delete_session(session_id: str, user: Dict[str, Any] = Depends(get_user_context)):
    """
    Delete a session (admin or owner only).
    """
    # Check ownership or admin role
    is_owner = session_id.startswith(f"session_{user['user_id']}_")
    is_admin = "Admin" in user.get("roles", [])

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    # Your session deletion logic here
    logger.info(f"Deleted session {session_id}")

    return {"message": "Session deleted"}

@router.get("/admin/all")
async def get_all_sessions(user: Dict[str, Any] = Depends(require_admin)):
    """
    Admin endpoint to get all sessions.
    """
    # Your admin logic here
    return {"sessions": [], "message": "Admin access granted"}