"""Stage 4: join weak signals that share an entity into one chain of attack steps (PLAN 6.5)."""

from collections import Counter

import networkx as nx

from engine.sort import parse

CANDIDATE = 0.30
HUB_SHARE = 0.05
JOIN_SECONDS = 45 * 60
STEP_CAP = 0.97

# stage, actions, technique, from field, to field
STAGES = [
    ("Initial access", ("AUTH_FAIL", "AUTH_OK"), "T1078 Valid Accounts", "src", "user"),
    (
        "Privilege escalation",
        ("PROC_START", "GROUP_ADD"),
        "T1098.007 Additional Local or Domain Groups",
        "actor",
        "member",
    ),
    ("Lateral movement", ("LOGON", "TICKET_REQ"), "T1021 Remote Services", "user", "host"),
    (
        "Collection",
        ("SMB_SESSION", "FILE_READ"),
        "T1039 Data from Network Shared Drive",
        "user",
        "host",
    ),
    (
        "Exfiltration",
        ("CONN_OPEN", "CONN_CLOSE", "DNS_QUERY"),
        "T1048.002 Exfiltration Over Asymmetric Encrypted Non-C2 Protocol",
        "src",
        "dst",
    ),
]
STAGE_OF = {action: i for i, (_, actions, *_) in enumerate(STAGES) for action in actions}
COUNTRIES = {
    "IN": "India",
    "RO": "Romania",
    "US": "United States",
    "GB": "United Kingdom",
    "SG": "Singapore",
    "AE": "United Arab Emirates",
    "DE": "Germany",
    "KP": "North Korea",
    "IR": "Iran",
}


def entities(e):
    values = [
        e["user"],
        e["host"],
        e["src"],
        e["dst"],
        e["attrs"].get("actor"),
        e["attrs"].get("member"),
    ]
    return list(dict.fromkeys(v for v in values if v))


def field(e, name):
    """from/to value of an event. PROC_START has no actor or member: use user and host."""
    value = e["attrs"].get(name) if name in ("actor", "member") else e[name]
    fallback = {"actor": "user", "member": "host"}.get(name)
    return value or (e[fallback] if fallback else None) or ""


def find_chain(scored):
    """The joined group with the highest total score, or [] (PLAN 6.5 steps 1 to 5)."""
    counts = Counter(x for e in scored for x in entities(e))
    hubs = {x for x, n in counts.items() if n > HUB_SHARE * len(scored)}
    cands = [e for e in scored if e["score"] >= CANDIDATE and e["action"] in STAGE_OF]
    g = nx.Graph()
    g.add_nodes_from(range(len(cands)))
    for i, a in enumerate(cands):  # ponytail: O(n^2) over candidates, fine for a few dozen
        ents = set(entities(a)) - hubs
        for j in range(i + 1, len(cands)):
            b = cands[j]
            if (
                ents & set(entities(b))
                and abs((parse(a["ts"]) - parse(b["ts"])).total_seconds()) <= JOIN_SECONDS
            ):
                g.add_edge(i, j)
    groups = [[cands[i] for i in sorted(c)] for c in nx.connected_components(g)]
    groups = [
        grp for grp in groups if len(grp) >= 3 and len({STAGE_OF[e["action"]] for e in grp}) >= 2
    ]
    if not groups:
        return []
    best = max(groups, key=lambda grp: (sum(e["score"] for e in grp), [e["id"] for e in grp]))
    return sorted(best, key=lambda e: (e["ts"], e["id"]))


def combine(scores):
    rest = 1.0
    for s in scores:
        rest *= 1 - s
    return round(min(1 - rest, STEP_CAP) * 100)


def hours_text(span):
    return f"{span[0]:02}:00 to {span[1]:02}:00"


def size_text(n):
    return f"{n / 1024**3:.1f} GB" if n >= 1024**3 else f"{n / 1024**2:.0f} MB"


