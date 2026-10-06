"""
tone_analyzer.py – Computes directness, hedging, formality and sentiment.

This module measures the "tone" of the text along four axes and
compares it against the target culture's preferred communication style.
A large mismatch produces a tone_mismatch flag.

NLP concepts used:
  - spaCy dependency parse (imperative detection: root verb with no
    explicit subject in base form)
  - Lexicon-based hedging/directness scoring
  - VADER sentiment for a quick polarity signal
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Tuple

from backend.config import TONE_MISMATCH_THRESHOLD
from nlp_engine.preprocess import PreprocessResult
from nlp_engine.knowledge_base import get_culture

logger = logging.getLogger(__name__)

# ── VADER singleton ────────────────────────────────────────────────
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except ImportError:
    logger.warning("vaderSentiment not installed – sentiment disabled.")
    _vader = None

# ── Lexicons ───────────────────────────────────────────────────────

# Words/phrases that signal hedging or indirectness
HEDGE_WORDS = {
    "maybe", "perhaps", "might", "possibly", "probably",
    "apparently", "seemingly", "arguably", "roughly",
    "sort of", "kind of", "somewhat",
}
HEDGE_PHRASES = [
    "i was wondering if",
    "it would be great if",
    "could possibly",
    "we'll see",
    "let me think about it",
    "i'll try",
    "that might be difficult",
    "not sure if",
    "i think maybe",
    "if you don't mind",
    "would you mind",
    "i suppose",
]

# Words that signal directness / bluntness
DIRECT_WORDS = {"must", "need", "should", "require", "demand", "expect",
                "immediately", "now", "fix", "wrong", "unacceptable",
                "failure", "failed", "stop"}

# Politeness / formality markers
FORMAL_MARKERS = {"dear", "sir", "madam", "kindly", "regards",
                  "sincerely", "respectfully", "esteemed", "honourable",
                  "cordially", "pursuant"}

# Informal markers
INFORMAL_MARKERS = {"hey", "hi", "yo", "gonna", "wanna", "gotta",
                    "lol", "haha", "btw", "nah", "yep", "nope",
                    "cool", "awesome", "dude", "bro"}


def _compute_directness(sent) -> float:
    """Compute a 0-1 directness score for a single sentence.

    High for imperative constructions, 'must/should/need', and blunt phrasing.
    Uses spaCy's dependency parse to detect imperatives (root verb
    with no explicit nsubj and base verb form).
    """
    tokens = sent.tokens
    if not tokens:
        return 0.5

    n_content = max(1, sum(1 for t in tokens if not t.is_punct and not t.is_stop))

    # Count imperative roots: verb as ROOT with no subject, base form
    imperative_count = 0
    for t in tokens:
        if t.pos == "VERB" and t.dep == "ROOT":
            # Check if there's no nsubj child
            has_subject = any(
                other.dep in ("nsubj", "nsubjpass")
                for other in tokens
                if other.idx != t.idx
            )
            if not has_subject:
                imperative_count += 1

    # Count direct/blunt words
    direct_count = sum(1 for t in tokens if t.lemma in DIRECT_WORDS)

    # Blunt negation patterns ("this is wrong", "that won't work")
    text_lower = sent.text.lower()
    blunt_patterns = [
        r"\bthis is (wrong|bad|terrible|unacceptable)\b",
        r"\bthat (won't|will not|doesn't|does not) work\b",
        r"\byou (should have|need to|must|failed)\b",
    ]
    blunt_count = sum(1 for p in blunt_patterns if re.search(p, text_lower))

    score = min(1.0, (imperative_count * 0.3 + direct_count * 0.2 +
                       blunt_count * 0.3) / max(1, n_content / 4))
    return score


def _compute_hedging(sent) -> float:
    """Compute a 0-1 hedging/indirectness score for a sentence.

    High when the sentence contains hedge words, softeners, or
    indirect phrasing.
    """
    text_lower = sent.text.lower()
    n_content = max(1, sum(1 for t in sent.tokens if not t.is_punct))

    # Count single hedge words
    hedge_count = sum(1 for w in HEDGE_WORDS if f" {w} " in f" {text_lower} ")

    # Count hedge phrases
    phrase_count = sum(1 for p in HEDGE_PHRASES if p in text_lower)

    # Modal verbs as hedging signals (could, would, might)
    modal_count = sum(1 for t in sent.tokens
                      if t.lemma in ("could", "would", "might") and t.pos == "AUX")

    score = min(1.0, (hedge_count * 0.15 + phrase_count * 0.25 +
                       modal_count * 0.1) / max(1, n_content / 5))
    return score


def _compute_formality(sent) -> float:
    """Compute a 0-1 formality score for a sentence.

    1.0 = very formal, 0.0 = very informal.
    Based on contractions, slang markers, and politeness markers.
    """
    text_lower = sent.text.lower()

    # Contractions reduce formality
    contraction_pattern = r"(?:'(?:ll|ve|re|s|m|d|t)|n't)\b"
    contractions = len(re.findall(contraction_pattern, text_lower))

    # Formal markers increase formality
    formal_count = sum(1 for w in FORMAL_MARKERS if w in text_lower.split())

    # Informal markers decrease formality
    informal_count = sum(1 for w in INFORMAL_MARKERS if w in text_lower.split())

    # Start with neutral
    score = 0.5
    score += formal_count * 0.15
    score -= contractions * 0.1
    score -= informal_count * 0.12

    return max(0.0, min(1.0, score))


def analyze_tone(
    prep: PreprocessResult,
    target_culture_id: str,
) -> Tuple[Dict, List[Dict]]:
    """Analyze the overall tone of the text and compare to the target culture.

    Args:
        prep: Preprocessed text.
        target_culture_id: Id of the recipient's culture.

    Returns:
        Tuple of (tone_profile dict, list of tone-mismatch flags).
    """
    flags: List[Dict] = []

    directness_scores = []
    hedging_scores = []
    formality_scores = []
    sentiment_scores = []

    for sent in prep.sentences:
        directness_scores.append(_compute_directness(sent))
        hedging_scores.append(_compute_hedging(sent))
        formality_scores.append(_compute_formality(sent))

        if _vader:
            vs = _vader.polarity_scores(sent.text)
            sentiment_scores.append(vs["compound"])
        else:
            sentiment_scores.append(0.0)

    # Average across sentences
    avg = lambda lst: sum(lst) / len(lst) if lst else 0.5
    profile = {
        "directness": round(avg(directness_scores), 3),
        "hedging": round(avg(hedging_scores), 3),
        "formality": round(avg(formality_scores), 3),
        "sentiment": round(avg(sentiment_scores), 3),
    }

    # ── Compare against target culture ─────────────────────────────
    target = get_culture(target_culture_id)
    if target:
        target_direct = target.dimensions.get("directness", 0.5)
        target_formal = target.dimensions.get("formality", 0.5)
        direct_diff = abs(profile["directness"] - target_direct)
        formal_diff = abs(profile["formality"] - target_formal)

        # Directness mismatch
        if direct_diff > TONE_MISMATCH_THRESHOLD:
            direction = "direct" if profile["directness"] > target_direct else "indirect"
            flags.append({
                "id": "tone_directness_mismatch",
                "text": prep.original_text[:min(80, len(prep.original_text))],
                "start": 0,
                "end": len(prep.original_text),
                "sentence_index": 0,
                "category": "tone_mismatch",
                "severity": 2,
                "confidence": min(1.0, direct_diff * 2),
                "detected_by": "tone",
                "explanation": (
                    f"This text is quite {direction} (score: {profile['directness']:.2f}). "
                    f"{target.display_name} business communication typically prefers a "
                    f"directness level around {target_direct:.2f}. "
                    f"Consider adjusting your tone."
                ),
                "literal_meaning_risk": "",
                "suggestions": [
                    "Add polite softeners such as 'Could you please…'" if direction == "direct"
                    else "Be more explicit about your expectations and requests"
                ],
            })

        # Formality mismatch
        if formal_diff > TONE_MISMATCH_THRESHOLD:
            direction = "informal" if profile["formality"] < target_formal else "formal"
            flags.append({
                "id": "tone_formality_mismatch",
                "text": prep.original_text[:min(80, len(prep.original_text))],
                "start": 0,
                "end": len(prep.original_text),
                "sentence_index": 0,
                "category": "tone_mismatch",
                "severity": 1,
                "confidence": min(1.0, formal_diff * 2),
                "detected_by": "tone",
                "explanation": (
                    f"The formality level ({profile['formality']:.2f}) may not match "
                    f"{target.display_name}'s expected level ({target_formal:.2f}). "
                    f"The text feels {direction} for this audience."
                ),
                "literal_meaning_risk": "",
                "suggestions": [
                    "Use more formal greetings and sign-offs" if direction == "informal"
                    else "A slightly less formal tone may be appropriate"
                ],
            })

    return profile, flags
