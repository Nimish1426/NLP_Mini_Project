import math
from typing import List, Dict, Tuple
from backend.config import SCORER_K, SCORE_LABELS

def score_text(flags: List[Dict], num_sentences: int) -> Tuple[float, str, List[Dict]]:
    if not flags or num_sentences == 0:
        return 0.0, SCORE_LABELS[0][1], []
        
    term_sum = sum(f['severity'] * f['confidence'] for f in flags)
    score = min(100.0, 100.0 * (1.0 - math.exp(-SCORER_K * (term_sum / math.sqrt(num_sentences)))))
    
    label = SCORE_LABELS[-1][1]
    for limit, lbl in SCORE_LABELS:
        if score <= limit:
            label = lbl
            break
            
    cat_counts = {}
    cat_risk = {}
    for f in flags:
        cat = f['category']
        risk = f['severity'] * f['confidence']
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        cat_risk[cat] = cat_risk.get(cat, 0.0) + risk
        
    total_risk = sum(cat_risk.values())
    breakdown = []
    if total_risk > 0:
        for cat, count in cat_counts.items():
            breakdown.append({
                'category': cat,
                'count': count,
                'share': cat_risk[cat] / total_risk
            })
            
    return score, label, breakdown
