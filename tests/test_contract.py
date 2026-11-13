import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    with (FIXTURES / name).open(encoding="utf-8") as fixture:
        return json.load(fixture)


def assert_keys(value, expected):
    assert set(value) == set(expected)


def assert_integer(value, minimum=0):
    assert type(value) is int
    assert value >= minimum


def assert_number(value, minimum=0, maximum=None):
    assert type(value) in (int, float)
    assert value >= minimum
    if maximum is not None:
        assert value <= maximum


def assert_string_list(value):
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)


def assert_summary(summary):
    assert_keys(summary, {"events", "sources", "late", "alerts_fired"})
    for value in summary.values():
        assert_integer(value)


def assert_volume(volume):
    assert isinstance(volume, list)
    for bucket in volume:
        assert_keys(bucket, {"start", "count"})
        assert isinstance(bucket["start"], str)
        assert_integer(bucket["count"])


def assert_intake_contract(intake):
    assert_keys(intake, {"summary", "alert_rules", "volume", "latest"})
    assert_summary(intake["summary"])
    assert_volume(intake["volume"])

    assert isinstance(intake["alert_rules"], list)
    for rule in intake["alert_rules"]:
        assert_keys(rule, {"name", "seen", "ratio", "fired"})
        assert isinstance(rule["name"], str)
        assert isinstance(rule["seen"], str)
        assert_number(rule["ratio"], 0, 1)
        assert type(rule["fired"]) is bool

    assert isinstance(intake["latest"], list)
    for event in intake["latest"]:
        assert_keys(event, {"id", "time", "source", "raw"})
        assert all(isinstance(value, str) for value in event.values())


def assert_stage(stage):
    assert_keys(stage, {"name", "does", "result", "seconds"})
    assert all(isinstance(stage[key], str) for key in ("name", "does", "result"))
    assert_number(stage["seconds"])


def assert_verdict(verdict):
    assert_keys(
        verdict,
        {
            "label",
            "confidence",
            "found",
            "headline",
            "entry_point",
            "blast_radius",
            "data_at_risk",
            "weakest_step",
        },
    )
    assert isinstance(verdict["label"], str)
    assert_number(verdict["confidence"], 0, 100)
    assert type(verdict["found"]) is bool
    assert isinstance(verdict["headline"], str)

    assert_keys(verdict["entry_point"], {"account", "event", "text"})
    assert all(isinstance(value, str) for value in verdict["entry_point"].values())

    assert_keys(verdict["blast_radius"], {"accounts", "touched", "reachable"})
    for value in verdict["blast_radius"].values():
        assert_string_list(value)

    assert_keys(verdict["data_at_risk"], {"files", "bytes_out"})
    assert_integer(verdict["data_at_risk"]["files"])
    assert_integer(verdict["data_at_risk"]["bytes_out"])
    assert_integer(verdict["weakest_step"], 1)


def assert_chain_step(step):
    assert_keys(
        step,
        {
            "step",
            "stage",
            "technique",
            "time",
            "minute",
            "from",
            "to",
            "what",
            "confidence",
            "inferred",
            "usual",
            "now",
            "signals",
            "exhibits",
        },
    )
    assert_integer(step["step"], 1)
    assert_integer(step["minute"])
    assert_number(step["confidence"], 0, 100)
    assert type(step["inferred"]) is bool
    for key in ("stage", "technique", "time", "from", "to", "what", "usual", "now"):
        assert isinstance(step[key], str)

    assert isinstance(step["signals"], list)
    for signal in step["signals"]:
        assert_keys(signal, {"name", "weight"})
        assert isinstance(signal["name"], str)
        assert_number(signal["weight"], -1, 1)

    assert isinstance(step["exhibits"], list)
    for exhibit in step["exhibits"]:
        assert_keys(exhibit, {"id", "raw", "late", "present"})
        assert isinstance(exhibit["id"], str)
        assert isinstance(exhibit["raw"], str)
        assert type(exhibit["late"]) is bool
        assert type(exhibit["present"]) is bool


def assert_graph(graph):
    assert_keys(graph, {"nodes", "edges"})
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)

    for node in graph["nodes"]:
        assert set(node) in (
            {"id", "type", "state", "x", "y"},
            {"id", "type", "state", "x", "y", "step"},
        )
        assert isinstance(node["id"], str)
        assert node["type"] in {"user", "machine", "outside"}
        assert node["state"] in {"hit", "reach", "normal"}
        assert_number(node["x"])
        assert_number(node["y"])
        if "step" in node:
            assert_integer(node["step"], 1)

    node_ids = {node["id"] for node in graph["nodes"]}
    for edge in graph["edges"]:
        assert_keys(edge, {"from", "to"})
        assert edge["from"] in node_ids
        assert edge["to"] in node_ids


def assert_hypothesis(hypothesis):
    assert_keys(hypothesis, {"name", "share", "fits", "breaks"})
    assert isinstance(hypothesis["name"], str)
    assert_number(hypothesis["share"], 0, 100)
    assert_string_list(hypothesis["fits"])
    assert_string_list(hypothesis["breaks"])


