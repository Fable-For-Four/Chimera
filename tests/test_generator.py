from datetime import datetime

from generator.__main__ import build

ATTACK = [
    "priya.s",
    "svc-backup",
    "WS-PRIYA-014",
    "DC-01",
    "FIN-SRV-02",
    "203.0.113.47",
    "198.51.100.23",
]


def parse(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def test_same_seed_same_files():
    assert build(7) == build(7)


def test_size_truth_and_late_events():
    events, files = build(7)
    assert 5100 <= len(events) <= 5200
    ids = {e["id"]: i for i, e in enumerate(events)}
    by_id = {e["id"]: e for e in events}
    planted = files["truth.json"]["planted"]
    assert len(planted) == 12
    late = [e for e in events if (parse(e["received_at"]) - parse(e["ts"])).seconds > 120]
    assert len(late) == 212
    assert [e["received_at"] for e in events] == sorted(e["received_at"] for e in events)
    late_planted = [i for i in planted if i in {e["id"] for e in late}]
    assert len(late_planted) == 1 and by_id[late_planted[0]]["action"] == "LOGON"
    ticket = next(i for i in planted if by_id[i]["action"] == "TICKET_REQ")
    logon = late_planted[0]
    assert ids[logon] > ids[ticket] and by_id[logon]["ts"] < by_id[ticket]["ts"]


def test_no_attack_entity_is_a_hub():
    events, _ = build(7)
    for name in ATTACK:
        n = sum(name in (e["user"], e["host"], e["src"], e["dst"]) for e in events)
        assert n / len(events) <= 0.05, name


def test_raw_matches_example():
    events, _ = build(7)
    e = next(e for e in events if e["action"] == "AUTH_OK" and e["ts"].endswith("03:12:17Z"))
    assert e["raw"] == "03:12:17 vpn-gw AUTH_OK user=priya.s src=203.0.113.47 geo=RO"


def test_dos_scenario_is_one_source_flooding_one_target():
    events, files = build(7, "dos")
    by_id = {e["id"]: e for e in events}
    flood = [by_id[i] for i in files["truth.json"]["planted"]]
    assert len(flood) == 1800
    assert {(e["src"], e["dst"], e["action"]) for e in flood} == {
        ("203.0.113.77", "MAIL-01", "CONN_OPEN")
    }
    assert max(e["ts"] for e in flood) < "2026-11-14T04:03:00Z"
    assert len(events) == 5087 + 25 + 1800
    assert build(7, "dos") == build(7, "dos")
