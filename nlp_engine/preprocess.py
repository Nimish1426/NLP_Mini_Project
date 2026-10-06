"""
preprocess.py – spaCy loading, sentence splitting, tokenization.

This module is the entry point for all text processing. It loads the
spaCy model ONCE (singleton) and provides helpers that every other
module relies on.

Key concepts used here:
  - Tokenization: splitting text into words (tokens)
  - Lemmatization: reducing words to their base form ("touching" → "touch")
  - Sentence segmentation: splitting text into sentences
  - Character-offset mapping: every token keeps a pointer back to its
    position in the ORIGINAL text so highlights are accurate.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span

from backend.config import MAX_INPUT_LENGTH, MIN_INPUT_LENGTH

logger = logging.getLogger(__name__)

# ── Singleton spaCy model ─────────────────────────────────────────
_nlp: Optional[Language] = None


def get_nlp() -> Language:
    """Load spaCy en_core_web_sm once and return it.

    The model provides tokenization, POS tagging, lemmatization,
    dependency parsing and sentence segmentation – all on CPU in
    a few milliseconds.
    """
    global _nlp
    if _nlp is None:
        logger.info("Loading spaCy model en_core_web_sm …")
        _nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model loaded.")
    return _nlp


# ── Data classes ───────────────────────────────────────────────────

@dataclass
class TokenInfo:
    """A single token with its metadata and original-text offsets."""
    text: str               # surface form as it appears in the input
    lemma: str              # base form (e.g. "touching" → "touch")
    pos: str                # part-of-speech tag (NOUN, VERB, …)
    dep: str                # dependency label (nsubj, ROOT, …)
    idx: int                # character start offset in original text
    end_idx: int            # character end offset in original text
    is_stop: bool           # True for "the", "is", "a", …
    is_punct: bool          # True for ".", ",", "!", …


@dataclass
class SentenceInfo:
    """A single sentence extracted from the input."""
    text: str               # raw text of the sentence
    start: int              # char start offset in original text
    end: int                # char end offset in original text
    index: int              # 0-based sentence index
    tokens: List[TokenInfo] = field(default_factory=list)
    doc: Optional[Span] = None  # the spaCy Span for this sentence


@dataclass
class PreprocessResult:
    """Everything downstream layers need from preprocessing."""
    original_text: str
    normalized_text: str          # lowercase, collapsed whitespace
    sentences: List[SentenceInfo]
    doc: Doc                      # full spaCy Doc (for Matchers)
    num_sentences: int = 0


# ── Public API ─────────────────────────────────────────────────────

def validate_input(text: str) -> str:
    """Validate and lightly clean the input text.

    Raises ValueError for empty or over-length input.
    Returns the cleaned text.
    """
    if not text or not text.strip():
        raise ValueError("Input text must not be empty.")
    text = text.strip()
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"Input text exceeds the maximum length of {MAX_INPUT_LENGTH} characters "
            f"(got {len(text)})."
        )
    return text


def preprocess(text: str) -> PreprocessResult:
    """Run the full preprocessing pipeline on *text*.

    Steps:
      1. Validate and clean input.
      2. Run spaCy pipeline (tokenize, POS, lemma, dependency, sentences).
      3. Build SentenceInfo objects with character-offset mappings.
      4. Create a normalized version for matching (lowercase, collapsed WS).

    Returns:
        PreprocessResult with sentences, tokens and the spaCy Doc.
    """
    text = validate_input(text)
    nlp = get_nlp()
    doc = nlp(text)

    sentences: List[SentenceInfo] = []
    for sent_idx, sent in enumerate(doc.sents):
        tokens = [
            TokenInfo(
                text=tok.text,
                lemma=tok.lemma_.lower(),
                pos=tok.pos_,
                dep=tok.dep_,
                idx=tok.idx,
                end_idx=tok.idx + len(tok.text),
                is_stop=tok.is_stop,
                is_punct=tok.is_punct,
            )
            for tok in sent
        ]
        sentences.append(SentenceInfo(
            text=sent.text,
            start=sent.start_char,
            end=sent.end_char,
            index=sent_idx,
            tokens=tokens,
            doc=sent,
        ))

    # Normalized version: lowercase, collapse whitespace (for matching only)
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    result = PreprocessResult(
        original_text=text,
        normalized_text=normalized,
        sentences=sentences,
        doc=doc,
        num_sentences=len(sentences),
    )
    return result
