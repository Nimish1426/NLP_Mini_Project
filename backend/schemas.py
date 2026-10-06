"""
schemas.py – Pydantic request / response models for the CultureLens API.

Every field is annotated with a description so FastAPI's auto-generated
docs at /docs are self-explanatory.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Request models ─────────────────────────────────────────────────

class AnalysisOptions(BaseModel):
    """Toggles for individual NLP layers (useful for demos)."""
    use_semantic: bool = Field(True, description="Enable semantic embedding layer")
    use_ml: bool = Field(True, description="Enable ML classifier layer")
    use_tone: bool = Field(True, description="Enable tone analysis layer")


class AnalyzeRequest(BaseModel):
    """Input for the /api/analyze endpoint."""
    text: str = Field(..., min_length=1, max_length=5000,
                      description="English text to analyze (1-5000 chars)")
    source_culture: str = Field(..., description="Culture id of the sender (e.g. 'usa')")
    target_culture: str = Field(..., description="Culture id of the recipient (e.g. 'japan')")
    options: AnalysisOptions = Field(default_factory=AnalysisOptions,
                                     description="Layer toggles")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text must not be blank.")
        return v


# ── Response models ────────────────────────────────────────────────

class FlagResponse(BaseModel):
    """A single flagged phrase or sentence."""
    id: str = Field(..., description="Unique flag identifier")
    text: str = Field(..., description="Exact substring from the input")
    start: int = Field(..., description="Start character offset in the original text")
    end: int = Field(..., description="End character offset in the original text")
    sentence_index: int = Field(..., description="0-based sentence index")
    category: str = Field(..., description="Category of the flag")
    severity: int = Field(..., ge=1, le=3, description="1=low, 2=medium, 3=high")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence 0-1")
    detected_by: str = Field(..., description="Detection layer: rule / semantic / ml / tone")
    explanation: str = Field(..., description="Why this is risky for the target culture")
    literal_meaning_risk: str = Field("", description="What a non-native reader might understand")
    suggestions: List[str] = Field(default_factory=list, description="Suggested alternatives")


class ToneProfile(BaseModel):
    """Tone analysis scores for the overall text."""
    directness: float = Field(..., ge=0.0, le=1.0)
    hedging: float = Field(..., ge=0.0, le=1.0)
    formality: float = Field(..., ge=0.0, le=1.0)
    sentiment: float = Field(..., description="VADER compound score (-1 to 1)")


class CategoryBreakdown(BaseModel):
    """Per-category flag count and risk share."""
    category: str
    count: int
    share: float = Field(..., description="Share of total risk score (0-1)")


class CultureInsight(BaseModel):
    """Information about the target culture for the UI."""
    culture_id: str
    display_name: str
    flag_emoji: str
    communication_tips: List[str]


class TimingsDebug(BaseModel):
    """Per-stage timing in milliseconds (for the 'How it works' panel)."""
    preprocess_ms: float = 0.0
    rules_ms: float = 0.0
    semantic_ms: float = 0.0
    ml_ms: float = 0.0
    tone_ms: float = 0.0
    merge_ms: float = 0.0
    culture_adjust_ms: float = 0.0
    scoring_ms: float = 0.0
    suggest_ms: float = 0.0
    total_ms: float = 0.0


class AnalyzeResponse(BaseModel):
    """Full analysis result returned by POST /api/analyze."""
    flags: List[FlagResponse] = Field(default_factory=list)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_label: str
    category_breakdown: List[CategoryBreakdown] = Field(default_factory=list)
    tone_profile: Optional[ToneProfile] = None
    suggested_rewrite: str = Field("", description="Auto-rewritten text with suggestions applied")
    culture_insight: Optional[CultureInsight] = None
    layers_active: Dict[str, bool] = Field(default_factory=dict)
    debug: TimingsDebug = Field(default_factory=TimingsDebug)


# ── Culture list response ──────────────────────────────────────────

class CultureDimensions(BaseModel):
    """Numeric culture dimensions (0-1 scale)."""
    context_level: float
    directness: float
    power_distance: float
    time_orientation: float
    formality: float


class CultureResponse(BaseModel):
    """A single culture profile for the dropdown."""
    id: str
    display_name: str
    flag_emoji: str
    dimensions: CultureDimensions
    communication_tips: List[str]
    english_proficiency_note: str


# ── Health check ───────────────────────────────────────────────────

class LayersActive(BaseModel):
    rules: bool = True
    semantic: bool = True
    ml: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    layers_active: LayersActive = Field(default_factory=LayersActive)
    version: str = ""


# ── Example messages ───────────────────────────────────────────────

class ExampleMessage(BaseModel):
    """A demo message for the 'Try an example' dropdown."""
    title: str
    text: str
    source_culture: str = "usa"
    target_culture: str = "japan"
