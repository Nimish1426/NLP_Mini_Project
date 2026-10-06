import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import EVAL_SET_PATH, PROJECT_ROOT
from nlp_engine.pipeline import init_engine, analyze
from backend.schemas import AnalysisOptions

def main():
    print("Initializing NLP Engine...")
    init_engine()
    
    if not EVAL_SET_PATH.exists():
        print(f"Eval set not found at {EVAL_SET_PATH}")
        return
        
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} examples from eval set.")
    
    options = AnalysisOptions(use_semantic=True, use_ml=True, use_tone=True)
    
    tp_overall = 0
    fp_overall = 0
    fn_overall = 0
    
    misses = []
    false_positives = []
    
    for item in data:
        text = item.get("text", "")
        source = item.get("source_culture", "usa")
        target = item.get("target_culture", "japan")
        expected = item.get("expected_flags", [])
        
        try:
            res = analyze(text, source, target, options)
            detected = [f['text'].lower() for f in res['flags']]
            expected_lower = [e['phrase'].lower() for e in expected]
            
            for exp in expected_lower:
                if any(exp in det or det in exp for det in detected):
                    tp_overall += 1
                else:
                    fn_overall += 1
                    misses.append({"text": text, "missed": exp})
                    
            for det in detected:
                if not any(exp in det or det in exp for exp in expected_lower):
                    fp_overall += 1
                    false_positives.append({"text": text, "false_positive": det})
                    
        except Exception as e:
            print(f"Error analyzing text: {text} - {e}")
            
    precision = tp_overall / (tp_overall + fp_overall) if (tp_overall + fp_overall) > 0 else 0
    recall = tp_overall / (tp_overall + fn_overall) if (tp_overall + fn_overall) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    report = []
    report.append("# Evaluation Report\n")
    report.append("## Overall Metrics")
    report.append(f"- **Precision:** {precision:.4f}")
    report.append(f"- **Recall:** {recall:.4f}")
    report.append(f"- **F1 Score:** {f1:.4f}\n")
    
    report.append("## Misses (False Negatives)")
    report.append("| Text | Missed Phrase |")
    report.append("|---|---|")
    for m in misses[:10]:
        report.append(f"| {m['text']} | {m['missed']} |")
        
    report.append("\n## False Positives")
    report.append("| Text | False Positive |")
    report.append("|---|---|")
    for fp in false_positives[:10]:
        report.append(f"| {fp['text']} | {fp['false_positive']} |")
        
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_path = docs_dir / "evaluation_report.md"
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Evaluation complete. Report saved to {out_path}")
    print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")

if __name__ == "__main__":
    main()
