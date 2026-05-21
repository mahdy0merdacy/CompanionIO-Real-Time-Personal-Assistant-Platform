"""
Pydantic schemas for the Danger Detection Service API.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class DangerResponse(BaseModel):
    """Primary response returned to the orchestrator."""
    danger: bool = Field(..., description="True when danger score ≥ threshold")
    score: float = Field(..., ge=0.0, le=1.0, description="Composite danger score (0–1)")
    triggers: List[str] = Field(..., description="Which signals fired")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Per-signal scores and top detections (for debugging / dashboards)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "danger": True,
                "score": 0.82,
                "triggers": ["screaming_detected", "fear_detected", "help_detected"],
                "details": {
                    "sound_score": 0.91,
                    "emotion_score": 0.76,
                    "text_score": 1.0,
                    "top_sounds": ["Screaming", "Shout"],
                    "top_emotion": "fea",
                    "matched_keywords": ["help"],
                },
            }
        }


class TextAnalysisRequest(BaseModel):
    """For text-only danger analysis (when STT output is already available)."""
    text: str
    language: Optional[str] = "en"


class PipelineAnalysisRequest(BaseModel):
    """
    Compound request from the orchestrator when both audio and STT text
    are already available (most efficient path).
    """
    stt_transcript: Optional[str] = None
    language: Optional[str] = "en"
    # audio is sent as multipart alongside this JSON body
