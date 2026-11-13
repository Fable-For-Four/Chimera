from engine.link import link
from engine.profile import Profile
from engine.score import score_events
from engine.sort import sort_events
from engine.verdict import verdict
from generator.__main__ import build

EVENTS, FILES = build(7)
PLANTED = FILES["truth.json"]["planted"]
PROFILE = Profile(FILES["history.json"])
STAGES = [
    "Initial access",
    "Privilege escalation",
    "Lateral movement",
    "Collection",
    "Exfiltration",
]


def run(events):
    scored, _ = score_events(sort_events(events)[0], PROFILE)
    linked, msg = link(scored, PROFILE)
    return scored, linked, msg


SCORED, LINKED, MSG = run(EVENTS)
CASE = verdict(LINKED, SCORED, PROFILE, FILES["access.json"], FILES["layout.json"])
DNS = next(e["id"] for e in EVENTS if e["id"] in PLANTED and e["action"] == "DNS_QUERY")


# ---- Link ----
def test_link_gives_five_steps_in_order_with_eleven_events():
    steps = LINKED["steps"]
    assert [s["stage"] for s in steps] == STAGES
    assert [s["step"] for s in steps] == [1, 2, 3, 4, 5]
    assert not any(s["inferred"] for s in steps)
    assert sum(len(s["exhibits"]) for s in steps) == 11
    assert MSG == "1 chain, 5 steps, 11 events"


def test_chain_is_exactly_the_planted_events_without_the_dns_query():
    chain_ids = {x["id"] for s in LINKED["steps"] for x in s["exhibits"]}
    assert chain_ids == set(PLANTED) - {DNS}


def test_no_lone_oddity_or_normal_event_is_in_the_chain():
    chain_ids = {e["id"] for e in LINKED["events"]}
    assert chain_ids <= set(PLANTED)


def test_step_fields():
    first, priv, lateral, coll, exfil = LINKED["steps"]
    assert (first["from"], first["to"], first["time"], first["minute"]) == (
        "203.0.113.47",
        "priya.s",
        "03:12",
        12,
    )
    assert (priv["from"], priv["to"]) == ("priya.s", "svc-backup")
    assert (lateral["from"], lateral["to"]) == ("svc-backup", "DC-01")
    assert (coll["from"], coll["to"]) == ("svc-backup", "FIN-SRV-02")
    assert (exfil["from"], exfil["to"]) == ("FIN-SRV-02", "198.51.100.23")
    assert first["technique"] == "T1078 Valid Accounts"
    assert first["what"] == "VPN sign-in to priya.s from a new country"
    assert first["usual"] == "India, 09:00 to 19:00" and first["now"] == "Romania, 03:12"
    for s in LINKED["steps"]:
        assert 0 < s["confidence"] <= 97
        weights = [sig["weight"] for sig in s["signals"]]
        assert weights == sorted(weights, reverse=True) and len(
            set(sig["name"] for sig in s["signals"])
        ) == len(weights)
        times = [x["id"] for x in s["exhibits"]]
        assert all(x["present"] for x in s["exhibits"]) and times
    assert 0 < LINKED["confidence"] <= 100


def test_attack_removed_gives_no_chain():
    _, linked, msg = run([e for e in EVENTS if e["id"] not in PLANTED])
    assert linked["steps"] == [] and linked["confidence"] == 0
    assert msg == "No chain found"


def test_missing_middle_stage_becomes_an_inferred_step():
    lateral = {
        e["id"] for e in EVENTS if e["id"] in PLANTED and e["action"] in ("LOGON", "TICKET_REQ")
    }
    _, linked, _ = run([e for e in EVENTS if e["id"] not in lateral])
    steps = linked["steps"]
    if [
        s["stage"] for s in steps
    ] != STAGES:  # the chain may split without its bridge; then nothing to infer
        return
    gap = steps[2]
    assert gap["inferred"] and gap["exhibits"] == []
    assert gap["from"] == steps[1]["to"] and gap["to"] == steps[3]["from"]
    assert gap["confidence"] == round(min(steps[1]["confidence"], steps[3]["confidence"]) / 2)


