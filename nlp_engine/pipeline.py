"""
pipeline.py – Orchestrates all NLP layers for CultureLens.

This is the main entry point for text analysis. It runs each layer
in sequence, merges results, adjusts for culture, scores, and
generates suggestions.

Pipeline order:
  preprocess → L1 rules → L2 semantic → L3 ML → tone →
  merge → culture adjust → suggest → score

Each stage is timed so the frontend can display a "How it works" panel.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from nlp_engine.preprocess import preprocess, get_nlp
from nlp_engine.rule_detector import detect as detect_rules, _initialize_matchers
from nlp_engine.semantic_detector import detect as detect_semantic, _initialize_semantic
from nlp_engine.ml_classifier import classify as detect_ml, _initialize_ml
from nlp_engine.tone_analyzer import analyze_tone
from nlp_engine.merge import merge_flags
from nlp_engine.culture_adjuster import adjust_flags
from nlp_engine.scorer import score_text
from nlp_engine.suggester import suggest_rewrite
from nlp_engine.knowledge_base import load_phrases, load_cultures, get_culture

logger = logging.getLogger(__name__)

# ── Engine state ───────────────────────────────────────────────────
_engine_initialized = False
_semantic_available = False
_ml_available = False


def init_engine() -> None:
    """Initialize the NLP engine: load data, warm up models.

    Called once at server startup via FastAPI lifespan. After this,
    analyze() can be called repeatedly with no cold-start penalty.
    """
    global _engine_initialized, _semantic_available, _ml_available

    logger.info("Initializing CultureLens NLP engine …")

    # 1. Load knowledge base
    load_phrases()
    load_cultures()
    logger.info("Knowledge base loaded.")

    # 2. Warm up spaCy (triggers model load)
    nlp = get_nlp()
    nlp("Warm up sentence.")
    logger.info("spaCy model warmed up.")

    # 3. Initialize rule matchers
    _initialize_matchers()
    logger.info("Rule matchers initialized.")

    # 4. Try to initialize semantic layer (may fail gracefully)
    try:
        _initialize_semantic()
        from nlp_engine.semantic_detector import _model as sem_model
        _semantic_available = sem_model is not None
    except Exception as e:
        logger.warning("Semantic layer initialization failed: %s", e)
        _semantic_available = False

    if _semantic_available:
        logger.info("Semantic layer ready.")
    else:
        logger.warning("Semantic layer DISABLED – continuing without it.")

    # 5. Try to initialize ML classifier
    try:
        _initialize_ml()
        from nlp_engine.ml_classifier import _classifier as ml_clf
        _ml_available = ml_clf is not None
    except Exception as e:
        logger.warning("ML classifier initialization failed: %s", e)
        _ml_available = False

    if _ml_available:
        logger.info("ML classifier ready.")
    else:
        logger.warning("ML classifier DISABLED – continuing without it.")

    _engine_initialized = True
    logger.info("NLP engine initialization complete.")


def get_engine_status() -> Dict[str, bool]:
    """Return which layers are currently active.

    Used by the /api/health endpoint.
    """
    return {
        "rules": True,  # rules always available if KB loaded
        "semantic": _semantic_available,
        "ml": _ml_available,
    }


def analyze(
    text: str,
    source_culture: str,
    target_culture: str,
    options: Any = None,
) -> Dict[str, Any]:
    """Run the full CultureLens analysis pipeline.

    Args:
        text: English text to analyze (1-5000 chars).
        source_culture: Culture id of the sender.
        target_culture: Culture id of the recipient.
        options: AnalysisOptions or dict with layer toggles.

    Returns:
        Dict matching the AnalyzeResponse schema.
    """
    if not _engine_initialized:
        init_engine()

    # Normalize options to dict
    if options is None:
        opts = {"use_semantic": True, "use_ml": True, "use_tone": True}
    elif hasattr(options, "model_dump"):
        opts = options.model_dump()
    elif isinstance(options, dict):
        opts = options
    else:
        opts = {"use_semantic": True, "use_ml": True, "use_tone": True}

    timings: Dict[str, float] = {}

    # ── Stage 1: Preprocess ────────────────────────────────────────
    t0 = time.perf_counter()
    prep = preprocess(text)
    timings["preprocess_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 2: Layer 1 – Rule-based detection ────────────────────
    t0 = time.perf_counter()
    flags_l1 = detect_rules(prep)
    timings["rules_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 3: Layer 2 – Semantic detection ──────────────────────
    flags_l2 = []
    t0 = time.perf_counter()
    if opts.get("use_semantic", True) and _semantic_available:
        flags_l2 = detect_semantic(prep, flags_l1)
    timings["semantic_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 4: Layer 3 – ML classifier ───────────────────────────
    flags_l3 = []
    t0 = time.perf_counter()
    if opts.get("use_ml", True) and _ml_available:
        flags_l3 = detect_ml(prep, flags_l1 + flags_l2)
    timings["ml_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 5: Tone analysis ─────────────────────────────────────
    tone_profile = None
    flags_tone = []
    t0 = time.perf_counter()
    if opts.get("use_tone", True):
        tone_profile, flags_tone = analyze_tone(prep, target_culture)
    timings["tone_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 6: Merge ─────────────────────────────────────────────
    t0 = time.perf_counter()
    all_flags = flags_l1 + flags_l2 + flags_l3 + flags_tone
    merged = merge_flags(all_flags)
    timings["merge_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 7: Culture adjustment ────────────────────────────────
    t0 = time.perf_counter()
    adjusted = adjust_flags(merged, source_culture, target_culture)
    timings["culture_adjust_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 8: Scoring ───────────────────────────────────────────
    t0 = time.perf_counter()
    score, label, breakdown = score_text(adjusted, prep.num_sentences)
    timings["scoring_ms"] = (time.perf_counter() - t0) * 1000

    # ── Stage 9: Suggestions ───────────────────────────────────────
    t0 = time.perf_counter()
    rewrite = suggest_rewrite(text, adjusted)
    timings["suggest_ms"] = (time.perf_counter() - t0) * 1000

    timings["total_ms"] = sum(timings.values())

    # ── Build culture insight ──────────────────────────────────────
    target = get_culture(target_culture)
    culture_insight = None
    if target:
        culture_insight = {
            "culture_id": target.id,
            "display_name": target.display_name,
            "flag_emoji": target.flag_emoji,
            "communication_tips": target.communication_tips,
        }

    logger.info(
        "Analysis complete: %d flags, score=%.1f (%s), %.0f ms",
        len(adjusted), score, label, timings["total_ms"],
    )

    return {
        "flags": adjusted,
        "risk_score": round(score, 1),
        "risk_label": label,
        "category_breakdown": breakdown,
        "tone_profile": tone_profile,
        "suggested_rewrite": rewrite,
        "culture_insight": culture_insight,
        "layers_active": {
            "rules": True,
            "semantic": opts.get("use_semantic", True) and _semantic_available,
            "ml": opts.get("use_ml", True) and _ml_available,
            "tone": opts.get("use_tone", True),
        },
        "debug": timings,
    }
