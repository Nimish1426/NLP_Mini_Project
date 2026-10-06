"""
knowledge_base.py – Loads and validates the JSON data files.

Provides typed access to:
  - phrases.json   (risky phrases knowledge base)
  - cultures.json  (culture profiles with dimensions)

Validates every entry at load time and fails loudly with a readable
error naming the bad entry if anything is wrong.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import (
    CULTURES_PATH,
    PHRASES_PATH,
    VALID_CATEGORIES,
)

logger = logging.getLogger(__name__)

# Categories that come from phrases.json (not tone_mismatch or sentence_level)
PHRASE_CATEGORIES = frozenset([
    "idiom", "slang", "sports_metaphor", "military_metaphor",
    "corporate_jargon", "vague_time", "date_format", "units_numbers",
    "indirect_refusal", "hedging", "blunt_feedback", "sarcasm_humor",
    "politeness_formula", "cultural_reference", "phrasal_verb",
])


# ── Data classes ───────────────────────────────────────────────────

@dataclass
class PhraseEntry:
    """A single entry from phrases.json."""
    id: str
    phrase: str
    pattern_type: str           # "lemma_phrase" | "regex" | "token_pattern"
    category: str
    base_severity: int          # 1, 2 or 3
    meaning: str
    risk_note: str
    examples: List[str]
    plain_alternatives: List[str]
    affected_cultures: List[str]  # empty list means all cultures
    origin_note: str = ""


@dataclass
class CultureProfile:
    """A single culture profile from cultures.json."""
    id: str
    display_name: str
    flag_emoji: str
    dimensions: Dict[str, float]     # context_level, directness, …
    dimension_notes: Dict[str, str]
    english_proficiency_note: str
    category_modifiers: Dict[str, float]
    communication_tips: List[str]


# ── Singleton storage ──────────────────────────────────────────────

_phrases: Optional[List[PhraseEntry]] = None
_phrases_by_id: Optional[Dict[str, PhraseEntry]] = None
_cultures: Optional[Dict[str, CultureProfile]] = None


# ── Validation helpers ─────────────────────────────────────────────

def _validate_phrase(raw: Dict[str, Any], idx: int) -> PhraseEntry:
    """Validate a single phrase entry and return a PhraseEntry.

    Raises ValueError with a descriptive message if anything is wrong.
    """
    entry_id = raw.get("id", f"<entry at index {idx}>")

    required = ["id", "phrase", "pattern_type", "category",
                 "base_severity", "meaning", "risk_note",
                 "examples", "plain_alternatives", "affected_cultures"]
    for fld in required:
        if fld not in raw:
            raise ValueError(
                f"Phrase entry '{entry_id}': missing required field '{fld}'."
            )

    cat = raw["category"]
    if cat not in PHRASE_CATEGORIES:
        raise ValueError(
            f"Phrase entry '{entry_id}': invalid category '{cat}'. "
            f"Must be one of: {sorted(PHRASE_CATEGORIES)}"
        )

    sev = raw["base_severity"]
    if sev not in (1, 2, 3):
        raise ValueError(
            f"Phrase entry '{entry_id}': base_severity must be 1, 2 or 3 "
            f"(got {sev})."
        )

    pt = raw["pattern_type"]
    if pt not in ("lemma_phrase", "regex", "token_pattern"):
        raise ValueError(
            f"Phrase entry '{entry_id}': invalid pattern_type '{pt}'."
        )

    return PhraseEntry(
        id=raw["id"],
        phrase=raw["phrase"],
        pattern_type=raw["pattern_type"],
        category=raw["category"],
        base_severity=raw["base_severity"],
        meaning=raw["meaning"],
        risk_note=raw["risk_note"],
        examples=raw["examples"],
        plain_alternatives=raw["plain_alternatives"],
        affected_cultures=raw["affected_cultures"],
        origin_note=raw.get("origin_note", ""),
    )


def _validate_culture(raw: Dict[str, Any]) -> CultureProfile:
    """Validate a single culture profile."""
    cid = raw.get("id", "<unknown>")

    required = ["id", "display_name", "flag_emoji", "dimensions",
                 "english_proficiency_note", "category_modifiers",
                 "communication_tips"]
    for fld in required:
        if fld not in raw:
            raise ValueError(
                f"Culture '{cid}': missing required field '{fld}'."
            )

    dims = raw["dimensions"]
    for dim_name in ["context_level", "directness", "power_distance",
                     "time_orientation", "formality"]:
        if dim_name not in dims:
            raise ValueError(
                f"Culture '{cid}': missing dimension '{dim_name}'."
            )
        val = dims[dim_name]
        if not (0.0 <= val <= 1.0):
            raise ValueError(
                f"Culture '{cid}': dimension '{dim_name}' must be 0-1 "
                f"(got {val})."
            )

    return CultureProfile(
        id=raw["id"],
        display_name=raw["display_name"],
        flag_emoji=raw["flag_emoji"],
        dimensions=raw["dimensions"],
        dimension_notes=raw.get("dimension_notes", {}),
        english_proficiency_note=raw["english_proficiency_note"],
        category_modifiers=raw["category_modifiers"],
        communication_tips=raw["communication_tips"],
    )


# ── Public loaders ─────────────────────────────────────────────────

def load_phrases(path: Optional[Path] = None) -> List[PhraseEntry]:
    """Load and validate phrases.json. Caches after first call.

    Args:
        path: Override path for testing. Defaults to config.PHRASES_PATH.

    Returns:
        List of validated PhraseEntry objects.

    Raises:
        FileNotFoundError: if the file doesn't exist.
        ValueError: if any entry fails validation.
    """
    global _phrases, _phrases_by_id
    if _phrases is not None and path is None:
        return _phrases

    p = path or PHRASES_PATH
    if not p.exists():
        raise FileNotFoundError(f"Phrases file not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    entries = [_validate_phrase(r, i) for i, r in enumerate(raw_list)]
    logger.info("Loaded %d phrase entries from %s", len(entries), p)

    if path is None:
        _phrases = entries
        _phrases_by_id = {e.id: e for e in entries}

    return entries


def load_cultures(path: Optional[Path] = None) -> Dict[str, CultureProfile]:
    """Load and validate cultures.json. Caches after first call.

    Returns:
        Dict mapping culture id → CultureProfile.
    """
    global _cultures
    if _cultures is not None and path is None:
        return _cultures

    p = path or CULTURES_PATH
    if not p.exists():
        raise FileNotFoundError(f"Cultures file not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    profiles = {}
    for raw in raw_list:
        cp = _validate_culture(raw)
        profiles[cp.id] = cp

    logger.info("Loaded %d culture profiles from %s", len(profiles), p)

    if path is None:
        _cultures = profiles

    return profiles


def get_phrases() -> List[PhraseEntry]:
    """Return cached phrases (must call load_phrases first)."""
    if _phrases is None:
        return load_phrases()
    return _phrases


def get_phrase_by_id(phrase_id: str) -> Optional[PhraseEntry]:
    """Look up a phrase by its id."""
    if _phrases_by_id is None:
        load_phrases()
    return _phrases_by_id.get(phrase_id) if _phrases_by_id else None


def get_cultures() -> Dict[str, CultureProfile]:
    """Return cached cultures (must call load_cultures first)."""
    if _cultures is None:
        return load_cultures()
    return _cultures


def get_culture(culture_id: str) -> Optional[CultureProfile]:
    """Look up a single culture by id."""
    cultures = get_cultures()
    return cultures.get(culture_id)
