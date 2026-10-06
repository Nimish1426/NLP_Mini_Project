"""
ml_classifier.py – Layer 3: TF-IDF + Logistic Regression sentence classifier.

This layer provides sentence-level classification for sentences that
Layer 1 (rules) and Layer 2 (semantic) did not already flag.

Model: TF-IDF (word 1-2 grams + char 3-5 grams) → One-vs-Rest
Logistic Regression trained on data/training_data.csv.

Labels: idiom_slang, vague_indirect, blunt_direct, sarcasm_humor,
        time_date_ambiguity, safe.

The trained model is saved as a single sklearn Pipeline to
models/classifier.joblib. If the file is missing, this module
attempts to auto-train on first use (< 10 seconds on CPU).
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from backend.config import (
    CLASSIFIER_PATH,
    ML_CONFIDENCE_THRESHOLD,
    ML_RANDOM_SEED,
    TRAINING_DATA_PATH,
)
from nlp_engine.preprocess import PreprocessResult

logger = logging.getLogger(__name__)

# ── Module-level state ─────────────────────────────────────────────
_classifier = None  # sklearn Pipeline (vectorizer + classifier combined)

# Labels the model was trained on (order matters for predict_proba)
LABELS = [
    "blunt_direct",
    "idiom_slang",
    "safe",
    "sarcasm_humor",
    "time_date_ambiguity",
    "vague_indirect",
]


def _auto_train() -> bool:
    """Train the classifier from training_data.csv and save it.

    Returns True on success, False otherwise.
    """
    global _classifier
    try:
        import pandas as pd
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.multiclass import OneVsRestClassifier
        from sklearn.pipeline import FeatureUnion, Pipeline
        import joblib

        if not TRAINING_DATA_PATH.exists():
            logger.warning("Training data not found at %s", TRAINING_DATA_PATH)
            return False

        logger.info("Auto-training ML classifier from %s …", TRAINING_DATA_PATH)
        df = pd.read_csv(TRAINING_DATA_PATH)

        pipeline = Pipeline([
            ("features", FeatureUnion([
                ("word_tfidf", TfidfVectorizer(
                    analyzer="word", ngram_range=(1, 2))),
                ("char_tfidf", TfidfVectorizer(
                    analyzer="char", ngram_range=(3, 5))),
            ])),
            ("clf", OneVsRestClassifier(LogisticRegression(
                random_state=ML_RANDOM_SEED,
                max_iter=1000,
                class_weight="balanced",
            ))),
        ])

        pipeline.fit(df["text"], df["label"])

        os.makedirs(CLASSIFIER_PATH.parent, exist_ok=True)
        joblib.dump(pipeline, CLASSIFIER_PATH)

        _classifier = pipeline
        logger.info("ML classifier trained and saved to %s", CLASSIFIER_PATH)
        return True

    except Exception as e:
        logger.warning("Auto-training failed: %s", e)
        return False


def _initialize_ml() -> None:
    """Load the saved classifier, or auto-train if missing."""
    global _classifier
    if _classifier is not None:
        return

    try:
        import joblib

        if CLASSIFIER_PATH.exists():
            _classifier = joblib.load(CLASSIFIER_PATH)
            logger.info("ML classifier loaded from %s", CLASSIFIER_PATH)
        else:
            logger.info("Classifier file not found, attempting auto-train …")
            _auto_train()

    except Exception as e:
        logger.warning("Failed to load ML classifier: %s", e)


def classify(
    prep: PreprocessResult,
    existing_flags: List[Dict],
) -> List[Dict]:
    """Classify sentences that have no existing L1/L2 flags.

    For each unflagged sentence, if the model predicts a risky label
    with probability ≥ ML_CONFIDENCE_THRESHOLD, emit a sentence-level
    flag with category='sentence_level'.

    Args:
        prep: Preprocessed text from preprocess.py.
        existing_flags: Flags already detected by L1 and L2.

    Returns:
        List of sentence-level flag dicts.
    """
    _initialize_ml()
    flags: List[Dict] = []

    if _classifier is None:
        logger.warning("ML layer disabled (no classifier loaded).")
        return flags

    # Find sentences already covered by L1/L2
    flagged_sentences = {f["sentence_index"] for f in existing_flags}

    for sent in prep.sentences:
        if sent.index in flagged_sentences:
            continue

        try:
            # predict_proba returns array of shape (n_samples, n_classes)
            proba = _classifier.predict_proba([sent.text])

            # Get the classes from the classifier
            classes = list(_classifier.classes_)

            for i, label in enumerate(classes):
                if label == "safe":
                    continue

                prob = float(proba[0][i])
                if prob >= ML_CONFIDENCE_THRESHOLD:
                    # Map ML label to a human-readable explanation
                    label_desc = {
                        "idiom_slang": "idiomatic or slang expressions",
                        "vague_indirect": "vague or indirect language",
                        "blunt_direct": "overly blunt or direct phrasing",
                        "sarcasm_humor": "sarcasm or humor",
                        "time_date_ambiguity": "ambiguous time/date references",
                    }.get(label, label)

                    # Category-specific suggestions
                    suggestion = {
                        "idiom_slang": "Replace informal expressions with plain language",
                        "vague_indirect": "Be more specific and direct in your request",
                        "blunt_direct": "Add polite softeners such as 'Could you please…'",
                        "sarcasm_humor": "Replace sarcastic tone with straightforward language",
                        "time_date_ambiguity": "State the exact date and timezone",
                    }.get(label, "Consider rephrasing for clarity")

                    flags.append({
                        "id": f"ml_{sent.index}_{sent.start}",
                        "text": sent.text.strip(),
                        "start": sent.start,
                        "end": sent.end,
                        "sentence_index": sent.index,
                        "category": "sentence_level",
                        "severity": 2,
                        "confidence": prob,
                        "detected_by": "ml",
                        "explanation": (
                            f"ML classifier detected {label_desc} "
                            f"in this sentence (confidence: {prob:.0%})."
                        ),
                        "literal_meaning_risk": "",
                        "suggestions": [suggestion],
                    })
                    break  # one flag per sentence

        except Exception as e:
            logger.debug("ML classify error on sentence %d: %s", sent.index, e)

    return flags
