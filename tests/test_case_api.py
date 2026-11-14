import json
import logging
import subprocess
import threading
import time

import pytest
from fastapi.testclient import TestClient

from api import auth, case_files, db
from api import email as mailer
from api import main as api_main
from api.main import app
from api.seed import seed

SECRET = "test-secret-that-is-at-least-32-characters"
PASSWORD = "test-pass-123"

CASE = {
    "level": 0,
    "deleted": 0,
    "verdict": {"label": "Likely attack", "confidence": 87, "found": True},
    "actions": [
        {"id": "reset-priya.s", "kind": "Contain", "text": "Reset the priya.s password"},
        {"id": "block-198.51.100.23", "kind": "Contain", "text": "Block 198.51.100.23"},
    ],
}
INTAKE = {"summary": {"events": 5124, "sources": 4, "late": 212, "alerts_fired": 0}}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def fake_engine(night="attack"):
    out = case_files.OUT_DIR
    write(out / "intake.json", INTAKE)
    for level in case_files.STRESS_LEVELS:
        write(out / "stress" / f"{level:02d}.json", {**CASE, "level": level})
    write(out / "case.json", CASE)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(auth, "BCRYPT_COST", 4)
    monkeypatch.setattr(case_files, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(case_files, "SAMPLES_DIR", tmp_path / "samples")
    monkeypatch.setattr(case_files, "run_engine", fake_engine)
    monkeypatch.setattr(mailer, "send_verification_email", lambda to, name, link: None)
    with TestClient(app) as c:
        conn = db.connect()
        seed(conn, PASSWORD)
        conn.close()
        yield c


def as_user(client, role):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": f"{role}@acme.test", "password": PASSWORD})
    assert r.status_code == 200
    return client


def user_id(client, email):
    users = as_user(client, "admin").get("/api/users").json()
    return next(u["id"] for u in users if u["email"] == email)


def test_case_is_404_before_any_run_and_200_after_run(client):
    as_user(client, "analyst")
    before = client.get("/api/case")
    assert before.status_code == 404
    assert before.json() == {"detail": "Run the investigation first"}
    run = client.post("/api/case/run")
    assert run.status_code == 200
    assert run.json() == CASE
    assert client.get("/api/case").json() == CASE


def test_viewer_cannot_run(client):
    r = as_user(client, "viewer").post("/api/case/run")
    assert r.status_code == 403
    assert r.json() == {"detail": "Your role cannot do this"}


def test_viewer_reads_case_but_cannot_approve(client):
    as_user(client, "analyst").post("/api/case/run")
    as_user(client, "viewer")
    assert client.get("/api/case").status_code == 200
    r = client.post("/api/actions/reset-priya.s/approve")
    assert r.status_code == 403


def test_analyst_approves_once_and_second_approval_is_409(client):
    as_user(client, "analyst").post("/api/case/run")
    first = client.post("/api/actions/reset-priya.s/approve")
    assert first.status_code == 201
    body = first.json()
    assert body["action_id"] == "reset-priya.s"
    assert body["approved_by"] == "Analyst"
    assert body["approved_at"]
    second = client.post("/api/actions/reset-priya.s/approve")
    assert second.status_code == 409


def test_approving_an_action_not_in_the_case_is_404(client):
    as_user(client, "analyst")
    assert client.post("/api/actions/reset-priya.s/approve").status_code == 404
    client.post("/api/case/run")
    assert client.post("/api/actions/made-up/approve").status_code == 404


def test_approvals_list_shows_who_and_when(client):
    as_user(client, "analyst").post("/api/case/run")
    approved = client.post("/api/actions/block-198.51.100.23/approve").json()
    listed = as_user(client, "viewer").get("/api/approvals")
    assert listed.status_code == 200
    assert listed.json() == [approved]


def test_run_clears_approvals_from_the_previous_case(client):
    as_user(client, "analyst").post("/api/case/run")
    client.post("/api/actions/reset-priya.s/approve")
    client.post("/api/case/run")
    assert client.get("/api/approvals").json() == []
    assert client.post("/api/actions/reset-priya.s/approve").status_code == 201


def test_failed_run_is_500_logs_reason_and_keeps_approvals(client, monkeypatch, caplog):
    as_user(client, "analyst").post("/api/case/run")
    client.post("/api/actions/reset-priya.s/approve")

    def broken(night="attack"):
        raise RuntimeError("Link stage crashed")

    monkeypatch.setattr(case_files, "run_engine", broken)
    with caplog.at_level(logging.ERROR, logger="chimera.api"):
        r = client.post("/api/case/run")
    assert r.status_code == 500
    assert r.json() == {"detail": "The investigation failed"}
    assert "Link stage crashed" in caplog.text
    assert "Link stage crashed" not in r.text
    assert len(client.get("/api/approvals").json()) == 1


def test_analyst_cannot_list_users_and_admin_can(client):
    assert as_user(client, "analyst").get("/api/users").status_code == 403
    r = as_user(client, "admin").get("/api/users")
    assert r.status_code == 200
    assert {u["role"] for u in r.json()} == {"admin", "analyst", "viewer"}
    assert set(r.json()[0]) == {"id", "email", "name", "role", "verified"}
    assert "password_hash" not in r.text


def test_role_change_applies_to_an_existing_session(client):
    as_user(client, "analyst").post("/api/case/run")
    analyst_cookie = client.cookies.get("session")
    analyst_id = user_id(client, "analyst@acme.test")
    r = client.patch(f"/api/users/{analyst_id}/role", json={"role": "viewer"})
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"
    client.cookies.clear()
    client.cookies.set("session", analyst_cookie)
    assert client.post("/api/actions/reset-priya.s/approve").status_code == 403


def test_role_change_errors(client):
    admin_id = user_id(client, "admin@acme.test")
    viewer_id = user_id(client, "viewer@acme.test")
    assert client.patch(f"/api/users/{viewer_id}/role", json={"role": "root"}).status_code == 422
    own = client.patch(f"/api/users/{admin_id}/role", json={"role": "viewer"})
    assert own.status_code == 409
    assert client.patch("/api/users/9999/role", json={"role": "viewer"}).status_code == 404
    analyst = as_user(client, "analyst")
    assert analyst.patch(f"/api/users/{viewer_id}/role", json={"role": "admin"}).status_code == 403


def test_stress_levels(client):
    as_user(client, "viewer")
    assert client.get("/api/case/stress/20").status_code == 404
    as_user(client, "analyst").post("/api/case/run")
    r = client.get("/api/case/stress/20")
    assert r.status_code == 200
    assert r.json()["level"] == 20
    for bad in ["7", "45", "-5", "abc", "020"]:
        assert client.get(f"/api/case/stress/{bad}").status_code == 404


def test_stress_says_run_first_before_any_case(client):
    r = as_user(client, "viewer").get("/api/case/stress/0")
    assert r.status_code == 404
    assert r.json() == {"detail": "Run the investigation first"}


def test_a_missing_stress_level_says_not_ready_when_the_case_exists(client):
    as_user(client, "analyst").post("/api/case/run")
    (case_files.OUT_DIR / "stress" / "20.json").unlink()
    r = client.get("/api/case/stress/20")
    assert r.status_code == 404
    assert r.json() == {"detail": "This stress level is not ready yet"}
    assert client.get("/api/case/stress/0").status_code == 200


def test_every_level_but_zero_is_not_ready_when_only_level_zero_exists(client):
    as_user(client, "analyst").post("/api/case/run")
    for level in case_files.STRESS_LEVELS[1:]:
        (case_files.OUT_DIR / "stress" / f"{level:02d}.json").unlink()
    assert client.get("/api/case/stress/0").status_code == 200
    for level in case_files.STRESS_LEVELS[1:]:
        r = client.get(f"/api/case/stress/{level}")
        assert r.json() == {"detail": "This stress level is not ready yet"}


def test_intake_uses_engine_output_then_falls_back_to_the_sample(client):
    as_user(client, "viewer")
    assert client.get("/api/intake").status_code == 404
    sample = {"summary": {"events": 1, "sources": 1, "late": 0, "alerts_fired": 0}}
    write(case_files.SAMPLES_DIR / "intake.sample.json", sample)
    assert client.get("/api/intake").json() == sample
    write(case_files.OUT_DIR / "intake.json", INTAKE)
    assert client.get("/api/intake").json() == INTAKE


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/intake"),
        ("get", "/api/case"),
        ("get", "/api/case/stress/0"),
        ("post", "/api/case/run"),
        ("post", "/api/actions/x/approve"),
        ("get", "/api/approvals"),
        ("get", "/api/users"),
        ("patch", "/api/users/1/role"),
    ],
)
def test_every_case_route_needs_sign_in(client, method, path):
    client.cookies.clear()
    assert getattr(client, method)(path).status_code == 401


