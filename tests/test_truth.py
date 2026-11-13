import copy
import json

from engine.truth import load_planted, score_truth


def exhibit(event_id, present=True):
    return {"id": event_id, "raw": "", "late": False, "present": present}


CHAIN = [
    {"step": 1, "exhibits": [exhibit("L-0001"), exhibit("L-0002")]},
    {"step": 2, "exhibits": [exhibit("L-0003", present=False), exhibit("L-0009")]},
    {"step": 3, "inferred": True, "exhibits": []},
]
PLANTED = ["L-0001", "L-0002", "L-0003", "L-0004"]
EVENTS = [
    {"id": event_id, "truth": None}
    for event_id in ["L-0001", "L-0002", "L-0003", "L-0004", "L-0009", "L-0050"]
]


def test_found_missed_and_false_links():
    score, _ = score_truth(PLANTED, CHAIN, EVENTS)
    assert score == {
        "planted": 4,
        "found": 2,
        "linked": 3,
        "recall": 50,
        "precision": 67,
        "missed": ["L-0003", "L-0004"],
        "false_links": ["L-0009"],
    }


def test_each_event_is_marked_with_its_truth():
    _, events = score_truth(PLANTED, CHAIN, EVENTS)
    assert {e["id"]: e["truth"] for e in events} == {
        "L-0001": "found",
        "L-0002": "found",
        "L-0003": "missed",
        "L-0004": "missed",
        "L-0009": "false_link",
        "L-0050": None,
    }


def test_input_is_not_changed():
    events = copy.deepcopy(EVENTS)
    chain = copy.deepcopy(CHAIN)
    score_truth(PLANTED, chain, events)
    assert events == EVENTS
    assert chain == CHAIN


def test_percentages_round_half_up_to_whole_numbers():
    planted = [f"L-{n:04d}" for n in range(1, 13)]
    chain = [{"exhibits": [exhibit(f"L-{n:04d}") for n in range(1, 12)]}]
    score, _ = score_truth(planted, chain, [])
    assert (score["found"], score["recall"], score["precision"]) == (11, 92, 100)
    assert score["missed"] == ["L-0012"]


def test_no_chain_finds_nothing_without_dividing_by_zero():
    score, _ = score_truth(PLANTED, [], EVENTS)
    assert score["found"] == score["linked"] == 0
    assert score["recall"] == score["precision"] == 0
    assert score["missed"] == PLANTED


def test_a_clean_night_with_nothing_planted():
    score, events = score_truth([], [], EVENTS)
    assert score["planted"] == score["recall"] == score["precision"] == 0
    assert all(e["truth"] is None for e in events)


def test_truth_score_has_exactly_the_contract_keys():
    score, _ = score_truth(PLANTED, CHAIN, EVENTS)
    assert set(score) == {
        "planted",
        "found",
        "linked",
        "recall",
        "precision",
        "missed",
        "false_links",
    }


def test_marked_events_keep_every_other_field_and_order():
    events = [
        {"id": "L-0002", "time": "03:12:17", "score": 0.62, "truth": None},
        {"id": "L-0001", "time": "03:09:01", "score": 0.4},
    ]
    _, marked = score_truth(PLANTED, CHAIN, events)
    assert [e["id"] for e in marked] == ["L-0002", "L-0001"]
    assert marked[0] == {"id": "L-0002", "time": "03:12:17", "score": 0.62, "truth": "found"}
    assert marked[1] == {"id": "L-0001", "time": "03:09:01", "score": 0.4, "truth": "found"}


def test_an_inferred_step_with_no_exhibits_adds_nothing():
    chain = [{"step": 1, "inferred": True, "exhibits": []}, {"step": 2, "inferred": True}]
    score, _ = score_truth(PLANTED, chain, EVENTS)
    assert score["linked"] == 0
    assert score["precision"] == 0


def test_an_exhibit_without_a_present_key_counts_as_present():
    chain = [{"exhibits": [{"id": "L-0001"}]}]
    score, _ = score_truth(PLANTED, chain, EVENTS)
    assert score["found"] == score["linked"] == 1


def test_the_same_event_in_two_steps_is_counted_once():
    chain = [
        {"exhibits": [exhibit("L-0001")]},
        {"exhibits": [exhibit("L-0001"), exhibit("L-0009")]},
    ]
    score, _ = score_truth(PLANTED, chain, EVENTS)
    assert score["linked"] == 2
    assert score["found"] == 1
    assert score["false_links"] == ["L-0009"]


def test_an_event_absent_in_one_step_but_present_in_another_is_linked():
    chain = [
        {"exhibits": [exhibit("L-0001", present=False)]},
        {"exhibits": [exhibit("L-0001")]},
    ]
    score, _ = score_truth(PLANTED, chain, EVENTS)
    assert score["found"] == 1
    assert "L-0001" not in score["missed"]


def test_duplicate_planted_ids_are_counted_once():
    score, _ = score_truth(["L-0001", "L-0001", "L-0002"], CHAIN, EVENTS)
    assert score["planted"] == 2
    assert score["found"] == 2
    assert score["recall"] == 100


def test_false_links_and_missed_are_sorted():
    chain = [{"exhibits": [exhibit("L-0300"), exhibit("L-0100")]}]
    score, _ = score_truth(["L-0900", "L-0500"], chain, [])
    assert score["false_links"] == ["L-0100", "L-0300"]
    assert score["missed"] == ["L-0500", "L-0900"]


def test_linked_events_with_nothing_planted_give_zero_precision():
    chain = [{"exhibits": [exhibit("L-0001")]}]
    score, events = score_truth([], chain, EVENTS)
    assert score["precision"] == 0
    assert score["false_links"] == ["L-0001"]
    assert {e["id"]: e["truth"] for e in events}["L-0001"] == "false_link"


def test_percentages_are_exact_at_the_half_boundaries():
    planted = [f"L-{n:04d}" for n in range(1, 9)]
    chain = [{"exhibits": [exhibit(f"L-{n:04d}") for n in range(1, 4)]}]
    score, _ = score_truth(planted, chain, [])
    assert score["recall"] == 38
    assert score["precision"] == 100


def test_the_planted_list_is_not_changed():
    planted = ["L-0004", "L-0001"]
    score_truth(planted, CHAIN, EVENTS)
    assert planted == ["L-0004", "L-0001"]


def test_load_planted_reads_truth_json(tmp_path):
    (tmp_path / "truth.json").write_text(json.dumps({"planted": PLANTED}), encoding="utf-8")
    assert load_planted(tmp_path) == PLANTED
