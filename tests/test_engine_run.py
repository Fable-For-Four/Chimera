import json
import time

from engine.run import run
from tests.test_contract import assert_case_contract


def test_run_writes_a_case_that_passes_the_contract(tmp_path):
    (tmp_path / "stress").mkdir()
    (tmp_path / "stress" / "05.json").write_text("{}")  # stale file from a sample run
    start = time.perf_counter()
    case = run("data", tmp_path)
    assert time.perf_counter() - start < 20

    written = json.loads((tmp_path / "case.json").read_text(encoding="utf-8"))
    assert written == case
    assert json.loads((tmp_path / "stress" / "00.json").read_text(encoding="utf-8")) == case
    assert not (tmp_path / "stress" / "05.json").exists()
    assert_case_contract(case)

    assert [s["name"] for s in case["stages"]] == [
        "Sort",
        "Profile",
        "Score",
        "Link",
        "Challenge",
        "Report",
    ]
    assert [s["step"] for s in case["chain"]] == [1, 2, 3, 4, 5]
    assert sum(h["share"] for h in case["hypotheses"]) == 100


def test_case_events_are_consistent(tmp_path):
    case = run("data", tmp_path)
    events = case["events"]
    ids = [e["id"] for e in events]
    assert len(ids) == len(set(ids))
    for step in case["chain"]:
        for x in step["exhibits"]:
            assert x["id"] in ids
            assert next(e for e in events if e["id"] == x["id"])["step"] == step["step"]

    t = case["truth_score"]
    assert t["missed"] == [e["id"] for e in events if e["truth"] == "missed"]
    assert t["found"] == sum(e["truth"] == "found" for e in events)
    assert t["false_links"] == [e["id"] for e in events if e["truth"] == "false_link"]
    assert (t["planted"], t["found"], t["recall"], t["precision"]) == (12, 11, 92, 100)
    assert sum(e["score"] < 0.30 and e["truth"] is None for e in events) == 40