def describe(stage, e, profile, time):
    """what, usual, now: one short line each, from the step's top event."""
    a = e["attrs"]
    if stage == 0:
        user, base = e["user"], profile.users.get(e["user"])
        kind = "VPN sign-in" if e["action"] == "AUTH_OK" else "Failed VPN sign-in"
        new = base and a.get("geo") not in base["countries"]
        what = (
            f"{kind} to {user} from a new country"
            if new
            else f"{kind} to {user} at an unusual hour"
        )
        usual = (
            ", ".join(COUNTRIES.get(c, c) for c in base["countries"])
            + ", "
            + hours_text(base["hours"])
            if base
            else "No history for this account"
        )
        return what, usual, f"{COUNTRIES.get(a.get('geo'), a.get('geo') or 'unknown')}, {time}"
    if stage == 1:
        if e["action"] == "GROUP_ADD":
            group = a.get("group", "").replace("-", " ")
            return (
                f"{a.get('actor')} added {a.get('member')} to {group}",
                f"{a.get('actor')} has never changed an admin group",
                f"{a.get('member')} added to {group} at {time}",
            )
        return (
            f"{e['user']} ran {a.get('cmd')} on {e['host']}",
            f"{e['user']} does not run admin lookups",
            f"{a.get('cmd')} at {time}",
        )
    svc = profile.service_accounts.get(e["user"])
    if stage in (2, 3):
        usual = (
            f"{svc['logon_types'][0].capitalize()} jobs from {', '.join(svc['sources'])}"
            f" at {svc['job_hours'][0]:02}:00"
            if svc
            else f"Uses {', '.join(profile.users.get(e['user'], {}).get('hosts', [])) or 'nothing known'}"
        )
    if stage == 2:
        if e["action"] == "LOGON":
            kind = a.get("type", "logon")
            return (
                f"{e['user']} was used {kind} on {e['host']}"
                if kind != "interactive"
                else f"{e['user']} was used interactively on {e['host']}",
                usual,
                f"{kind.capitalize()} use from {e['src']} at {time}",
            )
        return (
            f"{e['user']} asked for a ticket to {a.get('service')}",
            usual,
            f"Ticket asked from {e['src']} at {time}",
        )
    if stage == 3:
        if e["action"] == "FILE_READ":
            n = a.get("files", 0)
            return (
                f"{e['user']} read {n:,} files from {e['host']}",
                usual,
                f"{n:,} files read from {e['src']}",
            )
        return (
            f"{e['user']} opened a share on {e['host']}",
            usual,
            f"Share opened from {e['src']} at {time}",
        )
    host = profile.hosts.get(e["src"], {})
    peers = host.get("outside_peers")
    usual = f"{host.get('daily_upload_mb', 0)} MB per day and " + (
        f"outside peers {', '.join(peers)}" if peers else "no outside peers"
    )
    if e["action"] == "CONN_CLOSE":
        size = size_text(a.get("bytes_out", 0))
        return (
            f"{e['src']} sent {size} to a new outside address",
            usual,
            f"{size} sent to {e['dst']}",
        )
    return (
        f"{e['src']} reached a new outside address",
        usual,
        f"Connection to {e['dst'] or 'unknown'} at {time}",
    )


def build_steps(chain, profile, start):
    """PLAN 6.5 steps 6 to 9. `start` is the window start, for `minute`."""
    by_stage = {}
    for e in chain:
        by_stage.setdefault(STAGE_OF[e["action"]], []).append(e)
    steps = []
    for i in range(min(by_stage), max(by_stage) + 1):
        name, _, technique, src_field, dst_field = STAGES[i]
        events = by_stage.get(i)
        if not events:
            steps.append({"stage": name, "technique": technique, "inferred": True, "index": i})
            continue
        top = max(events, key=lambda e: e["score"])
        ts = parse(top["ts"])
        time = ts.strftime("%H:%M")
        what, usual, now = describe(i, top, profile, time)
        signals = {}
        for e in events:
            for r in e["reasons"]:
                signals.setdefault(r["name"], r)
        steps.append(
            {
                "stage": name,
                "technique": technique,
                "time": time,
                "minute": int((ts - start).total_seconds() // 60),
                "from": field(top, src_field),
                "to": field(top, dst_field),
                "what": what,
                "confidence": combine(e["score"] for e in events),
                "inferred": False,
                "usual": usual,
                "now": now,
                "signals": sorted(signals.values(), key=lambda r: -r["weight"]),
                "exhibits": [
                    {"id": e["id"], "raw": e["raw"], "late": e["late"], "present": True}
                    for e in events
                ],
            }
        )
    for n, s in enumerate(steps):
        if s.pop("index", None) is not None:  # inferred: bridge the steps either side
            before, after = steps[n - 1], steps[n + 1]
            s.update(
                {
                    "time": before["time"],
                    "minute": before["minute"],
                    "from": before["to"],
                    "to": after["from"],
                    "what": f"The logs do not show {s['stage'].lower()}, but the steps around need it",
                    "confidence": round(min(before["confidence"], after["confidence"]) / 2),
                    "usual": "",
                    "now": "",
                    "signals": [],
                    "exhibits": [],
                }
            )
    ordered = []
    for n, s in enumerate(steps, 1):
        ordered.append(
            {
                "step": n,
                **{
                    k: s[k]
                    for k in (
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
                    )
                },
            }
        )
    return ordered


def link(scored, profile):
    """Returns ({steps, confidence, events}, result line). `events` carry their step number."""
    chain = find_chain(scored)
    if not chain:
        return {"steps": [], "confidence": 0, "events": []}, "No chain found"
    start = min(parse(e["ts"]) for e in scored).replace(second=0)
    steps = build_steps(chain, profile, start)
    real = [s for s in steps if not s["inferred"]]
    mean = sum(s["confidence"] for s in steps) / len(steps)
    confidence = round(mean * (0.6 + 0.08 * len(real)))
    step_of = {x["id"]: s["step"] for s in real for x in s["exhibits"]}
    events = [{**e, "step": step_of[e["id"]]} for e in chain]
    return (
        {"steps": steps, "confidence": confidence, "events": events},
        f"1 chain, {len(steps)} steps, {len(chain)} events",
    )
