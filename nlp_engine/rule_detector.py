import re
import spacy
from spacy.matcher import PhraseMatcher, Matcher
from typing import List, Dict, Any

from backend.config import RULE_CONFIDENCE
from nlp_engine.preprocess import PreprocessResult, get_nlp
from nlp_engine.knowledge_base import get_phrases, get_phrase_by_id

_phrase_matcher = None
_matcher = None

def _initialize_matchers():
    global _phrase_matcher, _matcher
    if _phrase_matcher is not None:
        return
        
    nlp = get_nlp()
    _phrase_matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
    _matcher = Matcher(nlp.vocab)
    
    phrases = get_phrases()
    for entry in phrases:
        if entry.pattern_type == "lemma_phrase":
            doc = nlp(entry.phrase)
            _phrase_matcher.add(entry.id, [doc])
        elif entry.pattern_type == "token_pattern":
            # Just a placeholder since the exact patterns aren't specified in entry
            # Usually token_pattern in phrases.json would be handled here, assuming phrase is stringified json or similar
            pass

def _detect_ambiguous_dates(text: str, offset: int, sent_idx: int) -> List[Dict]:
    flags = []
    # match mm/dd/yyyy or dd/mm/yyyy
    for match in re.finditer(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b', text):
        n1, n2, yr = map(int, match.groups())
        if n1 <= 12 and n2 <= 12 and n1 != n2:
            flags.append({
                'id': f'ambig_date_{match.start()}',
                'text': match.group(0),
                'start': offset + match.start(),
                'end': offset + match.end(),
                'sentence_index': sent_idx,
                'category': 'date_format',
                'severity': 2,
                'confidence': RULE_CONFIDENCE,
                'detected_by': 'rule',
                'explanation': 'Ambiguous date format (could be mm/dd or dd/mm).',
                'literal_meaning_risk': 'Reader might confuse day and month.',
                'suggestions': ['Spell out the month (e.g., Mar 4, 2026)']
            })
    return flags

def _detect_relative_time(text: str, offset: int, sent_idx: int) -> List[Dict]:
    flags = []
    pattern = r'\b(next friday|this friday|end of day|eod|cob|by tomorrow|in a couple of days|asap|soon|shortly|in the evening)\b'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        flags.append({
            'id': f'rel_time_{match.start()}',
            'text': match.group(0),
            'start': offset + match.start(),
            'end': offset + match.end(),
            'sentence_index': sent_idx,
            'category': 'vague_time',
            'severity': 2,
            'confidence': RULE_CONFIDENCE,
            'detected_by': 'rule',
            'explanation': 'Relative time expressions can be vague and depend on timezone/context.',
            'literal_meaning_risk': 'Reader may not know the exact deadline.',
            'suggestions': ['Provide a specific date and time with timezone']
        })
    return flags

def _detect_units_numbers(text: str, offset: int, sent_idx: int) -> List[Dict]:
    flags = []
    # Currency symbols without code
    for match in re.finditer(r'([$£¥])\s*\d+', text):
        sym = match.group(1)
        flags.append({
            'id': f'currency_{match.start()}',
            'text': match.group(0),
            'start': offset + match.start(),
            'end': offset + match.end(),
            'sentence_index': sent_idx,
            'category': 'units_numbers',
            'severity': 2,
            'confidence': RULE_CONFIDENCE,
            'detected_by': 'rule',
            'explanation': f'Currency symbol "{sym}" is ambiguous.',
            'literal_meaning_risk': 'Reader might assume their local currency.',
            'suggestions': [f'Use ISO currency code (e.g., USD {match.group(0)[1:]})']
        })
    # Number formats 1,000.50
    for match in re.finditer(r'\b\d{1,3}(,\d{3})+\.\d+\b', text):
        flags.append({
            'id': f'num_fmt_{match.start()}',
            'text': match.group(0),
            'start': offset + match.start(),
            'end': offset + match.end(),
            'sentence_index': sent_idx,
            'category': 'units_numbers',
            'severity': 2,
            'confidence': RULE_CONFIDENCE,
            'detected_by': 'rule',
            'explanation': 'Number format with commas for thousands and dots for decimals can be confusing.',
            'literal_meaning_risk': 'Some cultures swap commas and decimals.',
            'suggestions': ['Ensure clarity or provide context']
        })
    return flags

def _detect_fiscal_seasons(text: str, offset: int, sent_idx: int) -> List[Dict]:
    flags = []
    pattern = r'\b(Q[1-4]|summer|winter|spring|autumn|fall)\b'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        flags.append({
            'id': f'season_{match.start()}',
            'text': match.group(0),
            'start': offset + match.start(),
            'end': offset + match.end(),
            'sentence_index': sent_idx,
            'category': 'vague_time',
            'severity': 1,
            'confidence': RULE_CONFIDENCE,
            'detected_by': 'rule',
            'explanation': 'Seasons/Quarters can be hemisphere or company dependent.',
            'literal_meaning_risk': 'May interpret a different timeframe.',
            'suggestions': ['Use specific months (e.g., July-Sept)']
        })
    return flags

def detect(prep: PreprocessResult) -> List[Dict]:
    """Detect rule-based L1 flags."""
    _initialize_matchers()
    flags = []
    
    # Match phrases
    matches = _phrase_matcher(prep.doc)
    for match_id, start, end in matches:
        phrase_id = prep.doc.vocab.strings[match_id]
        entry = get_phrase_by_id(phrase_id)
        if entry:
            span = prep.doc[start:end]
            # find sentence index
            sent_idx = 0
            for s in prep.sentences:
                if s.start <= span[0].idx and s.end >= span[-1].idx + len(span[-1]):
                    sent_idx = s.index
                    break
            
            flags.append({
                'id': f'rule_{phrase_id}_{span[0].idx}',
                'text': span.text,
                'start': span[0].idx,
                'end': span[-1].idx + len(span[-1].text),
                'sentence_index': sent_idx,
                'category': entry.category,
                'severity': entry.base_severity,
                'confidence': RULE_CONFIDENCE,
                'detected_by': 'rule',
                'explanation': entry.risk_note,
                'literal_meaning_risk': entry.meaning,
                'suggestions': entry.plain_alternatives
            })
    
    # regex patterns
    for sent in prep.sentences:
        flags.extend(_detect_ambiguous_dates(sent.text, sent.start, sent.index))
        flags.extend(_detect_relative_time(sent.text, sent.start, sent.index))
        flags.extend(_detect_units_numbers(sent.text, sent.start, sent.index))
        flags.extend(_detect_fiscal_seasons(sent.text, sent.start, sent.index))
        
    return flags
