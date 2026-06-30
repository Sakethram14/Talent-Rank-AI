import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"

def test_dashboard_analytics(client):
    response = client.get("/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "total_candidates" in data["data"]
    
def test_rank_candidates(client):
    payload = {
        "job_description": "Looking for a Python AI Engineer with PyTorch experience.",
        "top_k": 5,
        "filters": {
            "exclude_honeypots": True
        }
    }
    response = client.post("/candidates/rank", json=payload)
    if response.status_code != 200:
        print(response.text)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["candidates"]) <= 5
    # Ensure they are sorted
    scores = [c["overall_score"] for c in data["data"]["candidates"]]
    assert scores == sorted(scores, reverse=True)
    
def test_get_evidence(client):
    # First get a candidate ID from ranking
    payload = {
        "job_description": "Data Scientist",
        "top_k": 1
    }
    rank_res = client.post("/candidates/rank", json=payload)
    cid = rank_res.json()["data"]["candidates"][0]["id"]
    
    # Then ask for their evidence
    ev_res = client.get(f"/candidates/{cid}/evidence")
    assert ev_res.status_code == 200
    data = ev_res.json()
    assert data["success"] is True
    assert data["data"]["candidate_id"] == cid
    assert "positive_signals" in data["data"]
    assert "behavioral_summary" in data["data"]

def test_export_csv(client):
    # First, run a ranking to populate the active session
    payload = {
        "job_description": "Machine Learning Engineer",
        "top_k": 50
    }
    client.post("/candidates/rank", json=payload)
    
    # Now, export the session
    response = client.get("/export/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    content = response.text
    assert "candidate_id,rank" in content

def test_sessions_persistence(client):
    # 1. Run a ranking to establish a session
    payload = {
        "job_description": "Kubernetes and Go Backend Developer",
        "top_k": 3
    }
    rank_res = client.post("/candidates/rank", json=payload)
    assert rank_res.status_code == 200
    session_data = rank_res.json()["data"]
    session_id = session_data["session_id"]
    
    # 2. Retrieve active session
    active_res = client.get("/sessions/active")
    assert active_res.status_code == 200
    assert active_res.json()["data"]["session_id"] == session_id
    
    # 3. Retrieve session by ID
    by_id_res = client.get(f"/sessions/{session_id}")
    assert by_id_res.status_code == 200
    assert by_id_res.json()["data"]["session_id"] == session_id

def test_get_candidate_profile(client):
    # Retrieve a candidate profile from the active session
    active_res = client.get("/sessions/active")
    assert active_res.status_code == 200
    candidates = active_res.json()["data"]["candidates"]
    assert len(candidates) > 0
    cid = candidates[0]["id"]
    
    # Fetch Candidate details
    c_res = client.get(f"/candidates/{cid}")
    assert c_res.status_code == 200
    data = c_res.json()["data"]
    assert data["id"] == cid
    assert "name" in data
    assert "scores" in data
    assert "career" in data
    assert "education" in data
    assert "evidence" in data

