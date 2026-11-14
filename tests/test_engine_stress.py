import json

from engine.run import investigate, load_data, run
from engine.stress import LEVELS, damage
from tests.test_contract import assert_case_contract

EVENTS, FILES, PLANTED = load_data("data")


def test_damage_deletes_the_level_and_delays_a_fifth_of_the_rest():
    assert damage(EVENTS, 0, 7) == EVENTS
    kept = damage(EVENTS, 20, 7)
    assert len(kept) == len(EVENTS) - round(len(EVENTS) * 0.2)
    assert kept == damage(EVENTS, 20, 7)  # same seed, same result
    original = {e["id"]: e for e in EVENTS}
    changed = [e for e in kept if e["received_at"] != original[e["id"]]["received_at"]]
    assert 0 < len(changed) <= round(len(kept) * 0.2)
    for e in changed:
        assert e["ts"] <= e["received_at"]
    assert [e["received_at"] for e in kept] == sorted(e["received_at"] for e in kept)


def test_run_writes_nine_stress_files(tmp_path):
    case = run("data", tmp_path)
    cases = {}
    for level in LEVELS:
        cases[level] = json.loads((tmp_path / "stress" / f"{level:02d}.json").read_text("utf-8"))
        assert_case_contract(cases[level])
        assert cases[level]["level"] == level
        assert cases[level]["deleted"] == round(len(EVENTS) * level / 100)
    assert cases[0] == case
    assert cases[40]["verdict"]["confidence"] < cases[0]["verdict"]["confidence"]


def test_deleted_exhibits_come_back_marked_not_present(tmp_path):
    run("data", tmp_path)
    base = {s["stage"]: s for s in json.loads((tmp_path / "case.json").read_text("utf-8"))["chain"]}
    seen_missing = False
    for level in LEVELS[1:]:
        case = json.loads((tmp_path / "stress" / f"{level:02d}.json").read_text("utf-8"))
        event_ids = {e["id"] for e in case["events"]}
        for step in case["chain"]:
            for x in step["exhibits"]:
                if not x["present"]:
                    seen_missing = True
                    assert x["id"] in {b["id"] for b in base[step["stage"]]["exhibits"]}
                    assert x["id"] not in event_ids
    assert seen_missing


def test_investigate_records_level_and_deleted():
    case = investigate(EVENTS[:-10], FILES, PLANTED, level=5, deleted=10)
    assert (case["level"], case["deleted"]) == (5, 10)
