import ipaddress
import random
from datetime import datetime, timedelta, timezone

from generator import scenario

WINDOW_START = datetime(2026, 11, 14, 3, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 11, 14, 4, 30, tzinfo=timezone.utc)


def company(seed=7):
    return scenario.build_company(random.Random(seed))


def test_same_seed_gives_same_company():
    assert company(7) == company(7)
    assert company(7) != company(8)


def test_fifty_unique_users_with_named_ones():
    users = company()["users"]
    names = [u["name"] for u in users]
    assert len(names) == 50
    assert len(set(names)) == 50
    assert {"priya.s", "arjun.m", "neha.k"} <= set(names)


def test_twelve_night_workers_and_priya_works_days():
    users = {u["name"]: u for u in company()["users"]}
    night = [n for n, u in users.items() if u["hours"] == [22, 6]]
    assert len(night) == 12
    assert "arjun.m" in night and "neha.k" in night
    assert users["priya.s"]["hours"] == [9, 19]
    assert all(u["hours"] in ([22, 6], [9, 19]) for u in users.values())


def test_twenty_machines_with_inside_addresses():
    machines = company()["machines"]
    assert len(machines) == 20
    for name in ["MAIL-01", "DC-01", "FIN-SRV-02", "HR-SRV-01", "BKP-01", "PRINT-02", "WS-PRIYA-014", "WS-NEHA-022"]:
        assert name in machines
    assert len([m for m in machines if m.startswith("WS-")]) == 14
    ips = list(machines.values())
    assert len(set(ips)) == 20
    assert all(ipaddress.ip_address(ip) in ipaddress.ip_network("10.0.0.0/8") for ip in ips)


def test_history_baselines():
    history = scenario.build_history(company())
    assert history["users"]["priya.s"]["countries"] == ["IN"]
    assert history["users"]["priya.s"]["hours"] == [9, 19]
    assert "WS-PRIYA-014" in history["users"]["priya.s"]["hosts"]
    assert all("GROUP_ADD" not in u["actions"] for u in history["users"].values())
    assert history["service_accounts"]["svc-backup"] == {
        "logon_types": ["batch"], "sources": ["BKP-01"], "job_hours": [1], "admin": False,
    }
    assert history["hosts"]["FIN-SRV-02"] == {"outside_peers": [], "daily_upload_mb": 50}
    assert len(history["users"]) == 50
    assert len(history["hosts"]) == 20


def test_access():
    access = scenario.build_access(company())
    assert access["priya.s"] == ["WS-PRIYA-014", "MAIL-01"]
    assert access["svc-backup"] == ["BKP-01", "FIN-SRV-02", "HR-SRV-01", "DC-01"]
    assert len(access) == 51


def test_layout_has_fourteen_nodes_inside_the_canvas():
    layout = scenario.LAYOUT
    assert len(layout) == 14
    assert layout["priya.s"] == [190, 240]
    assert all(0 <= x <= 860 and 0 <= y <= 480 for x, y in layout.values())


def attack():
    return scenario.attack_events()


def test_attack_has_twelve_events_in_step_order():
    actions = [e["action"] for e in attack()]
    assert actions == [
        "AUTH_FAIL", "AUTH_FAIL", "AUTH_OK",
        "PROC_START", "GROUP_ADD",
        "LOGON", "TICKET_REQ",
        "SMB_SESSION", "FILE_READ",
        "DNS_QUERY", "CONN_OPEN", "CONN_CLOSE",
    ]


def test_attack_events_have_the_event_shape_and_sit_in_the_window():
    for e in attack():
        assert set(e) == {"ts", "received_at", "source", "action", "user", "host", "src", "dst", "attrs"}
        assert WINDOW_START <= e["ts"] <= WINDOW_END


def test_attack_fields_needed_for_scoring_and_linking():
    events = attack()
    by_action = {e["action"]: e for e in events}
    assert all(e["user"] == "priya.s" and e["src"] == "203.0.113.47" and e["attrs"]["geo"] == "RO" for e in events[:3])
    assert by_action["PROC_START"]["user"] == "priya.s"
    assert by_action["PROC_START"]["host"] == "WS-PRIYA-014"
    assert by_action["PROC_START"]["attrs"]["cmd"] == "net-group"
    assert by_action["GROUP_ADD"]["attrs"] == {"actor": "priya.s", "member": "svc-backup", "group": "Domain-Admins"}
    for action in ["LOGON", "TICKET_REQ", "SMB_SESSION", "FILE_READ"]:
        assert by_action[action]["user"] == "svc-backup"
        assert by_action[action]["src"] == "WS-PRIYA-014"
    assert by_action["LOGON"]["attrs"]["type"] == "interactive"
    assert by_action["TICKET_REQ"]["attrs"]["service"] == "cifs/FIN-SRV-02"
    assert by_action["FILE_READ"]["attrs"] == {"path": "/finance/payroll/2026", "files": 1412}
    for action in ["DNS_QUERY", "CONN_OPEN", "CONN_CLOSE"]:
        assert by_action[action]["src"] == "FIN-SRV-02"
    assert by_action["CONN_OPEN"]["dst"] == "198.51.100.23"


def test_attack_stays_under_the_old_alert_limits():
    events = attack()
    assert sum(e["action"] == "AUTH_FAIL" for e in events) < 5
    close = next(e for e in events if e["action"] == "CONN_CLOSE")
    assert 2_000_000_000 <= close["attrs"]["bytes_out"] < 5 * 1024**3
    assert all(e["attrs"].get("geo") not in ("KP", "IR") for e in events)


def test_only_the_logon_is_late_and_it_arrives_after_the_ticket_request():
    events = attack()
    late = [e for e in events if e["received_at"] - e["ts"] > timedelta(minutes=2)]
    assert [e["action"] for e in late] == ["LOGON"]
    logon = late[0]
    ticket = next(e for e in events if e["action"] == "TICKET_REQ")
    assert logon["received_at"] - logon["ts"] == timedelta(minutes=6)
    assert logon["ts"] < ticket["ts"]
    assert logon["received_at"] > ticket["received_at"]