def assert_event(event):
    assert_keys(
        event,
        {"id", "time", "source", "raw", "score", "reasons", "step", "late", "truth"},
    )
    for key in ("id", "time", "source", "raw"):
        assert isinstance(event[key], str)
    assert_number(event["score"], 0, 1)
    assert_string_list(event["reasons"])
    assert event["step"] is None or type(event["step"]) is int
    assert type(event["late"]) is bool
    assert event["truth"] in {"found", "missed", "false_link", None}


def assert_truth_score(truth_score):
    assert_keys(
        truth_score,
        {"planted", "found", "linked", "recall", "precision", "missed", "false_links"},
    )
    for key in ("planted", "found", "linked", "recall", "precision"):
        assert_integer(truth_score[key])
    assert truth_score["recall"] <= 100
    assert truth_score["precision"] <= 100
    assert_string_list(truth_score["missed"])
    assert_string_list(truth_score["false_links"])


def assert_case_contract(case):
    assert_keys(
        case,
        {
            "level",
            "deleted",
            "summary",
            "stages",
            "verdict",
            "chain",
            "graph",
            "volume",
            "hypotheses",
            "events",
            "truth_score",
            "report",
            "limits",
            "actions",
            "questions",
        },
    )
    assert_integer(case["level"])
    assert_integer(case["deleted"])
    assert_summary(case["summary"])
    assert_volume(case["volume"])

    assert isinstance(case["stages"], list)
    for stage in case["stages"]:
        assert_stage(stage)

    assert_verdict(case["verdict"])
    assert isinstance(case["chain"], list)
    for step in case["chain"]:
        assert_chain_step(step)

    assert_graph(case["graph"])

    assert isinstance(case["hypotheses"], list)
    for hypothesis in case["hypotheses"]:
        assert_hypothesis(hypothesis)

    assert isinstance(case["events"], list)
    for event in case["events"]:
        assert_event(event)

    assert_truth_score(case["truth_score"])
    assert_string_list(case["limits"])

    assert isinstance(case["report"], list)
    for claim in case["report"]:
        assert_keys(claim, {"text", "cites", "step"})
        assert isinstance(claim["text"], str)
        assert_string_list(claim["cites"])
        assert_integer(claim["step"], 1)

    assert isinstance(case["actions"], list)
    for action in case["actions"]:
        assert_keys(action, {"id", "kind", "text"})
        assert all(isinstance(value, str) for value in action.values())

    assert isinstance(case["questions"], list)
    for question in case["questions"]:
        assert_keys(question, {"q", "a", "cites"})
        assert isinstance(question["q"], str)
        assert isinstance(question["a"], str)
        assert isinstance(question["cites"], list)
        for citation in question["cites"]:
            assert_keys(citation, {"id", "step"})
            assert isinstance(citation["id"], str)
            assert_integer(citation["step"], 1)


def test_intake_sample_matches_contract():
    intake = load_fixture("intake.sample.json")
    assert_intake_contract(intake)
    assert len(intake["alert_rules"]) == 4
    assert len(intake["latest"]) == 8
    assert intake["summary"]["alerts_fired"] == 0
    assert not any(rule["fired"] for rule in intake["alert_rules"])


def test_case_sample_matches_contract():
    case = load_fixture("case.sample.json")
    assert_case_contract(case)
    assert [stage["name"] for stage in case["stages"]] == [
        "Sort",
        "Profile",
        "Score",
        "Link",
        "Challenge",
        "Report",
    ]
    assert [step["step"] for step in case["chain"]] == [1, 2, 3, 4, 5]
    assert sum(hypothesis["share"] for hypothesis in case["hypotheses"]) == 100


def test_case_sample_references_existing_events():
    case = load_fixture("case.sample.json")
    event_ids = {event["id"] for event in case["events"]}

    for step in case["chain"]:
        assert {exhibit["id"] for exhibit in step["exhibits"]} <= event_ids
    for claim in case["report"]:
        assert set(claim["cites"]) <= event_ids
    for question in case["questions"]:
        assert {citation["id"] for citation in question["cites"]} <= event_ids


def test_case_sample_identifiers_are_unique():
    case = load_fixture("case.sample.json")
    event_ids = [event["id"] for event in case["events"]]
    action_ids = [action["id"] for action in case["actions"]]
    node_ids = [node["id"] for node in case["graph"]["nodes"]]

    assert len(event_ids) == len(set(event_ids))
    assert len(action_ids) == len(set(action_ids))
    assert len(node_ids) == len(set(node_ids))


def test_case_sample_truth_score_is_consistent():
    case = load_fixture("case.sample.json")
    truth_score = case["truth_score"]
    found = [event for event in case["events"] if event["truth"] == "found"]
    missed = [event["id"] for event in case["events"] if event["truth"] == "missed"]
    false_links = [event["id"] for event in case["events"] if event["truth"] == "false_link"]

    assert truth_score["planted"] == truth_score["found"] + len(truth_score["missed"])
    assert truth_score["found"] == len(found)
    assert truth_score["missed"] == missed
    assert truth_score["false_links"] == false_links
