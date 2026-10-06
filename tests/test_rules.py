import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp_engine.preprocess import preprocess
from nlp_engine.rule_detector import detect, _initialize_matchers
from backend.schemas import AnalysisOptions
from nlp_engine.knowledge_base import load_phrases, load_cultures

@pytest.fixture(autouse=True)
def setup_engine():
    load_phrases()
    load_cultures()
    _initialize_matchers()

def test_lemma_matching():
    text = "We are touching base tomorrow."
    prep = preprocess(text)
    flags = detect(prep)
    assert any("touch base" in f['text'].lower() or "touching base" in f['text'].lower() for f in flags)

def test_offset_accuracy():
    text = "Let's touch base soon."
    prep = preprocess(text)
    flags = detect(prep)
    flag = next(f for f in flags if "touch base" in f['text'].lower())
    assert text[flag['start']:flag['end']].lower() == "touch base"

def test_ambiguous_date_detection():
    prep = preprocess("The meeting is on 03/04/2026.")
    flags = detect(prep)
    assert any("03/04/2026" in f['text'] for f in flags)

def test_unambiguous_date_no_flag():
    prep = preprocess("The meeting is on 25/04/2026.")
    flags = detect(prep)
    assert not any("25/04/2026" in f['text'] for f in flags)

def test_next_friday_detection():
    prep = preprocess("Let's meet next Friday.")
    flags = detect(prep)
    assert any("next friday" in f['text'].lower() for f in flags)

def test_currency_symbol_ambiguity():
    prep = preprocess("It costs $100.")
    flags = detect(prep)
    assert any("$100" in f['text'] or "$" in f['text'] for f in flags)

def test_no_false_positive_clean_text():
    prep = preprocess("Please send the report by March 12.")
    flags = detect(prep)
    assert len(flags) == 0

def test_eod_cob_detection():
    prep = preprocess("Finish this by EOD.")
    flags = detect(prep)
    assert any("eod" in f['text'].lower() for f in flags)
    
    prep2 = preprocess("Finish this by COB.")
    flags2 = detect(prep2)
    assert any("cob" in f['text'].lower() for f in flags2)

def test_asap_detection():
    prep = preprocess("I need this ASAP.")
    flags = detect(prep)
    assert any("asap" in f['text'].lower() for f in flags)

def test_idiom_detection():
    prep = preprocess("Let's break the ice.")
    flags = detect(prep)
    assert any("break the ice" in f['text'].lower() for f in flags)

def test_corporate_jargon_detection():
    prep = preprocess("Grab the low-hanging fruit.")
    flags = detect(prep)
    assert any("low-hanging fruit" in f['text'].lower() for f in flags)

def test_phrasal_verb_detection():
    prep = preprocess("They will call off the meeting.")
    flags = detect(prep)
    assert any("call off" in f['text'].lower() for f in flags)

def test_sports_metaphor_detection():
    prep = preprocess("We need to hit a home run.")
    flags = detect(prep)
    assert any("hit a home run" in f['text'].lower() or "home run" in f['text'].lower() for f in flags)

def test_multiple_flags_one_sentence():
    prep = preprocess("Touch base ASAP about the low-hanging fruit.")
    flags = detect(prep)
    assert len(flags) >= 3

def test_empty_input_raises_value_error():
    with pytest.raises(ValueError):
        preprocess("")
