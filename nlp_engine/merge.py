from typing import List, Dict

def merge_flags(flags: List[Dict]) -> List[Dict]:
    precedence = {'rule': 4, 'semantic': 3, 'ml': 2, 'tone': 1}
    
    # Sort by start offset first
    flags.sort(key=lambda x: x['start'])
    
    merged = []
    for f in flags:
        overlap = False
        for i, m in enumerate(merged):
            if not (f['end'] <= m['start'] or f['start'] >= m['end']):
                overlap = True
                
                # Resolve overlap
                f_prec = precedence.get(f['detected_by'], 0)
                m_prec = precedence.get(m['detected_by'], 0)
                
                if f_prec > m_prec:
                    merged[i] = f
                elif f_prec == m_prec:
                    if f['confidence'] > m['confidence']:
                        merged[i] = f
                break
                
        if not overlap:
            merged.append(f)
            
    return sorted(merged, key=lambda x: x['start'])
