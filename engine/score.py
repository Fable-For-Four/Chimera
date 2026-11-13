"""Stage 3: check each event against its baseline with 12 rules and combine the weights (PLAN 6.4)."""

from collections import defaultdict

from engine.sort import parse

LATE_REASON = "Log arrived late, time less certain"
LATE_FACTOR = 0.9
WEAK_SIGNAL = 0.30
LOOKUP_COMMANDS = ["net-group", "whoami", "nltest"]
JOB_ACTIONS = ("JOB_START", "JOB_END")
USER_FAIL_WINDOW = 300


def in_hours(hour, span):
    """Hours are whole UTC hours, inclusive. [22, 6] wraps past midnight."""
    first, last = span
    return first <= hour <= last if first <= last else hour >= first or hour <= last


# Each rule: (name, weight, test). The test gets the event `e`, profile `p`, hour `h` and the
# user's failed sign-ins in the last 5 minutes `fails`.
RULES = [
    ("New country for this user", 0.34, lambda e, p, h, fails:
        e["action"] in ("AUTH_OK", "AUTH_FAIL") and e["user"] in p.users
        and e["attrs"].get("geo") not in p.users[e["user"]]["countries"]),
    ("Outside the usual hours", 0.28, lambda e, p, h, fails:
        e["user"] in p.users and not in_hours(h, p.users[e["user"]]["hours"])),
    ("Failed tries, then success", 0.20, lambda e, p, h, fails:
        e["action"] == "AUTH_OK" and fails >= 2),
    ("First group change by this user", 0.36, lambda e, p, h, fails:
        e["action"] == "GROUP_ADD" and e["attrs"].get("actor") in p.users
        and "GROUP_ADD" not in p.users[e["attrs"]["actor"]]["actions"]),
    ("Service account gains admin rights", 0.38, lambda e, p, h, fails:
        e["action"] == "GROUP_ADD" and p.is_service(e["attrs"].get("member"))
        and e["attrs"].get("group") == "Domain-Admins"),
    ("Lookup command for groups", 0.25, lambda e, p, h, fails:
        e["action"] == "PROC_START" and e["attrs"].get("cmd") in LOOKUP_COMMANDS),
    ("Service account used by a person", 0.33, lambda e, p, h, fails:
        e["action"] == "LOGON" and e["attrs"].get("type") == "interactive" and p.is_service(e["user"])
        and "interactive" not in p.service_accounts[e["user"]]["logon_types"]),
    ("Wrong machine for this service account", 0.30, lambda e, p, h, fails:
        p.is_service(e["user"]) and e["src"] not in p.service_accounts[e["user"]]["sources"]),
    ("Wrong time for this service account", 0.27, lambda e, p, h, fails:
        p.is_service(e["user"]) and h not in p.service_accounts[e["user"]]["job_hours"]
        and e["action"] not in JOB_ACTIONS),
    ("Large read of files", 0.30, lambda e, p, h, fails:
        e["action"] == "FILE_READ" and e["attrs"].get("files", 0) >= 500),
    ("First outside connection", 0.33, lambda e, p, h, fails:
        e["action"] in ("CONN_OPEN", "CONN_CLOSE") and e["src"] in p.hosts and p.is_outside(e["dst"])
        and e["dst"] not in p.hosts[e["src"]]["outside_peers"]),
    ("Upload far above normal", 0.30, lambda e, p, h, fails:
        e["action"] == "CONN_CLOSE" and e["src"] in p.hosts
        and e["attrs"].get("bytes_out", 0) >= 20 * p.hosts[e["src"]]["daily_upload_mb"] * 1024**2),
]


def score_events(events, profile):
    """`events` must come from sort_events (time order, `late` set). Adds `score` and `reasons`."""
    failed = defaultdict(list)
    scored = []
    for e in events:
        ts = parse(e["ts"])
        if e["action"] == "AUTH_FAIL":
            failed[e["user"]].append(ts)
        recent = sum(0 <= (ts - t).total_seconds() <= USER_FAIL_WINDOW for t in failed[e["user"]])
        reasons = [{"name": name, "weight": w} for name, w, test in RULES if test(e, profile, ts.hour, recent)]
        score = 1.0
        for r in reasons:
            score *= 1 - r["weight"]
        score = 1 - score
        if e["late"] and reasons:
            score *= LATE_FACTOR
            reasons.append({"name": LATE_REASON, "weight": -0.10})  # shown only, already applied above
        scored.append({**e, "score": round(score, 2), "reasons": reasons})
    return scored, f"{sum(e['score'] >= WEAK_SIGNAL for e in scored)} weak signals"
