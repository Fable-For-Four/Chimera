ATTACK = "Outside attacker with a stolen password"
OWNER = "The account owner working late while travelling"
BACKUP = "A backup job set up wrongly"

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def number(n):
    return NUMBER_WORDS.get(n, str(n))


def explained_stages(name, chain, service_accounts):
    if name == OWNER:
        return {"Initial access"}
    for step in chain:
        if step.get("inferred"):
            continue
        if step["stage"] == "Collection" and step["from"] in service_accounts:
            return {"Collection"}
    return set()


def split_rest(rest, weights):
    total = sum(weights)
    exact = [rest * w / total for w in weights] if total else [rest / len(weights)] * len(weights)
    shares = [int(x) for x in exact]
    leftover = rest - sum(shares)
    order = sorted(range(len(exact)), key=lambda i: (-(exact[i] - shares[i]), i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares


def phrases(chain, stages):
    seen = []
    for step in chain:
        if step["stage"] not in seen:
            seen.append(step["stage"])
    fits = [f"Explains the {s.lower()}" for s in seen if s in stages]
    breaks = [f"Cannot explain the {s.lower()}" for s in seen if s not in stages]
    return fits, breaks


def challenge(chain, confidence, service_accounts):
    if not chain:
        return [], "No chain to challenge"
    attack_share = max(0, min(100, int(confidence + 0.5)))
    names = [OWNER, BACKUP]
    explains = [explained_stages(name, chain, service_accounts) for name in names]
    weights = [
        sum(step["confidence"] for step in chain if step["stage"] in stages) for stages in explains
    ]
    shares = split_rest(100 - attack_share, weights)
    fits = [f"All {number(len(chain))} steps, in order"]
    inferred = sum(1 for step in chain if step.get("inferred"))
    if inferred:
        fits.append(f"{number(inferred).capitalize()} of them inferred, not seen in the logs")
    attack = {"name": ATTACK, "share": attack_share, "fits": fits, "breaks": []}
    hypotheses = [attack]
    for name, stages, share in zip(names, explains, shares, strict=True):
        fits, breaks = phrases(chain, stages)
        hypotheses.append({"name": name, "share": share, "fits": fits, "breaks": breaks})
    return hypotheses, result_line(hypotheses)


def result_line(hypotheses):
    attack, *others = hypotheses
    stronger = [h["name"] for h in others if h["share"] >= attack["share"]]
    if not stronger:
        return f"{len(others)} tested, both weaker"
    if len(stronger) == len(others):
        return f"{len(others)} tested, neither is weaker"
    return f"{len(others)} tested, {stronger[0].lower()} is not weaker"
