import json
from pathlib import Path


def load_planted(data_dir):
    data = json.loads((Path(data_dir) / "truth.json").read_text(encoding="utf-8"))
    return data["planted"]


def chain_event_ids(chain):
    ids = set()
    for step in chain:
        for exhibit in step.get("exhibits", []):
            if exhibit.get("present", True):
                ids.add(exhibit["id"])
    return ids


def percent(part, whole):
    return (part * 100 + whole // 2) // whole if whole else 0


def label(event_id, planted, linked):
    if event_id in planted:
        return "found" if event_id in linked else "missed"
    return "false_link" if event_id in linked else None


def score_truth(planted, chain, events):
    planted = set(planted)
    linked = chain_event_ids(chain)
    found = planted & linked
    truth_score = {
        "planted": len(planted),
        "found": len(found),
        "linked": len(linked),
        "recall": percent(len(found), len(planted)),
        "precision": percent(len(found), len(linked)),
        "missed": sorted(planted - linked),
        "false_links": sorted(linked - planted),
    }
    marked = [{**event, "truth": label(event["id"], planted, linked)} for event in events]
    return truth_score, marked
