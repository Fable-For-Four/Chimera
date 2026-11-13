import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from api import auth, case_files, db
from api import email as mailer
from api.main import app

SECRET = "test-secret-that-is-at-least-32-characters"
APP_URL = "http://localhost:3000"
INVALID = {"detail": "This link is invalid or has expired"}
REAL_SEND = mailer.send_verification_email


class FakeSender:
    def __init__(self):
        self.calls = []

    def __call__(self, to, name, link):
        self.calls.append({"to": to, "name": name, "link": link})

    def last_token(self):
        return parse_qs(urlparse(self.calls[-1]["link"]).query)["token"][0]


@pytest.fixture
def sender(monkeypatch):
    fake = FakeSender()
    monkeypatch.setattr(mailer, "send_verification_email", fake)
    return fake


@pytest.fixture(autouse=True)
def restore_resend_key(monkeypatch):
    monkeypatch.setattr(mailer.resend, "api_key", mailer.resend.api_key)


@pytest.fixture
def client(monkeypatch, tmp_path, sender):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("APP_URL", APP_URL)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(auth, "BCRYPT_COST", 4)
    monkeypatch.setattr(case_files, "OUT_DIR", tmp_path / "out")
    with TestClient(app) as c:
        yield c


def signup(client, email="new@example.com", name="New Person"):
    body = {"email": email, "name": name, "password": "good-password"}
    return client.post("/api/auth/signup", json=body)


def verify(client, token):
    return client.post("/api/auth/verify", json={"token": token})


def write_case():
    path = case_files.OUT_DIR / "case.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"actions": []}), encoding="utf-8")


def test_signup_sends_one_email_with_a_link_under_app_url(client, sender):
    assert signup(client).status_code == 201
    assert len(sender.calls) == 1
    call = sender.calls[0]
    assert call["to"] == "new@example.com"
    assert call["name"] == "New Person"
    assert call["link"].startswith(f"{APP_URL}/verify?token=")


def test_new_user_is_blocked_until_verified(client, sender):
    write_case()
    signup(client)
    blocked = client.get("/api/case")
    assert blocked.status_code == 403
    assert blocked.json() == {"detail": "Confirm your email first"}
    r = verify(client, sender.last_token())
    assert r.status_code == 200
    assert r.json()["verified"] is True
    assert client.get("/api/case").status_code == 200
    assert client.get("/api/auth/me").json()["verified"] is True


def test_a_token_works_once(client, sender):
    signup(client)
    token = sender.last_token()
    assert verify(client, token).status_code == 200
    second = verify(client, token)
    assert second.status_code == 400
    assert second.json() == INVALID


def test_expired_and_made_up_tokens_get_the_same_400(client, sender):
    signup(client)
    token = sender.last_token()
    conn = db.connect()
    past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat(timespec="seconds")
    conn.execute("UPDATE email_tokens SET expires_at = ?", (past,))
    conn.commit()
    conn.close()
    expired = verify(client, token)
    made_up = verify(client, "made-up-token")
    assert expired.status_code == made_up.status_code == 400
    assert expired.json() == made_up.json() == INVALID
    assert client.get("/api/auth/me").json()["verified"] is False


def test_token_lasts_30_minutes(client, sender):
    signup(client)
    conn = db.connect()
    expires = conn.execute("SELECT expires_at FROM email_tokens").fetchone()[0]
    conn.close()
    left = datetime.fromisoformat(expires) - datetime.now(UTC)
    assert timedelta(minutes=29) < left <= timedelta(minutes=30)


def test_send_again_makes_the_earlier_token_stop_working(client, sender):
    signup(client)
    first = sender.last_token()
    r = client.post("/api/auth/resend-verification")
    assert r.status_code == 204
    assert len(sender.calls) == 2
    second = sender.last_token()
    assert first != second
    assert verify(client, first).json() == INVALID
    assert verify(client, second).status_code == 200


def test_send_again_needs_sign_in_and_an_unverified_email(client, sender):
    assert client.post("/api/auth/resend-verification").status_code == 401
    signup(client)
    verify(client, sender.last_token())
    r = client.post("/api/auth/resend-verification")
    assert r.status_code == 409
    assert len(sender.calls) == 1


def test_only_the_token_hash_is_stored(client, sender):
    signup(client)
    token = sender.last_token()
    conn = db.connect()
    stored = conn.execute("SELECT token_hash FROM email_tokens").fetchone()[0]
    conn.close()
    assert stored != token
    assert stored == auth.hash_token(token)
    assert len(token) >= 40


def test_verify_does_not_need_a_session(client, sender):
    signup(client)
    token = sender.last_token()
    client.cookies.clear()
    r = verify(client, token)
    assert r.status_code == 200
    assert r.json()["email"] == "new@example.com"
    assert "password_hash" not in r.text


def test_without_a_key_signup_works_and_the_link_is_logged(monkeypatch, client, caplog):
    monkeypatch.setattr(mailer, "send_verification_email", REAL_SEND)
    sent = []
    monkeypatch.setattr(mailer.resend.Emails, "send", lambda params: sent.append(params))
    with caplog.at_level(logging.WARNING, logger="chimera.email"):
        assert signup(client, email="nokey@example.com").status_code == 201
    assert f"{APP_URL}/verify?token=" in caplog.text
    assert sent == []


