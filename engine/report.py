"""Stage 6: a sentence per step, the limits and three answers, all citing log IDs (PLAN 6.8)."""

from engine.challenge import number
from engine.link import COUNTRIES, entities, size_text


def sentence(stage, e, fails):
    """One claim from the step's highest-scoring event."""
    a, t = e["attrs"], e["ts"][11:16]
    if stage == "Initial access":
        place = COUNTRIES.get(a.get("geo"), a.get("geo") or "an unknown place")
        if e["action"] == "AUTH_FAIL":
            return f"At {t} someone tried to sign in as {e['user']} from {place}."
        tries = f" after {number(fails)} failed {'try' if fails == 1 else 'tries'}" if fails else ""
        return f"At {t} someone signed in as {e['user']} from {place}{tries}."
    if stage == "Privilege escalation":
        if e["action"] == "GROUP_ADD":
            group = a.get("group", "").replace("-", " ")
            return f"At {t} {a.get('actor')} added {a.get('member')} to {group}."
        return f"At {t} {e['user']} ran {a.get('cmd')} on {e['host']}."
    if stage == "Lateral movement":
        if e["action"] == "LOGON":
            how = (
                "interactively"
                if a.get("type") == "interactive"
                else f"for a {a.get('type')} logon"
            )
            return f"At {t} {e['user']} was used {how} on {e['host']} from {e['src']}."
        return f"At {t} {e['user']} asked for a ticket to {a.get('service')} from {e['src']}."
    if stage == "Collection":
        if e["action"] == "FILE_READ":
            return f"At {t} {e['user']} read {a.get('files', 0):,} files from {e['host']}."
        return f"At {t} {e['user']} opened a share on {e['host']} from {e['src']}."
    if e["action"] == "CONN_CLOSE":
        return (
            f"At {t} {e['src']} finished sending {size_text(a.get('bytes_out', 0))} to {e['dst']}."
        )
    return f"At {t} {e['src']} opened a connection to {e['dst']}."


def claims(steps, chain):
    out = []
    for s in steps:
        if s["inferred"]:
            stage = s["stage"].lower()
            text = f"The logs do not show {stage}, but the steps before and after need it."
            out.append({"text": text, "cites": [], "step": s["step"]})
            continue
        events = [e for e in chain if e["step"] == s["step"]]
        top = max(events, key=lambda e: e["score"])
        fails = sum(e["action"] == "AUTH_FAIL" for e in events)
        out.append(
            {"text": sentence(s["stage"], top, fails), "cites": [top["id"]], "step": s["step"]}
        )
    return out


def limits(steps, reachable):
    stages = {s["stage"] for s in steps if not s["inferred"]}
    out = [
        f"How {s['stage'].lower()} happened, which the logs do not show."
        for s in steps
        if s["inferred"]
    ]
    out += [f"Whether {m} was touched." for m in reachable]
    if "Collection" in stages:
        out.append("Whether the files were opened or only copied.")
    if "Initial access" in stages:
        out.append("How the password was obtained.")
    return out


def cite(claim_list):
    return [{"id": i, "step": c["step"]} for c in claim_list for i in c["cites"]]


def questions(steps, chain, report, limit_lines, service_accounts):
    real = [c for c in report if c["cites"]]
    if not real:
        return []
    accounts = [x for s in steps for x in (s["from"], s["to"])]
    flagged = next((a for a in accounts if a in service_accounts), steps[0]["to"])
    involved = {e["step"] for e in chain if flagged in entities(e)}
    about = [c for c in real if c["step"] in involved] or real[:1]
    out = [
        {
            "q": f"Why is {flagged} flagged?",
            "a": " ".join(c["text"] for c in about),
            "cites": cite(about),
        }
    ]

    first = real[0]
    rest = [s["stage"].lower() for s in steps[1:] if not s["inferred"]]
    if steps[0]["stage"] == "Initial access" and rest:
        a = (
            "Working late could explain the first sign-in, but not the "
            + (", ".join(rest[:-1]) + " and " + rest[-1] if len(rest) > 1 else rest[0])
            + "."
        )
        out.append({"q": "Could this be the account owner?", "a": a, "cites": cite(real)})
    else:
        first_stage = steps[0]["stage"].lower()
        a = f"The logs show no ordinary sign-in by the owner. The chain starts with {first_stage}."
        out.append({"q": "Could this be the account owner?", "a": a, "cites": cite([first])})

    if limit_lines:
        parts = [line[0].lower() + line[1:].rstrip(".") for line in limit_lines]
        backing = [first] + [
            c for c in real if c is not first and steps[c["step"] - 1]["stage"] == "Collection"
        ]
        out.append(
            {
                "q": "What can the logs not prove?",
                "a": "They cannot prove " + "; ".join(parts) + ".",
                "cites": cite(backing),
            }
        )
    return out


def write_report(linked, reachable, event_ids, service_accounts):
    """Returns ({report, limits, questions}, result line). Drops claims citing unknown IDs."""
    steps, chain = linked["steps"], linked["events"]
    report = [c for c in claims(steps, chain) if set(c["cites"]) <= event_ids]
    limit_lines = limits(steps, reachable)
    qs = [
        q
        for q in questions(steps, chain, report, limit_lines, service_accounts)
        if {c["id"] for c in q["cites"]} <= event_ids
    ]
    citations = sum(len(c["cites"]) for c in report)
    return (
        {"report": report, "limits": limit_lines, "questions": qs},
        f"{len(report)} claims, {citations} citations",
    )
