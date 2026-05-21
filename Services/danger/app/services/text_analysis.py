"""
Text Analysis Service – detects danger signals in STT transcripts.

Two levels:
1. Fast keyword / phrase matching (always runs)
2. Optional LLM-based contextual analysis (async, low-latency path uses #1)
"""
import re
import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Pre-compile keyword patterns once at import time
_DANGER_PATTERNS: List[re.Pattern] = [
    re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
    for kw in settings.DANGER_KEYWORDS
]


class TextAnalysisService:

    async def analyse(
        self,
        text: Optional[str],
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Returns:
            {
                "score": float,
                "matched_keywords": list[str],
                "triggers": list[str]
            }
        """
        if not text or not text.strip():
            return self._empty_result()

        matched = self._keyword_match(text)

        if not matched:
            # Optionally run a lightweight heuristic on suspicious syntax
            matched = self._heuristic_match(text)

        score = self._compute_score(matched, text)
        triggers = ["help_detected"] if matched else []

        return {
            "score": score,
            "matched_keywords": matched,
            "triggers": triggers,
        }

    # ── Keyword matching ──────────────────────────────────────────────────────

    def _keyword_match(self, text: str) -> List[str]:
        matched = []
        for pattern in _DANGER_PATTERNS:
            m = pattern.search(text)
            if m:
                matched.append(m.group(0).lower())
        return list(set(matched))

    # ── Simple heuristics for urgent phrases without exact keyword ────────────

    _URGENT_PHRASES = re.compile(
        r"\b(someone|somebody)\s+(is\s+)?(attacking|hurting|following|after)\s+(me|us)\b"
        r"|i\s+(can'?t|cannot)\s+breathe"
        r"|let\s+me\s+(go|out)"
        r"|i'?m\s+(going\s+to\s+)?(die|be\s+killed)",
        re.IGNORECASE,
    )

    def _heuristic_match(self, text: str) -> List[str]:
        m = self._URGENT_PHRASES.search(text)
        return [m.group(0).lower()] if m else []

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _compute_score(self, matched_keywords: List[str], text: str) -> float:
        if not matched_keywords:
            return 0.0
        # Base score per keyword, boost for multiple matches
        base = 0.7
        boost = min(len(matched_keywords) - 1, 3) * 0.1
        # Extra boost if text is very short (a desperate cry is usually terse)
        word_count = len(text.split())
        brevity_boost = 0.1 if word_count <= 5 else 0.0
        return min(base + boost + brevity_boost, 1.0)

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {"score": 0.0, "matched_keywords": [], "triggers": []}
