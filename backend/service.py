"""
service.py – Thin service layer between FastAPI routes and the NLP engine.

Routes in main.py call these functions. Each function validates input,
calls the engine, and formats the output into Pydantic response models.
This keeps main.py focused on HTTP concerns only.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import HTTPException

from backend.config import APP_VERSION
from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryBreakdown,
    CultureDimensions,
    CultureInsight,
    CultureResponse,
    ExampleMessage,
    FlagResponse,
    HealthResponse,
    LayersActive,
    TimingsDebug,
    ToneProfile,
)
from nlp_engine.knowledge_base import get_culture, get_cultures
from nlp_engine.pipeline import analyze as engine_analyze, get_engine_status

logger = logging.getLogger(__name__)


# ── Health ─────────────────────────────────────────────────────────

def get_health() -> HealthResponse:
    """Return system status and which layers are active."""
    try:
        status = get_engine_status()
    except Exception as e:
        logger.error("Error getting engine status: %s", e)
        status = {"rules": False, "semantic": False, "ml": False}

    return HealthResponse(
        status="ok",
        layers_active=LayersActive(**status),
        version=APP_VERSION,
    )


# ── Cultures ───────────────────────────────────────────────────────

def get_all_cultures() -> List[CultureResponse]:
    """Return all culture profiles for the UI dropdowns."""
    cultures = get_cultures()
    return [
        CultureResponse(
            id=c.id,
            display_name=c.display_name,
            flag_emoji=c.flag_emoji,
            dimensions=CultureDimensions(**c.dimensions),
            communication_tips=c.communication_tips,
            english_proficiency_note=c.english_proficiency_note,
        )
        for c in cultures.values()
    ]


# ── Analysis ───────────────────────────────────────────────────────

def run_analysis(request: AnalyzeRequest) -> AnalyzeResponse:
    """Validate the request, run the engine, format the response.

    Raises HTTPException(422) if a culture id is invalid.
    """
    cultures = get_cultures()

    if request.source_culture not in cultures:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown source culture '{request.source_culture}'. "
                   f"Valid: {sorted(cultures.keys())}",
        )
    if request.target_culture not in cultures:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown target culture '{request.target_culture}'. "
                   f"Valid: {sorted(cultures.keys())}",
        )

    try:
        result = engine_analyze(
            text=request.text,
            source_culture=request.source_culture,
            target_culture=request.target_culture,
            options=request.options,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Analysis error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during analysis.",
        )

    # Format flags into response models
    flags = [
        FlagResponse(
            id=f["id"],
            text=f["text"],
            start=f["start"],
            end=f["end"],
            sentence_index=f["sentence_index"],
            category=f["category"],
            severity=max(1, min(3, f["severity"])),
            confidence=max(0.0, min(1.0, f["confidence"])),
            detected_by=f["detected_by"],
            explanation=f.get("explanation", ""),
            literal_meaning_risk=f.get("literal_meaning_risk", ""),
            suggestions=f.get("suggestions", []),
        )
        for f in result.get("flags", [])
    ]

    # Tone profile
    tp = result.get("tone_profile")
    tone = ToneProfile(**tp) if tp else None

    # Category breakdown
    breakdown = [
        CategoryBreakdown(**b)
        for b in result.get("category_breakdown", [])
    ]

    # Culture insight
    ci = result.get("culture_insight")
    culture_insight = CultureInsight(**ci) if ci else None

    # Timings
    dbg = result.get("debug", {})
    timings = TimingsDebug(
        preprocess_ms=dbg.get("preprocess_ms", 0),
        rules_ms=dbg.get("rules_ms", 0),
        semantic_ms=dbg.get("semantic_ms", 0),
        ml_ms=dbg.get("ml_ms", 0),
        tone_ms=dbg.get("tone_ms", 0),
        merge_ms=dbg.get("merge_ms", 0),
        culture_adjust_ms=dbg.get("culture_adjust_ms", 0),
        scoring_ms=dbg.get("scoring_ms", 0),
        suggest_ms=dbg.get("suggest_ms", 0),
        total_ms=dbg.get("total_ms", 0),
    )

    return AnalyzeResponse(
        flags=flags,
        risk_score=result.get("risk_score", 0),
        risk_label=result.get("risk_label", "Low"),
        category_breakdown=breakdown,
        tone_profile=tone,
        suggested_rewrite=result.get("suggested_rewrite", ""),
        culture_insight=culture_insight,
        layers_active=result.get("layers_active", {}),
        debug=timings,
    )


# ── Examples ───────────────────────────────────────────────────────

def get_examples() -> List[ExampleMessage]:
    """Return 6 pre-built demo messages that showcase different flags."""
    return [
        ExampleMessage(
            title="Business Email",
            text=(
                "Hi Tanaka-san, Let's touch base ASAP and circle back on "
                "the low-hanging fruit. We'll see if we can pull it off by "
                "EOD Friday. Meeting on 03/04/2026. Let me know your "
                "bandwidth. Thanks!"
            ),
            source_culture="usa",
            target_culture="japan",
        ),
        ExampleMessage(
            title="Slack Message",
            text=(
                "Hey team 👋 heads up - we need to hit a home run on this "
                "one. It's a no-brainer that we should think outside the "
                "box. FYI the deadline is soon. No worries if you can't "
                "make it!"
            ),
            source_culture="usa",
            target_culture="germany",
        ),
        ExampleMessage(
            title="Meeting Invite",
            text=(
                "Let's have a quick sync this Friday to go over the Q3 "
                "numbers. I'll try to keep it short. We should be on the "
                "same page before the summer deadline. RSVP by COB."
            ),
            source_culture="usa",
            target_culture="india",
        ),
        ExampleMessage(
            title="Feedback Message",
            text=(
                "To be honest, this isn't good enough. You should have "
                "caught these issues earlier. The code quality needs "
                "immediate improvement. Let me know if you need me to "
                "spell it out for you."
            ),
            source_culture="usa",
            target_culture="japan",
        ),
        ExampleMessage(
            title="Negotiation",
            text=(
                "That's an interesting proposal. We'll see what we can do. "
                "I'll try my best, but it might be difficult to get "
                "approval. Let me think about it and circle back next week."
            ),
            source_culture="uk",
            target_culture="china",
        ),
        ExampleMessage(
            title="Casual Team Chat",
            text=(
                "Yeah right, another all-hands meeting will totally fix "
                "everything 😂 Thanks a lot for the heads up about the "
                "reorg. My bad for not flagging it earlier - I figured "
                "we'd just roll with the punches. Catch you later!"
            ),
            source_culture="usa",
            target_culture="uae",
        ),
    ]
