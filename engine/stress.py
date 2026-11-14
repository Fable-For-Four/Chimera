"""Stress runs: delete and delay logs at 0 to 40 percent, then rerun the case (PLAN 6.10)."""

import random
from datetime import timedelta

from engine.sort import parse

LEVELS = [0, 5, 10, 15, 20, 25, 30, 35, 40]
DELAYED_SHARE = 0.20
MAX_DELAY_SECONDS = 600


def damage(events, level, seed):
    """Delete `level` percent, delay 20% of the rest by 0 to 10 minutes, reorder by arrival."""
    if level == 0:
        return list(events)
    rng = random.Random(seed + level)
    gone = set(rng.sample(range(len(events)), round(len(events) * level / 100)))
    kept = [e for i, e in enumerate(events) if i not in gone]
    for i in rng.sample(range(len(kept)), round(len(kept) * DELAYED_SHARE)):
        e = kept[i]
        late = parse(e["ts"]) + timedelta(seconds=rng.randint(0, MAX_DELAY_SECONDS))
        kept[i] = {**e, "received_at": late.strftime("%Y-%m-%dT%H:%M:%SZ")}
    kept.sort(key=lambda e: e["received_at"])  # stable, so ties keep file order
    return kept


def mark_missing(case, base, ts_all, kept_ids):
    """Add back level-0 exhibits that were deleted, as present false, to steps of the same stage."""
    base_steps = {s["stage"]: s for s in base["chain"]}
    for step in case["chain"]:
        if step["stage"] not in base_steps:
            continue
        have = {x["id"] for x in step["exhibits"]}
        lost = [
            {**x, "present": False}
            for x in base_steps[step["stage"]]["exhibits"]
            if x["id"] not in have and x["id"] not in kept_ids
        ]
        step["exhibits"] = sorted(step["exhibits"] + lost, key=lambda x: (ts_all[x["id"]], x["id"]))
    return case


def stress_runs(events, files, planted, base, investigate, seed=7):
    """One case per level. `base` is the level-0 case; `investigate` is engine.run.investigate."""
    ts_all = {e["id"]: e["ts"] for e in events}
    cases = []
    for level in LEVELS:
        if level == 0:
            cases.append(base)
            continue
        kept = damage(events, level, seed)
        case = investigate(kept, files, planted, level=level, deleted=len(events) - len(kept))
        cases.append(mark_missing(case, base, ts_all, {e["id"] for e in kept}))
    return cases
