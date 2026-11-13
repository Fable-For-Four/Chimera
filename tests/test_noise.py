import ipaddress
import random
from collections import Counter

from generator import noise, scenario

ATTACK_ONLY = {"priya.s", "203.0.113.47", "198.51.100.23"}


def setup(seed=7):
    company = scenario.build_company(random.Random(seed))
    rng = random.Random(seed + 1)
    return company, noise.normal_events(rng, company), noise.lone_oddities(rng, company)


def entities(e):
    values = [e["user"], e["host"], e["src"], e["dst"], e["attrs"].get("actor"), e["attrs"].get("member")]
    return {v for v in values if v}


def is_outside(address, company):
    if address in company["machines"]:
        return False
    return ipaddress.ip_address(address) not in ipaddress.ip_network("10.0.0.0/8")


def test_same_seed_gives_same_noise():
    assert setup(7)[1:] == setup(7)[1:]


def test_counts_add_up_to_5124():
    _, normal, odd = setup()
    assert len(normal) == noise.NOISE_COUNT
    assert len(odd) == 25
    assert len(normal) + len(odd) + len(scenario.attack_events()) == 5124


def test_noise_is_spread_evenly_over_the_window():
    _, normal, _ = setup()
    per_5_min = Counter((e["ts"] - scenario.WINDOW_START).seconds // 300 for e in normal)
    assert len(per_5_min) == 18
    assert all(230 <= n <= 340 for n in per_5_min.values())
    assert all(scenario.WINDOW_START <= e["ts"] <= scenario.WINDOW_END for e in normal)


def test_noise_stays_inside_every_baseline():
    company, normal, _ = setup()
    history = scenario.build_history(company)
    for e in normal:
        assert e["action"] not in ("AUTH_FAIL", "GROUP_ADD", "PROC_START", "TICKET_REQ")
        assert not entities(e) & ATTACK_ONLY
        if e["user"] == "svc-backup":
            assert e["action"] in ("JOB_START", "JOB_END") and e["src"] == "BKP-01"
        elif e["user"]:
            baseline = history["users"][e["user"]]
            assert baseline["hours"] == [22, 6]
            assert e["action"] in baseline["actions"]
        if e["action"] == "AUTH_OK":
            assert e["attrs"]["geo"] == "IN"
        if e["action"] == "FILE_READ":
            assert e["attrs"]["files"] < 500
        if e["action"] == "LOGON":
            assert e["attrs"]["type"] != "interactive" or e["user"] != "svc-backup"
        if e["action"] in ("CONN_OPEN", "CONN_CLOSE") and is_outside(e["dst"], company):
            assert e["dst"] in history["hosts"][e["src"]]["outside_peers"]
        if e["action"] == "CONN_CLOSE":
            assert e["attrs"]["bytes_out"] < 20 * history["hosts"][e["src"]]["daily_upload_mb"] * 1024**2


def test_backup_verify_runs_at_0320_as_job_events_only():
    _, normal, _ = setup()
    jobs = [e for e in normal if e["user"] == "svc-backup"]
    assert [e["action"] for e in jobs] == ["JOB_START", "JOB_END"]
    assert jobs[0]["ts"].strftime("%H:%M") == "03:20"


def test_no_attack_entity_is_a_hub():
    _, normal, odd = setup()
    all_events = normal + odd + scenario.attack_events()
    counts = Counter(v for e in all_events for v in entities(e))
    limit = 0.05 * len(all_events)
    for name in ["priya.s", "svc-backup", "WS-PRIYA-014", "DC-01", "FIN-SRV-02", "203.0.113.47", "198.51.100.23"]:
        assert counts[name] < limit, (name, counts[name], limit)


def test_oddities_share_nothing_with_the_attack():
    _, _, odd = setup()
    attack_entities = set().union(*(entities(e) for e in scenario.attack_events()))
    for e in odd:
        assert not entities(e) & attack_entities, e


def test_oddity_users_are_all_different_where_they_could_link():
    _, _, odd = setup()
    linkable = [e["user"] for e in odd if e["user"] and e["action"] != "PROC_START"]
    assert len(linkable) == len(set(linkable)) == 15
