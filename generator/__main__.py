"""python -m generator --seed 7 [--scenario dos]: writes the five files in data/.

The dos scenario writes to data_dos/ instead. Same seed, same files.
"""

import argparse
import json
import random
from datetime import timedelta
from pathlib import Path

from generator import noise, scenario

LATE_COUNT = 211  # plus the planted step 3 LOGON makes 212 late events

SCENARIOS = {
    "chain": scenario.attack_events,
    "dos": scenario.dos_events,
    "stopped": scenario.stopped_events,
    "gap": scenario.gap_events,
    "spray": scenario.spray_events,
    "late_work": scenario.late_work_events,
}


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def raw_line(e):
    parts = [e["ts"].strftime("%H:%M:%S"), e["source"], e["action"]]
    fields = {k: e[k] for k in ("user", "host", "src", "dst")}
    parts += [f"{k}={v}" for k, v in {**fields, **e["attrs"]}.items() if v is not None]
    return " ".join(parts)


def build(seed, scenario_name="chain"):
    rng = random.Random(seed)
    company = scenario.build_company(rng)
    normal = noise.normal_events(rng, company)
    for e in rng.sample(normal, LATE_COUNT):
        e["received_at"] = e["ts"] + timedelta(seconds=rng.randint(180, 720))
    attack = SCENARIOS[scenario_name]()
    attack_ids = {id(e) for e in attack}

    # Stable sort keeps generation order for ties, so the same seed gives the same file.
    events = sorted(
        normal + noise.lone_oddities(rng, company) + attack, key=lambda e: e["received_at"]
    )
    out, planted = [], []
    for i, e in enumerate(events, 1):
        eid = f"L-{i:04d}"
        if id(e) in attack_ids:
            planted.append(eid)
        out.append(
            {
                "id": eid,
                "ts": iso(e["ts"]),
                "received_at": iso(e["received_at"]),
                "source": e["source"],
                "action": e["action"],
                "user": e["user"],
                "host": e["host"],
                "src": e["src"],
                "dst": e["dst"],
                "attrs": e["attrs"],
                "raw": raw_line(e),
            }
        )
    return out, {
        "history.json": scenario.build_history(company),
        "access.json": scenario.build_access(company),
        "truth.json": {"planted": planted},
        "layout.json": scenario.LAYOUT,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--scenario", choices=list(SCENARIOS), default="chain")
    ap.add_argument("--out")
    args = ap.parse_args()
    events, files = build(args.seed, args.scenario)
    out = Path(args.out or ("data" if args.scenario == "chain" else f"data_{args.scenario}"))
    out.mkdir(exist_ok=True)
    (out / "events.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8", newline="\n"
    )
    for name, data in files.items():
        (out / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(events)} events and {len(files)} files to {out}/")


if __name__ == "__main__":
    main()
