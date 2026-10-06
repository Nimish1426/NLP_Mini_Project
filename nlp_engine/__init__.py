"""
nlp_engine/__init__.py – Package marker for the CultureLens NLP engine.

The engine is a 3-layer hybrid detector:
  Layer 1 – Rule-based (spaCy PhraseMatcher + regex patterns)
  Layer 2 – Semantic (sentence-transformer embedding similarity)
  Layer 3 – ML classifier (TF-IDF + Logistic Regression)

Plus tone analysis, culture adjustment, scoring and suggestion.
"""
