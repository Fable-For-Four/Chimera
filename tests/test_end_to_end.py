"""The whole product in one path: real API, real engine subprocess, real generated data."""

import pytest
from fastapi.testclient import TestClient

from api import auth, db
from api import email as mailer
from api.main import app
from api.seed import seed

PASSWORD = "test-pass-123"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "end-to-end-secret-that-is-32-chars-plus")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "e2e.db")
    monkeypatch.setattr(auth, "BCRYPT_COST", 4)
    monkeypatch.setattr(mailer, "send_verification_email", lambda to, name, link: None)
    with TestClient(app) as c:
        conn = db.connect()
        seed(conn, PASSWORD)
        conn.close()
        yield c


def sign_in(client, email):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


def test_analyst_runs_the_real_engine_and_follows_the_case(client):
    assert client.get("/api/case").status_code == 401

    sign_in(client, "analyst@acme.test")
    intake = client.get("/api/intake").json()
    assert intake["summary"] == {"events": 5124, "sources": 4, "late": 212, "alerts_fired": 0}

    r = client.post("/api/case/run")
    assert r.status_code == 200, r.text
    case = r.json()
    assert case["verdict"]["found"] and case["verdict"]["label"] == "Likely attack"
    assert [s["stage"] for s in case["chain"]] == [
        "Initial access",
        "Privilege escalation",
        "Lateral movement",
        "Collection",
        "Exfiltration",
    ]
    assert sum(len(s["exhibits"]) for s in case["chain"]) == 11
    assert case["truth_score"]["found"] == 11 and case["truth_score"]["false_links"] == []
    assert len(case["report"]) == 5 and all(c["cites"] for c in case["report"])
    assert client.get("/api/case").json() == case

    for level in range(0, 45, 5):
        stressed = client.get(f"/api/case/stress/{level}")
        assert stressed.status_code == 200 and stressed.json()["level"] == level
    assert (
        client.get("/api/case/stress/40").json()["verdict"]["confidence"]
        < case["verdict"]["confidence"]
    )

    action = case["actions"][0]["id"]
    assert client.post(f"/api/actions/{action}/approve").status_code == 201
    assert client.post(f"/api/actions/{action}/approve").status_code == 409
    assert [a["action_id"] for a in client.get("/api/approvals").json()] == [action]


def test_viewer_reads_the_real_case_but_cannot_run_or_approve(client):
    sign_in(client, "analyst@acme.test")
    case = client.post("/api/case/run").json()

    sign_in(client, "viewer@acme.test")
    assert client.get("/api/case").json()["verdict"] == case["verdict"]
    assert client.post("/api/case/run").status_code == 403
    assert client.post(f"/api/actions/{case['actions'][0]['id']}/approve").status_code == 403
