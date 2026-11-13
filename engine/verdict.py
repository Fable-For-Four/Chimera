"""Verdict: label, entry point, blast radius, data at risk, graph and actions (PLAN 6.6)."""

from collections import Counter

from engine.link import entities
from engine.sort import parse

WIDTH, HEIGHT = 860, 480
MAX_NORMAL = 6

NO_CHAIN = {
    "label": "No chain found",
    "confidence": 0,
    "found": False,
    "headline": "No linked chain of events was found in these logs.",
    "entry_point": {"account": "", "event": "", "text": ""},
    "blast_radius": {"accounts": [], "touched": [], "reachable": []},
    "data_at_risk": {"files": 0, "bytes_out": 0},
    "weakest_step": 1,  # the contract wants 1 or more; the UI ignores it when found is false
}


def label(confidence):
    if confidence >= 70:
        return "Likely attack"
    if confidence >= 50:
        return "Probable attack"
    return "Possible attack"


def node_type(name, profile):
    if name in profile.users or profile.is_service(name):
        return "user"
    if name in profile.hosts:
        return "machine"
    try:
        return "outside" if profile.is_outside(name) else "machine"
    except ValueError:
        return "user"


def headline(steps, chain):
    """Minutes are counted from step 1's main event, the same time shown on step 1."""
    first = steps[0]
    after = (
        "after the first sign-in" if first["stage"] == "Initial access" else "after the first step"
    )
    start = parse(
        max((e for e in chain if e["step"] == first["step"]), key=lambda e: e["score"])["ts"]
    )
    parts = []
    priv = next(
        (s for s in steps if s["stage"] == "Privilege escalation" and not s["inferred"]), None
    )
    if priv and priv is not first:
        parts.append(
            f"The attacker gained admin rights {priv['minute'] - first['minute']} minutes {after}."
        )
    exfil = next((s for s in steps if s["stage"] == "Exfiltration" and not s["inferred"]), None)
    if exfil and exfil is not first:
        leave = min(parse(e["ts"]) for e in chain if e["step"] == exfil["step"])
        parts.append(
            f"Data started leaving {int((leave - start).total_seconds() // 60)} minutes {after}."
        )
    span = steps[-1]["minute"] - first["minute"]
    return " ".join(parts) or f"{len(steps)} linked steps over {span} minutes."


def graph(steps, chain, scored, profile, accounts, reachable, access, layout):
    step_of = {}
    for e in chain:
        for x in entities(e):
            step_of.setdefault(x, e["step"])
    for s in steps:  # inferred steps reach their nodes through from/to
        for x in (s["from"], s["to"]):
            step_of.setdefault(x, s["step"])
    chain_ids = {e["id"] for e in chain}
    shown = set(step_of) | set(reachable)
    near = Counter(
        x
        for e in scored
        if e["id"] not in chain_ids and shown & set(entities(e))
        for x in entities(e)
        if x not in shown
    )
    # Names with a planned position in layout.json go first, so the graph stays tidy.
    normal = [
        x for x, _ in sorted(near.items(), key=lambda kv: (kv[0] not in layout, -kv[1], kv[0]))
    ][:MAX_NORMAL]

    names = list(step_of) + [r for r in reachable if r not in step_of] + normal
    missing = [n for n in names if n not in layout]
    nodes = []
    for n in names:
        x, y = layout.get(n) or (
            round((missing.index(n) + 1) * WIDTH / (len(missing) + 1)),
            HEIGHT - 20,
        )
        node = {
            "id": n,
            "type": node_type(n, profile),
            "state": "hit" if n in step_of else "reach" if n in reachable else "normal",
            "x": x,
            "y": y,
        }
        if n in step_of:
            node["step"] = step_of[n]
        nodes.append(node)

    # Step edges first to keep the attack's direction,
    # then account to reachable, then shared events.
    pairs = [(s["from"], s["to"]) for s in steps]
    pairs += [(a, h) for a in accounts for h in access.get(a, []) if h in reachable]
    for e in scored:
        ents = [x for x in entities(e) if x in step_of or x in reachable or x in normal]
        pairs += [(a, b) for i, a in enumerate(ents) for b in ents[i + 1 :]]
    seen, edges = set(), []
    for a, b in pairs:
        if a and b and a != b and frozenset((a, b)) not in seen:
            seen.add(frozenset((a, b)))
            edges.append({"from": a, "to": b})
    return {"nodes": nodes, "edges": edges}


def actions(accounts, chain, reachable, profile):
    out = [
        {
            "id": f"reset-{u}",
            "kind": "Contain",
            "text": f"Reset the {u} password and end their sessions",
        }
        for u in accounts
        if u in profile.users
    ]
    for e in chain:
        member = e["attrs"].get("member")
        if (
            e["action"] == "GROUP_ADD"
            and profile.is_service(member)
            and e["attrs"].get("group") == "Domain-Admins"
        ):
            out.append(
                {
                    "id": f"demote-{member}",
                    "kind": "Contain",
                    "text": f"Remove {member} from Domain Admins",
                }
            )
    for e in chain:
        if (
            e["action"] in ("CONN_OPEN", "CONN_CLOSE")
            and e["dst"]
            and node_type(e["dst"], profile) == "outside"
        ):
            out.append(
                {
                    "id": f"block-{e['dst']}",
                    "kind": "Contain",
                    "text": f"Block {e['dst']} and isolate {e['src']}",
                }
            )
    out += [
        {"id": f"review-{h}", "kind": "Check", "text": f"Review {h}, which the account could reach"}
        for h in reachable
    ]
    return list({a["id"]: a for a in out}.values())


def verdict(linked, scored, profile, access, layout):
    """Returns {verdict, graph, actions} for case.json."""
    steps, chain = linked["steps"], linked["events"]
    if not steps:
        return {"verdict": dict(NO_CHAIN), "graph": {"nodes": [], "edges": []}, "actions": []}

    accounts = list(
        dict.fromkeys(
            x
            for s in steps
            for x in (s["from"], s["to"])
            if x in profile.users or profile.is_service(x)
        )
    )
    touched = list(dict.fromkeys(x for e in chain for x in entities(e) if x in profile.hosts))
    reachable = list(
        dict.fromkeys(h for a in accounts for h in access.get(a, []) if h not in touched)
    )
    first = steps[0]
    top = max(
        (e for e in chain if e["step"] == first["step"]), key=lambda e: e["score"], default=None
    )
    weakest = min(steps, key=lambda s: s["confidence"])

    return {
        "verdict": {
            "label": label(linked["confidence"]),
            "confidence": linked["confidence"],
            "found": True,
            "headline": headline(steps, chain),
            "entry_point": {
                "account": first["to"],
                "event": top["id"] if top else "",
                "text": first["what"],
            },
            "blast_radius": {"accounts": accounts, "touched": touched, "reachable": reachable},
            "data_at_risk": {
                "files": sum(
                    e["attrs"].get("files", 0) for e in chain if e["action"] == "FILE_READ"
                ),
                "bytes_out": sum(
                    e["attrs"].get("bytes_out", 0) for e in chain if e["action"] == "CONN_CLOSE"
                ),
            },
            "weakest_step": weakest["step"],
        },
        "graph": graph(steps, chain, scored, profile, accounts, reachable, access, layout),
        "actions": actions(accounts, chain, reachable, profile),
    }