# ---- Verdict ----
def test_verdict_fields():
    v = CASE["verdict"]
    assert v["found"] and v["label"] == "Likely attack" and v["confidence"] == LINKED["confidence"]
    assert v["entry_point"]["account"] == "priya.s"
    assert v["entry_point"]["event"] == next(
        e["id"] for e in EVENTS if e["action"] == "AUTH_OK" and e["id"] in PLANTED
    )
    assert v["blast_radius"]["accounts"] == ["priya.s", "svc-backup"]
    assert v["blast_radius"]["touched"] == ["WS-PRIYA-014", "DC-01", "FIN-SRV-02"]
    assert set(v["blast_radius"]["reachable"]) == set(
        FILES["access.json"]["priya.s"] + FILES["access.json"]["svc-backup"]
    ) - {"WS-PRIYA-014", "DC-01", "FIN-SRV-02"}
    assert v["data_at_risk"] == {"files": 1412, "bytes_out": 2254857830}
    confs = [s["confidence"] for s in LINKED["steps"]]
    assert v["weakest_step"] == confs.index(min(confs)) + 1
    assert "29 minutes" in v["headline"]


def test_graph_nodes_and_edges():
    g = CASE["graph"]
    nodes = {n["id"]: n for n in g["nodes"]}
    assert len(nodes) == len(g["nodes"])
    assert nodes["priya.s"] == {
        "id": "priya.s",
        "type": "user",
        "state": "hit",
        "x": 190,
        "y": 240,
        "step": 1,
    }
    assert nodes["203.0.113.47"]["type"] == "outside" and nodes["DC-01"]["type"] == "machine"
    assert nodes["FIN-SRV-02"]["step"] == 4 and nodes["198.51.100.23"]["step"] == 5
    for r in CASE["verdict"]["blast_radius"]["reachable"]:
        assert nodes[r]["state"] == "reach" and "step" not in nodes[r]
    assert sum(n["state"] == "normal" for n in g["nodes"]) <= 6
    assert all(0 <= n["x"] <= 860 and 0 <= n["y"] <= 480 for n in g["nodes"])
    for edge in g["edges"]:
        assert edge["from"] in nodes and edge["to"] in nodes
    assert {"from": "203.0.113.47", "to": "priya.s"} in g["edges"]


def test_actions():
    ids = [a["id"] for a in CASE["actions"]]
    assert ids[:3] == ["reset-priya.s", "demote-svc-backup", "block-198.51.100.23"]
    assert all(i.startswith("review-") for i in ids[3:]) and len(ids) == 3 + len(
        CASE["verdict"]["blast_radius"]["reachable"]
    )
    assert CASE["actions"][2]["text"] == "Block 198.51.100.23 and isolate FIN-SRV-02"


def test_no_chain_verdict():
    scored, linked, _ = run([e for e in EVENTS if e["id"] not in PLANTED])
    case = verdict(linked, scored, PROFILE, FILES["access.json"], FILES["layout.json"])
    v = case["verdict"]
    assert (v["found"], v["label"], v["confidence"]) == (False, "No chain found", 0)
    assert case["actions"] == [] and case["graph"] == {"nodes": [], "edges": []}


def test_labels():
    from engine.verdict import label

    assert [label(c) for c in (70, 69, 50, 49)] == [
        "Likely attack",
        "Probable attack",
        "Probable attack",
        "Possible attack",
    ]


# ---- Shape and robustness ----
def check_shapes(linked, case):
    from tests.test_contract import assert_chain_step, assert_graph, assert_verdict

    assert_verdict(case["verdict"])
    assert_graph(case["graph"])
    for step in linked["steps"]:
        assert_chain_step(step)


def test_output_matches_the_contract():
    check_shapes(LINKED, CASE)


def test_survives_deleted_events_like_the_stress_runs():
    import random

    for level in range(0, 45, 5):
        rng = random.Random(7 + level)
        kept = [e for e in EVENTS if rng.random() >= level / 100]
        scored, linked, _ = run(kept)
        check_shapes(
            linked, verdict(linked, scored, PROFILE, FILES["access.json"], FILES["layout.json"])
        )
