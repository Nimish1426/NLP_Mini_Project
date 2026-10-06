import logging
import os
import numpy as np
from typing import List, Dict

from backend.config import SEMANTIC_THRESHOLD, SEMANTIC_MODEL_NAME, MAX_CHUNKS_PER_SENTENCE, SEMANTIC_NGRAM_MIN, SEMANTIC_NGRAM_MAX, PHRASE_EMBEDDINGS_PATH
from nlp_engine.preprocess import PreprocessResult
from nlp_engine.knowledge_base import get_phrases

logger = logging.getLogger(__name__)

_model = None
_phrase_embeddings = None
_phrase_entries = []

def _initialize_semantic():
    global _model, _phrase_embeddings, _phrase_entries
    if _model is not None or _phrase_embeddings is not None:
        return
        
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(SEMANTIC_MODEL_NAME)
    except Exception as e:
        logger.warning(f"Failed to load sentence_transformers: {e}")
        return

    phrases = get_phrases()
    examples = []
    for p in phrases:
        for ex in p.examples:
            examples.append(ex)
            _phrase_entries.append(p)
            
    if PHRASE_EMBEDDINGS_PATH.exists():
        _phrase_embeddings = np.load(PHRASE_EMBEDDINGS_PATH)
    else:
        _phrase_embeddings = _model.encode(examples, show_progress_bar=False)
        os.makedirs(PHRASE_EMBEDDINGS_PATH.parent, exist_ok=True)
        np.save(PHRASE_EMBEDDINGS_PATH, _phrase_embeddings)

def detect(prep: PreprocessResult, existing_flags: List[Dict] = None) -> List[Dict]:
    """Detect semantic L2 flags."""
    _initialize_semantic()
    flags = []
    
    if _model is None or _phrase_embeddings is None:
        logger.warning("Semantic layer disabled.")
        return flags
        
    existing_spans = [(f['start'], f['end']) for f in (existing_flags or [])]
    
    from sentence_transformers.util import cos_sim

    for sent in prep.sentences:
        chunks = []
        chunk_spans = []
        
        # N-grams from spaCy noun/verb phrases
        tokens = [t for t in sent.tokens]
        n_tokens = len(tokens)
        
        candidates = 0
        for n in range(SEMANTIC_NGRAM_MIN, min(SEMANTIC_NGRAM_MAX + 1, n_tokens + 1)):
            for i in range(n_tokens - n + 1):
                if candidates >= MAX_CHUNKS_PER_SENTENCE:
                    break
                chunk_tokens = tokens[i:i+n]
                c_start = chunk_tokens[0].idx
                c_end = chunk_tokens[-1].end_idx
                
                # Check overlap
                overlap = False
                for es, ee in existing_spans:
                    if not (c_end <= es or c_start >= ee):
                        overlap = True
                        break
                if overlap:
                    continue
                    
                chunk_text = sent.text[c_start - sent.start:c_end - sent.start]
                chunks.append(chunk_text)
                chunk_spans.append((c_start, c_end))
                candidates += 1
                
        if not chunks:
            continue
            
        chunk_embs = _model.encode(chunks, show_progress_bar=False)
        sims = cos_sim(chunk_embs, _phrase_embeddings).numpy()
        
        for i, chunk_sims in enumerate(sims):
            max_idx = np.argmax(chunk_sims)
            max_sim = chunk_sims[max_idx]
            
            if max_sim >= SEMANTIC_THRESHOLD:
                matched_entry = _phrase_entries[max_idx]
                c_start, c_end = chunk_spans[i]
                
                flags.append({
                    'id': f'semantic_{c_start}',
                    'text': prep.original_text[c_start:c_end],
                    'start': c_start,
                    'end': c_end,
                    'sentence_index': sent.index,
                    'category': matched_entry.category,
                    'severity': matched_entry.base_severity,
                    'confidence': float(max_sim),
                    'detected_by': 'semantic',
                    'explanation': f'Resembles known risky phrase "{matched_entry.phrase}". {matched_entry.risk_note}',
                    'literal_meaning_risk': matched_entry.meaning,
                    'suggestions': matched_entry.plain_alternatives
                })
                
    return flags
