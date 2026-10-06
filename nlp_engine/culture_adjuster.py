import math
from typing import List, Dict
from backend.config import SEVERITY_LOW_MAX, SEVERITY_MED_MAX
from nlp_engine.knowledge_base import get_culture

def adjust_flags(flags: List[Dict], source_culture_id: str, target_culture_id: str) -> List[Dict]:
    source_c = get_culture(source_culture_id)
    target_c = get_culture(target_culture_id)
    
    if not source_c or not target_c:
        return flags
        
    dims = ['context_level', 'directness', 'power_distance', 'time_orientation', 'formality']
    dist_sq = sum((source_c.dimensions[d] - target_c.dimensions[d])**2 for d in dims)
    culture_distance = math.sqrt(dist_sq) / math.sqrt(len(dims))
    
    adjusted_flags = []
    for f in flags:
        base_risk = f['severity']
        cat = f['category']
        
        cat_mod = target_c.category_modifiers.get(cat, 1.0)
        
        if source_culture_id == target_culture_id:
            adjusted_risk = base_risk * 0.5
        else:
            adjusted_risk = base_risk * (1 + 0.5 * culture_distance) * cat_mod
            
        if adjusted_risk <= SEVERITY_LOW_MAX:
            new_sev = 1
        elif adjusted_risk <= SEVERITY_MED_MAX:
            new_sev = 2
        else:
            new_sev = 3
            
        f_adj = dict(f)
        f_adj['severity'] = new_sev
        
        # Substitute target culture name in explanation
        f_adj['explanation'] = f_adj['explanation'].replace('{target_culture}', target_c.display_name)
        
        adjusted_flags.append(f_adj)
        
    return adjusted_flags
