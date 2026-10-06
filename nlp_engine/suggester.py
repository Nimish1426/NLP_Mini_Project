from typing import List, Dict

def suggest_rewrite(text: str, flags: List[Dict]) -> str:
    sorted_flags = sorted(flags, key=lambda x: x['start'], reverse=True)
    
    rewrite = text
    for f in sorted_flags:
        # Only substitute literal replacements (rule/semantic), not meta-suggestions (ml/tone)
        if f['suggestions'] and f.get('detected_by') in ('rule', 'semantic'):
            best_sugg = f['suggestions'][0]
            start = f['start']
            end = f['end']
            rewrite = rewrite[:start] + best_sugg + rewrite[end:]
            
    return rewrite
