from engine.report import write_report
from tests.test_engine_a3 import CASE, EVENTS, LINKED

REACHABLE = CASE["verdict"]["blast_radius"]["reachable"]
ALL_IDS = {e["id"] for e in EVENTS}
SERVICE = {"svc-backup"}


def written(linked=LINKED, ids=ALL_IDS):
    return write_report(linked, REACHABLE, ids, SERVICE)


def test_one_claim_per_step_citing_its_top_exhibit():
    out, line = written()
    assert line == "5 claims, 5 citations"
    assert [c["step"] for c in out["report"]] == [1, 2, 3, 4, 5]
    assert out["report"][0]["text"] == (
        "At 03:12 someone signed in as priya.s from Romania after two failed tries."
    )
    assert out["report"][1]["text"] == "At 03:41 priya.s added svc-backup to Domain Admins."
    for claim in out["report"]:
        step_events = [e for e in LINKED["events"] if e["step"] == claim["step"]]
        assert claim["cites"] == [max(step_events, key=lambda e: e["score"])["id"]]


def test_limits():
    out, _ = written()
    assert out["limits"] == [f"Whether {m} was touched." for m in REACHABLE] + [
        "Whether the files were opened or only copied.",
        "How the password was obtained.",
    ]


def test_three_questions_with_citations_from_the_chain():
    out, _ = written()
    assert [q["q"] for q in out["questions"]] == [
        "Why is svc-backup flagged?",
        "Could this be the account owner?",
        "What can the logs not prove?",
    ]
    chain_ids = {e["id"] for e in LINKED["events"]}
    for q in out["questions"]:
        assert q["cites"] and {c["id"] for c in q["cites"]} <= chain_ids
    assert "admin" in out["questions"][0]["a"].lower()
    assert "exfiltration" in out["questions"][1]["a"]


def test_claims_citing_a_missing_event_are_dropped():
    top = written()[0]["report"][1]["cites"][0]
    out, line = written(ids=ALL_IDS - {top})
    assert [c["step"] for c in out["report"]] == [1, 3, 4, 5]
    assert line == "4 claims, 4 citations"
    assert all(top not in [c["id"] for c in q["cites"]] for q in out["questions"])


def test_inferred_step_has_an_uncited_claim_and_a_limit():
    steps = [dict(s) for s in LINKED["steps"]]
    steps[2] = {**steps[2], "inferred": True, "exhibits": []}
    events = [e for e in LINKED["events"] if e["step"] != 3]
    out, _ = written({"steps": steps, "confidence": 50, "events": events})
    assert out["report"][2] == {
        "text": "The logs do not show lateral movement, but the steps before and after need it.",
        "cites": [],
        "step": 3,
    }
    assert out["limits"][0] == "How lateral movement happened, which the logs do not show."


def test_no_chain_gives_empty_lists():
    out, line = write_report({"steps": [], "confidence": 0, "events": []}, [], ALL_IDS, SERVICE)
    assert out == {"report": [], "limits": [], "questions": []}
    assert line == "0 claims, 0 citations"
