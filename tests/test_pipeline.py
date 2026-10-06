import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp_engine.pipeline import init_engine, analyze
from backend.schemas import AnalysisOptions

@pytest.fixture(scope="module", autouse=True)
def setup_engine():
    init_engine()

def test_flags_merged_without_duplicates():
    # Pipeline should deduplicate flags overlapping on exact same bounds
    options = AnalysisOptions(use_semantic=True, use_ml=True, use_tone=True)
    res = analyze("Let's touch base.", "usa", "japan", options)
    # Ensure no duplicates
    assert len(res['flags']) == len({f['start'] for f in res['flags']})

def test_score_rises_with_more_risk():
    options = AnalysisOptions(use_semantic=False, use_ml=False, use_tone=False)
    res1 = analyze("Let's meet.", "usa", "japan", options)
    res2 = analyze("Let's touch base ASAP and hit a home run.", "usa", "japan", options)
    assert res2['risk_score'] > res1['risk_score']

def test_score_lower_for_plain_sentence():
    options = AnalysisOptions(use_semantic=False, use_ml=False, use_tone=False)
    res = analyze("Please send the report by March 12.", "usa", "japan", options)
    assert res['risk_score'] < 25

def test_same_culture_risk_is_lower():
    options = AnalysisOptions(use_semantic=False, use_ml=False, use_tone=False)
    res_cross = analyze("Let's touch base.", "usa", "japan", options)
    res_same = analyze("Let's touch base.", "usa", "usa", options)
    assert res_same['risk_score'] < res_cross['risk_score']

def test_rewrite_removes_flagged_phrases():
    options = AnalysisOptions(use_semantic=False, use_ml=False, use_tone=False)
    res = analyze("Let's touch base.", "usa", "japan", options)
    assert "touch base" not in res['suggested_rewrite'].lower()

def test_rules_only_mode():
    options = AnalysisOptions(use_semantic=False, use_ml=False, use_tone=False)
    res = analyze("Touch base ASAP.", "usa", "japan", options)
    for flag in res['flags']:
        assert flag['detected_by'] == "rule"

def test_acceptance_criterion_text():
    text = "Hi Tanaka-san, Let's touch base ASAP and circle back on the low-hanging fruit. We'll see if we can pull it off by EOD Friday. Meeting on 03/04/2026. Let me know your bandwidth. Thanks!"
    options = AnalysisOptions(use_semantic=False, use_ml=False, use_tone=False)
    res = analyze(text, "usa", "japan", options)
    assert len(res['flags']) >= 6
