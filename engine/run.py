"""python -m engine.run: read data/, write out/, print the chain (PLAN 6.11)."""

import json
import os
import random
import sys
import time
from pathlib import Path

from engine.challenge import challenge
from engine.intake import build_intake
from engine.link import CANDIDATE, link
from engine.profile import Profile
from engine.report import write_report
from engine.score import score_events
from engine.sort import sort_events
from engine.stress import stress_runs
from engine.truth import load_planted, score_truth
from engine.verdict import verdict

NORMAL_SAMPLE = 40
SAMPLE_SEED = 7
DOES = {
    "Sort": "Put every event in true time order",
    "Profile": "Compare activity with 30 days of history",
    "Score": "Score weak signals against each baseline",
    "Link": "Join weak signals through shared entities",
    "Challenge": "Test innocent explanations",
    "Report": "Write claims backed by log citations",
}


def load_data(data_dir):
    data_dir = Path(data_dir)
    with open(data_dir / "events.jsonl", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    files = {}
    for name in ("history", "access", "layout"):
        with open(data_dir / f"{name}.json", encoding="utf-8") as f:
            files[name] = json.load(f)
    return events, files, load_planted(data_dir)


def case_events(arrival, scored, chain_events, planted, steps):
    """Weak signals, 40 seeded normal events and every planted event, in arrival order."""
    by_id = {e["id"]: e for e in scored}
    step_of = {e["id"]: e["step"] for e in chain_events}
    normal = sorted(e["id"] for e in scored if e["score"] < CANDIDATE)
    keep = {e["id"] for e in scored if e["score"] >= CANDIDATE} | set(planted)
    keep |= set(random.Random(SAMPLE_SEED).sample(normal, min(NORMAL_SAMPLE, len(normal))))
    _, marked = score_truth(planted, steps, [by_id[e["id"]] for e in arrival if e["id"] in keep])
    return [
        {
            "id": e["id"],
            "time": e["ts"][11:19],
            "source": e["source"],
            "raw": e["raw"],
            "score": e["score"],
            "reasons": [r["name"] for r in e["reasons"]],
            "step": step_of.get(e["id"]),
            "late": e["late"],
            "truth": e["truth"],
        }
        for e in marked
    ]


def timed(stages, name, fn, *args):
    start = time.perf_counter()
    result, line = fn(*args)
    stages.append(
        {
            "name": name,
            "does": DOES[name],
            "result": line,
            "seconds": round(time.perf_counter() - start, 2),
        }
    )
    return result


def make_profile(history):
    profile = Profile(history)
    return profile, profile.message()


def link_and_judge(scored, profile, files):
    """Verdict counts inside Link's time (PLAN 6.11)."""
    linked, line = link(scored, profile)
    return (linked, verdict(linked, scored, profile, files["access"], files["layout"])), line


def investigate(events, files, planted, level=0, deleted=0):
    """The whole pipeline on one event list. Returns one case.json dict."""
    stages = []
    ordered = timed(stages, "Sort", sort_events, events)
    profile = timed(stages, "Profile", make_profile, files["history"])
    scored = timed(stages, "Score", score_events, ordered, profile)

    linked, judged = timed(stages, "Link", link_and_judge, scored, profile, files)

    steps = linked["steps"]
    hypotheses = timed(
        stages,
        "Challenge",
        challenge,
        steps,
        linked["confidence"],
        set(files["history"]["service_accounts"]),
    )
    case_list = case_events(events, scored, linked["events"], planted, steps)
    written = timed(
        stages,
        "Report",
        write_report,
        linked,
        judged["verdict"]["blast_radius"]["reachable"],
        {e["id"] for e in case_list},
        set(files["history"]["service_accounts"]),
    )

    truth_score, _ = score_truth(planted, steps, scored)
    intake = build_intake(events, files["history"])
    return {
        "level": level,
        "deleted": deleted,
        "summary": intake["summary"],
        "stages": stages,
        "verdict": judged["verdict"],
        "chain": steps,
        "graph": judged["graph"],
        "volume": intake["volume"],
        "hypotheses": hypotheses,
        "events": case_list,
        "truth_score": truth_score,
        "report": written["report"],
        "limits": written["limits"],
        "actions": judged["actions"],
        "questions": written["questions"],
    }


def write_json(path, data):
    """Write to a temp file, then swap it in, so the API never reads half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temp, path)


def print_chain(case):
    v = case["verdict"]
    print(f"{v['label']} ({v['confidence']}%)")
    for s in case["chain"]:
        ids = " ".join(x["id"] for x in s["exhibits"]) or "inferred"
        print(f"  {s['step']}. {s['time']}  {s['stage']:<21} {s['confidence']:>3}%  {ids}")


def run(data_dir="data", out_dir="out"):
    out_dir = Path(out_dir)
    events, files, planted = load_data(data_dir)
    write_json(out_dir / "intake.json", build_intake(events, files["history"]))
    case = investigate(events, files, planted)
    for stressed in stress_runs(events, files, planted, case, investigate):
        write_json(out_dir / "stress" / f"{stressed['level']:02d}.json", stressed)
    write_json(out_dir / "case.json", case)  # last, so a new case.json means every file is ready
    return case


if __name__ == "__main__":
    start = time.perf_counter()
    print_chain(run(*sys.argv[1:3]))
    print(f"Done in {time.perf_counter() - start:.1f}s")