def test_sample_files_stand_in_until_the_engine_is_merged(monkeypatch, tmp_path):
    monkeypatch.setattr(case_files, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(case_files, "SAMPLES_DIR", tmp_path / "samples")
    monkeypatch.setattr(case_files, "engine_available", lambda: False)
    with pytest.raises(RuntimeError):
        case_files.run_engine()
    write(tmp_path / "samples" / "case.sample.json", CASE)
    write(tmp_path / "samples" / "intake.sample.json", INTAKE)
    assert case_files.run_investigation(lambda: None) == CASE
    assert case_files.stress(35)["level"] == 35
    assert case_files.read(tmp_path / "out" / "intake.json") == INTAKE
    assert not list((tmp_path / "out").rglob("*.tmp"))


def test_runs_never_overlap_and_reads_wait_for_the_run(monkeypatch, tmp_path):
    monkeypatch.setattr(case_files, "OUT_DIR", tmp_path / "out")
    active = []
    overlaps = []

    def slow_engine(night="attack"):
        active.append(1)
        if len(active) > 1:
            overlaps.append(True)
        time.sleep(0.2)
        fake_engine()
        active.pop()

    monkeypatch.setattr(case_files, "run_engine", slow_engine)
    runs = [
        threading.Thread(target=case_files.run_investigation, args=(lambda: None,))
        for _ in range(3)
    ]
    for t in runs:
        t.start()
    time.sleep(0.05)
    assert case_files.case() is not None
    for t in runs:
        t.join()
    assert overlaps == []


def test_run_that_writes_no_case_is_500_and_keeps_approvals(client, monkeypatch):
    as_user(client, "analyst").post("/api/case/run")
    client.post("/api/actions/reset-priya.s/approve")
    monkeypatch.setattr(
        case_files, "run_engine", lambda: (case_files.OUT_DIR / "case.json").unlink()
    )
    r = client.post("/api/case/run")
    assert r.status_code == 500
    assert r.json() == {"detail": "The investigation failed"}
    assert len(client.get("/api/approvals").json()) == 1


def test_failed_run_releases_the_lock_so_the_next_run_works(client, monkeypatch):
    as_user(client, "analyst")

    def broken():
        raise RuntimeError("boom")

    monkeypatch.setattr(case_files, "run_engine", broken)
    assert client.post("/api/case/run").status_code == 500
    monkeypatch.setattr(case_files, "run_engine", fake_engine)
    assert client.post("/api/case/run").status_code == 200


def test_sample_run_writes_all_nine_stress_files_with_their_level(monkeypatch, tmp_path):
    monkeypatch.setattr(case_files, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(case_files, "SAMPLES_DIR", tmp_path / "samples")
    monkeypatch.setattr(case_files, "engine_available", lambda: False)
    write(tmp_path / "samples" / "case.sample.json", CASE)
    write(tmp_path / "samples" / "intake.sample.json", INTAKE)
    case_files.run_investigation(lambda: None)
    levels = [0, 5, 10, 15, 20, 25, 30, 35, 40]
    for level in levels:
        assert case_files.stress(level)["level"] == level


def test_unverified_user_gets_confirm_email_403_on_case_routes(client):
    as_user(client, "analyst").post("/api/case/run")
    conn = db.connect()
    conn.execute(
        "UPDATE users SET email_verified_at = NULL WHERE email = ?", ("analyst@acme.test",)
    )
    conn.commit()
    conn.close()
    for method, path in [
        ("get", "/api/intake"),
        ("get", "/api/case"),
        ("get", "/api/case/stress/0"),
        ("post", "/api/case/run"),
        ("post", "/api/actions/reset-priya.s/approve"),
        ("get", "/api/approvals"),
    ]:
        r = getattr(client, method)(path)
        assert r.status_code == 403
        assert r.json() == {"detail": "Confirm your email first"}


def test_viewer_cannot_manage_users(client):
    as_user(client, "viewer")
    assert client.get("/api/users").status_code == 403
    assert client.patch("/api/users/1/role", json={"role": "admin"}).status_code == 403


def test_real_engine_failure_and_timeout_raise_with_the_reason(monkeypatch):
    monkeypatch.setattr(case_files, "engine_available", lambda: True)

    def failing(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="Traceback\nKeyError: ts")

    monkeypatch.setattr(case_files.subprocess, "run", failing)
    with pytest.raises(RuntimeError, match="KeyError: ts"):
        case_files.run_engine()

    def hanging(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="engine.run", timeout=kwargs["timeout"])

    monkeypatch.setattr(case_files.subprocess, "run", hanging)
    with pytest.raises(subprocess.TimeoutExpired):
        case_files.run_engine()


def test_real_engine_runs_in_repo_root_without_secrets_or_stdin(monkeypatch):
    monkeypatch.setattr(case_files, "engine_available", lambda: True)
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("RESEND_API_KEY", "re_secret")
    calls = []

    def ok(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(case_files.subprocess, "run", ok)
    case_files.run_engine()
    cmd, kwargs = calls[0]
    assert cmd[1:] == ["-m", "engine.run", str(case_files.ROOT / "data"), str(case_files.OUT_DIR)]
    assert kwargs["cwd"] == case_files.ROOT
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert "JWT_SECRET" not in kwargs["env"]
    assert "RESEND_API_KEY" not in kwargs["env"]
    assert "PATH" in kwargs["env"]


def test_engine_check_is_false_when_the_engine_package_is_missing(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(case_files.importlib.util, "find_spec", missing)
    assert case_files.engine_available() is False


def test_corrupt_case_file_is_a_plain_500_and_logged(client, caplog):
    as_user(client, "analyst").post("/api/case/run")
    (case_files.OUT_DIR / "case.json").write_text('{"verdict": ', encoding="utf-8")
    with caplog.at_level(logging.ERROR, logger="chimera.api"):
        for r in [client.get("/api/case"), client.post("/api/actions/reset-priya.s/approve")]:
            assert r.status_code == 500
            assert r.json() == {"detail": "The case files could not be read"}
    assert "case.json" in caplog.text
    assert str(case_files.OUT_DIR) not in client.get("/api/case").text


def test_approvals_are_cleared_inside_the_run_lock(client, monkeypatch):
    as_user(client, "analyst")
    calls = []
    original = case_files.run_investigation

    def spy(on_success, night="attack"):
        def wrapped():
            calls.append(case_files.lock._is_owned())
            on_success()

        return original(wrapped, night)

    monkeypatch.setattr(case_files, "run_investigation", spy)
    assert client.post("/api/case/run").status_code == 200
    assert calls == [True]


def test_role_change_without_a_role_is_422(client):
    viewer_id = user_id(client, "viewer@acme.test")
    assert client.patch(f"/api/users/{viewer_id}/role", json={}).status_code == 422


@pytest.mark.parametrize(
    "body, night",
    [
        (None, "attack"),
        ({}, "attack"),
        ({"night": "quiet"}, "quiet"),
        ({"night": "random"}, "random"),
    ],
)
def test_run_passes_the_chosen_night_to_the_engine(client, monkeypatch, body, night):
    seen = []

    def recording_engine(night="attack"):
        seen.append(night)
        fake_engine()

    monkeypatch.setattr(case_files, "run_engine", recording_engine)
    as_user(client, "analyst")
    r = (
        client.post("/api/case/run", json=body)
        if body is not None
        else client.post("/api/case/run")
    )
    assert r.status_code == 200
    assert seen == [night]


@pytest.mark.parametrize("night", ["../etc", "data", "ATTACK", "dos", "chain", 7])
def test_run_rejects_an_unknown_night(client, night):
    as_user(client, "analyst")
    assert client.post("/api/case/run", json={"night": night}).status_code == 422


def test_viewer_cannot_run_any_night(client):
    as_user(client, "viewer")
    assert client.post("/api/case/run", json={"night": "random"}).status_code == 403


@pytest.mark.parametrize(
    "night, found, steps, inferred",
    [
        ("attack", True, 5, 0),
        ("stopped", True, 3, 0),
        ("gap", True, 5, 1),
        ("quiet", False, 0, 0),
        ("spray", False, 0, 0),
        ("late_work", False, 0, 0),
        ("random", True, 5, 0),
    ],
)
def test_real_engine_gives_each_test_case_its_verdict(
    monkeypatch, tmp_path, night, found, steps, inferred
):
    monkeypatch.setattr(case_files, "OUT_DIR", tmp_path / "out")
    case = case_files.run_investigation(lambda: None, night=night)
    assert case["verdict"]["found"] is found
    assert len(case["chain"]) == steps
    assert sum(s["inferred"] for s in case["chain"]) == inferred
    assert (tmp_path / "out" / "intake.json").exists()
    assert (tmp_path / "out" / "stress" / "40.json").exists()


def raw_attack_night():
    with open(case_files.BASELINE_DIR / "events.jsonl", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    rows.sort(key=lambda row: row["received_at"])
    return "".join(row["raw"] + "\n" for row in rows)


def test_upload_runs_the_real_engine_on_raw_lines(client):
    as_user(client, "analyst")
    r = client.post(
        "/api/case/upload?name=C:\\logs\\night.log", content=raw_attack_night() + "not a log line\n"
    )
    assert r.status_code == 200
    assert r.json() == {"events": 5124, "unparsed": 1, "formats": {"key=value": 5124}}
    assert client.get("/api/case/version").json()["source"] == {
        "kind": "upload",
        "name": "night.log",
        **r.json(),
    }
    case = client.get("/api/case").json()
    assert case["verdict"]["found"] is True
    assert [s["stage"] for s in case["chain"]][-1] == "Exfiltration"
    assert case["truth_score"]["planted"] == 0
    assert client.get("/api/intake").json()["summary"]["events"] == 5124
    assert client.get("/api/case/stress/40").status_code == 200


def test_viewer_cannot_upload(client):
    r = as_user(client, "viewer").post("/api/case/upload", content="03:00:00 dc LOGON user=a")
    assert r.status_code == 403


@pytest.mark.parametrize(
    "body, status, detail",
    [
        ("", 422, "The file is empty"),
        ("  \n\n", 422, "The file is empty"),
        ("hello\nworld\n", 422, "None of the 2 lines could be read as a log line"),
        (
            '{"ts": "2026-11-13T03:00:00Z", "user": "a"}\n'
            '{"ts": "2026-11-14T03:00:01Z", "user": "a"}\n',
            422,
            "The lines cover 25 hours. Upload at most 24 hours of logs at a time",
        ),
    ],
)
def test_unusable_upload_is_rejected_and_keeps_the_case(client, body, status, detail):
    as_user(client, "analyst").post("/api/case/run")
    client.post("/api/actions/reset-priya.s/approve")
    r = client.post("/api/case/upload", content=body)
    assert r.status_code == status
    assert r.json() == {"detail": detail}
    assert client.get("/api/case").json() == CASE
    assert len(client.get("/api/approvals").json()) == 1


def test_upload_over_the_limit_is_413(client, monkeypatch):
    monkeypatch.setattr(api_main, "UPLOAD_LIMIT_BYTES", 10)
    r = as_user(client, "analyst").post("/api/case/upload", content="03:00:00 dc LOGON user=abc")
    assert r.status_code == 413


def test_failed_upload_engine_keeps_the_old_case_and_approvals(client, monkeypatch, caplog):
    as_user(client, "analyst").post("/api/case/run")
    client.post("/api/actions/reset-priya.s/approve")

    def broken(args):
        raise RuntimeError("Link stage crashed")

    monkeypatch.setattr(case_files, "run_module", broken)
    with caplog.at_level(logging.ERROR, logger="chimera.api"):
        r = client.post("/api/case/upload", content="03:00:00 dc LOGON user=abc")
    assert r.status_code == 500
    assert r.json() == {"detail": "The investigation failed"}
    assert "Link stage crashed" in caplog.text
    assert "user=abc" not in caplog.text
    assert client.get("/api/case").json() == CASE
    assert len(client.get("/api/approvals").json()) == 1


def test_upload_clears_approvals_from_the_previous_case(client):
    as_user(client, "analyst").post("/api/case/run")
    client.post("/api/actions/reset-priya.s/approve")
    assert client.post("/api/case/upload", content=raw_attack_night()).status_code == 200
    assert client.get("/api/approvals").json() == []


def test_version_changes_when_the_case_or_approvals_change(client):
    as_user(client, "viewer")
    assert client.get("/api/case/version").json() == {"case": None, "approvals": 0, "source": None}
    as_user(client, "analyst").post("/api/case/run", json={"night": "spray"})
    first = client.get("/api/case/version").json()
    assert first["case"] is not None
    assert first["source"] == {"kind": "simulated", "name": "spray"}
    client.post("/api/actions/reset-priya.s/approve")
    assert client.get("/api/case/version").json() == {**first, "approvals": 1}
    time.sleep(0.01)
    client.post("/api/case/run")
    assert client.get("/api/case/version").json()["case"] != first["case"]


def test_version_needs_sign_in(client):
    client.cookies.clear()
    assert client.get("/api/case/version").status_code == 401
