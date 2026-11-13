
import pytest

from engine.profile import Profile
from engine.score import LATE_REASON, score_events
from engine.sort import sort_events
from generator.__main__ import build

EVENTS, FILES = build(7)
PLANTED = set(FILES["truth.json"]["planted"])
PROFILE = Profile(FILES["history.json"])


def ev(
    action, user=None, src=None, dst=None, host=None, ts="2026-11-14T03:30:00Z", late=False, **attrs
):
    return {
        "id": "L-X",
        "ts": ts,
        "received_at": ts,
        "source": "x",
        "action": action,
        "user": user,
        "host": host,
        "src": src,
        "dst": dst,
        "attrs": attrs,
        "late": late,
    }


def names(e):
    return [r["name"] for r in score_events([e], PROFILE)[0][0]["reasons"]]


# ---- Sort ----
def test_sort_puts_the_late_logon_before_the_ticket_request():
    ordered, msg = sort_events(EVENTS)
    pos = {e["id"]: i for i, e in enumerate(ordered)}
    planted = {e["action"]: e["id"] for e in ordered if e["id"] in PLANTED}
    assert pos[planted["LOGON"]] < pos[planted["TICKET_REQ"]]
    assert [e["ts"] for e in ordered] == sorted(e["ts"] for e in ordered)
    assert msg == "212 late events moved"


def test_sort_flags_only_events_over_two_minutes_late():
    a = {**ev("HEALTH_OK"), "id": "L-2", "received_at": "2026-11-14T03:32:00Z"}
    b = {**ev("HEALTH_OK"), "id": "L-1", "received_at": "2026-11-14T03:32:01Z"}
    out, _ = sort_events([a, b])
    assert [(e["id"], e["late"]) for e in out] == [
        ("L-1", True),
        ("L-2", False),
    ]  # tie broken by id


# ---- Profile ----
def test_profile_lookups_and_message():
    assert PROFILE.users["priya.s"]["countries"] == ["IN"]
    assert PROFILE.is_service("svc-backup") and not PROFILE.is_service("priya.s")
    assert PROFILE.service_accounts["svc-backup"]["logon_types"] == ["batch"]
    assert PROFILE.hosts["FIN-SRV-02"]["daily_upload_mb"] == 50
    assert PROFILE.message() == "71 baselines from 30 days"


def test_profile_outside_means_not_10_slash_8_and_not_a_machine():
    assert PROFILE.is_outside("198.51.100.23") and PROFILE.is_outside("192.0.2.25")
    assert not PROFILE.is_outside("10.0.1.10") and not PROFILE.is_outside("MAIL-01")


# ---- One test per rule ----
@pytest.mark.parametrize(
    "rule, event",
    [
        ("New country for this user", ev("AUTH_OK", "priya.s", geo="RO")),
        ("Outside the usual hours", ev("MAIL_SEND", "priya.s")),  # 03:xx, Priya works 9 to 19
        (
            "First group change by this user",
            ev("GROUP_ADD", "priya.s", actor="priya.s", member="x", group="g"),
        ),
        (
            "Service account gains admin rights",
            ev("GROUP_ADD", "arjun.m", actor="arjun.m", member="svc-backup", group="Domain-Admins"),
        ),
        ("Lookup command for groups", ev("PROC_START", "arjun.m", cmd="nltest")),
        (
            "Service account used by a person",
            ev("LOGON", "svc-backup", src="BKP-01", type="interactive"),
        ),
        (
            "Wrong machine for this service account",
            ev("SMB_SESSION", "svc-backup", src="WS-PRIYA-014"),
        ),
        (
            "Wrong time for this service account",
            ev("FILE_READ", "svc-backup", src="BKP-01", files=1),
        ),
        ("Large read of files", ev("FILE_READ", "arjun.m", files=500)),
        ("First outside connection", ev("CONN_OPEN", src="FIN-SRV-02", dst="198.51.100.23")),
        (
            "Upload far above normal",
            ev("CONN_CLOSE", src="FIN-SRV-02", dst="MAIL-01", bytes_out=1000 * 1024**2),
        ),
    ],
)
def test_each_rule_fires(rule, event):
    assert rule in names(event)


def test_rules_stay_quiet_on_normal_behaviour():
    assert names(ev("AUTH_OK", "arjun.m", geo="IN")) == []
    assert names(ev("FILE_READ", "arjun.m", files=499)) == []
    assert names(ev("JOB_START", "svc-backup", src="BKP-01")) == []  # exempt from "Wrong time"
    assert names(ev("CONN_OPEN", src="MAIL-01", dst="192.0.2.25")) == []  # known peer
    assert names(ev("CONN_CLOSE", src="FIN-SRV-02", dst="MAIL-01", bytes_out=999 * 1024**2)) == []
    assert names(ev("DNS_QUERY", src="FIN-SRV-02")) == []


def test_failed_tries_then_success_needs_two_fails_inside_five_minutes():
    def fail(t):
        return {**ev("AUTH_FAIL", "arjun.m", geo="IN", ts=t), "id": t}

    ok = ev("AUTH_OK", "arjun.m", geo="IN", ts="2026-11-14T03:10:00Z")
    hit, _ = score_events([fail("2026-11-14T03:06:00Z"), fail("2026-11-14T03:08:00Z"), ok], PROFILE)
    miss, _ = score_events(
        [fail("2026-11-14T03:04:59Z"), fail("2026-11-14T03:08:00Z"), ok], PROFILE
    )
    assert "Failed tries, then success" in [r["name"] for r in hit[-1]["reasons"]]
    assert miss[-1]["reasons"] == []


def test_wrap_around_hours():
    assert (
        names(ev("MAIL_SEND", "arjun.m", ts="2026-11-14T03:30:00Z")) == []
    )  # night worker [22, 6]
    assert "Outside the usual hours" in names(ev("MAIL_SEND", "arjun.m", ts="2026-11-14T12:00:00Z"))


def test_scores_combine_and_late_events_are_discounted():
    odd = ev("PROC_START", "priya.s", cmd="net-group")  # 0.25 and 0.28
    s = score_events([odd], PROFILE)[0][0]["score"]
    assert s == round(1 - 0.75 * 0.72, 2) == 0.46
    late = score_events([{**odd, "late": True}], PROFILE)[0][0]
    assert late["score"] == round(0.46 * 0.9, 2) and late["reasons"][-1] == {
        "name": LATE_REASON,
        "weight": -0.10,
    }


# ---- The "Done when" checks on the real data ----
def scored():
    ordered, _ = sort_events(EVENTS)
    return score_events(ordered, PROFILE)


def test_every_planted_event_but_the_dns_query_is_a_weak_signal():
    out, _ = scored()
    planted = [e for e in out if e["id"] in PLANTED]
    assert len(planted) == 12
    for e in planted:
        if e["action"] == "DNS_QUERY":
            assert e["score"] == 0 and e["reasons"] == []
        else:
            assert e["score"] >= 0.30, e
    logon = next(e for e in planted if e["action"] == "LOGON")
    assert logon["late"] and logon["score"] >= 0.30


def test_normal_noise_stays_under_015_and_only_the_25_oddities_are_in_between():
    out, msg = scored()
    others = [e for e in out if e["id"] not in PLANTED]
    raised = [e for e in others if e["score"] >= 0.15]
    assert len(raised) == 25 and all(0.25 <= e["score"] <= 0.45 for e in raised)
    assert all(e["score"] == 0 for e in others if e["score"] < 0.15)
    assert (
        msg == "26 weak signals"
    )  # 11 planted + 15 oddities (the 10 lookup/off-hours ones score under 0.30)