def test_with_a_key_the_email_goes_through_resend_and_the_link_is_not_logged(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "team@example.com")
    sent = []
    monkeypatch.setattr(mailer.resend.Emails, "send", lambda params: sent.append(params))
    link = f"{APP_URL}/verify?token=abc123"
    with caplog.at_level(logging.DEBUG, logger="chimera.email"):
        mailer.send_verification_email("a@example.com", "<b>Pat</b>", link)
    assert len(sent) == 1
    params = sent[0]
    assert params["from"] == "team@example.com"
    assert params["to"] == ["a@example.com"]
    assert params["subject"] == "Confirm your email"
    assert link in params["text"]
    assert "This link works for 30 minutes." in params["text"]
    assert "&lt;b&gt;Pat&lt;/b&gt;" in params["html"]
    assert "<b>Pat</b>" not in params["html"]
    assert "abc123" not in caplog.text


def test_a_failing_resend_call_does_not_fail_signup(monkeypatch, client, caplog):
    monkeypatch.setattr(mailer, "send_verification_email", REAL_SEND)
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    def failing(params):
        raise RuntimeError("resend is down")

    monkeypatch.setattr(mailer.resend.Emails, "send", failing)
    with caplog.at_level(logging.ERROR, logger="chimera.email"):
        r = signup(client, email="down@example.com")
    assert r.status_code == 201
    assert "Could not send the verification email: RuntimeError" in caplog.text
    assert client.get("/api/auth/me").status_code == 200


def test_app_url_with_a_trailing_slash_gives_a_clean_link(monkeypatch, client, sender):
    monkeypatch.setenv("APP_URL", "https://chimera.example.com/")
    signup(client)
    assert sender.calls[0]["link"].startswith("https://chimera.example.com/verify?token=")


def test_verifying_one_user_does_not_cancel_another_users_token(client, sender):
    signup(client, email="a@example.com")
    token_a = sender.last_token()
    client.cookies.clear()
    signup(client, email="b@example.com")
    token_b = sender.last_token()
    assert verify(client, token_b).json()["email"] == "b@example.com"
    r = verify(client, token_a)
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


def test_send_again_for_one_user_leaves_another_users_token_valid(client, sender):
    signup(client, email="a@example.com")
    token_a = sender.last_token()
    client.cookies.clear()
    signup(client, email="b@example.com")
    client.post("/api/auth/resend-verification")
    assert verify(client, token_a).status_code == 200


def test_verify_sets_used_at_and_keeps_the_role(client, sender):
    signup(client)
    before = client.get("/api/auth/me").json()
    verify(client, sender.last_token())
    after = client.get("/api/auth/me").json()
    assert after["role"] == before["role"]
    conn = db.connect()
    used = conn.execute("SELECT used_at FROM email_tokens").fetchone()[0]
    verified = conn.execute("SELECT email_verified_at FROM users").fetchone()[0]
    conn.close()
    assert used is not None
    assert verified is not None


def test_verify_without_a_token_field_is_422(client):
    assert client.post("/api/auth/verify", json={}).status_code == 422


def test_an_old_token_is_400_even_after_the_email_is_verified(client, sender):
    signup(client)
    first = sender.last_token()
    client.post("/api/auth/resend-verification")
    verify(client, sender.last_token())
    assert client.get("/api/auth/me").json()["verified"] is True
    r = verify(client, first)
    assert r.status_code == 400
    assert r.json() == INVALID


def test_a_failed_verify_does_not_verify_the_user(client, sender):
    signup(client)
    assert verify(client, "wrong").status_code == 400
    assert client.get("/api/auth/me").json()["verified"] is False


def test_send_again_emails_the_same_address_and_name(client, sender):
    signup(client, name="Sam Lee")
    client.post("/api/auth/resend-verification")
    assert sender.calls[1]["to"] == "new@example.com"
    assert sender.calls[1]["name"] == "Sam Lee"


def test_a_resend_error_echoing_the_bare_token_is_not_logged(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    def failing(params):
        raise ValueError("bad request: token=bare-token-123&x=%2Fverify%3Ftoken%3Dbare-token-123")

    monkeypatch.setattr(mailer.resend.Emails, "send", failing)
    with caplog.at_level(logging.ERROR, logger="chimera.email"):
        link = f"{APP_URL}/verify?token=bare-token-123"
        mailer.send_verification_email("a@example.com", "Pat", link)
    assert "ValueError" in caplog.text
    assert "bare-token-123" not in caplog.text


def test_signup_saves_the_user_and_token_together(client, monkeypatch):
    def broken(db, user_id):
        raise RuntimeError("token table locked")

    monkeypatch.setattr("api.main.new_verification_token", broken)
    with pytest.raises(RuntimeError):
        signup(client)
    conn = db.connect()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    assert count == 0


def test_an_over_long_token_is_rejected_before_lookup(client):
    assert verify(client, "x" * 201).status_code == 422


def test_a_resend_error_is_logged_without_the_token(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    link = f"{APP_URL}/verify?token=secret-token-value"

    def failing(params):
        raise RuntimeError(f"rejected request containing {link}")

    monkeypatch.setattr(mailer.resend.Emails, "send", failing)
    with caplog.at_level(logging.ERROR, logger="chimera.email"):
        mailer.send_verification_email("a@example.com", "Pat", link)
    assert "Could not send the verification email" in caplog.text
    assert "secret-token-value" not in caplog.text
