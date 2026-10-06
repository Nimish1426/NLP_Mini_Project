import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_get_cultures():
    response = client.get("/api/cultures")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8

def test_analyze_valid_input():
    response = client.post("/api/analyze", json={
        "text": "Let's touch base ASAP.",
        "source_culture": "usa",
        "target_culture": "japan",
        "options": {
            "use_semantic": False,
            "use_ml": False,
            "use_tone": False
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert "flags" in data

def test_analyze_invalid_culture():
    response = client.post("/api/analyze", json={
        "text": "Hello",
        "source_culture": "invalid",
        "target_culture": "japan"
    })
    assert response.status_code == 422

def test_analyze_empty_text():
    response = client.post("/api/analyze", json={
        "text": "",
        "source_culture": "usa",
        "target_culture": "japan"
    })
    assert response.status_code == 422

def test_analyze_overlong_text():
    response = client.post("/api/analyze", json={
        "text": "A" * 5001,
        "source_culture": "usa",
        "target_culture": "japan"
    })
    # Validation error for max_length in schema
    assert response.status_code == 422

def test_get_examples():
    response = client.get("/api/examples")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    assert data[0]["title"] == "Business Email"
