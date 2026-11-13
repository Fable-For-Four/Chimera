"""Normal noise and lone oddities for the scenario night.

Normal events stay inside every baseline in history.json, so they match no scoring rule (PLAN 6.4).
Lone oddities each break exactly one rule, and share nothing with the attack, so they are scored but never linked.
"""

from datetime import timedelta

from generator.scenario import (
    MAIL_RELAY_IP, NIGHT_HOURS, SERVERS, SERVICE_ACCOUNT, WINDOW_END, WINDOW_START, event,
)

# 5,124 events in total: 12 planted + 25 oddities + this many normal ones.
NOISE_COUNT = 5087
WINDOW_SECONDS = int((WINDOW_END - WINDOW_START).total_seconds())

# How often each kind of normal event appears. The hosts are chosen so DC-01 and FIN-SRV-02
# stay under 5% of all events, or Link would treat them as hubs and the chain would break.
KINDS = {
    "health": 20,
    "cron": 4,
    "dns": 6,
    "mail": 22,
    "relay": 8,
    "vpn": 8,
    "logon": 10,
    "file": 12,
    "internal_conn": 10,
}
LOGON_SERVERS = ["MAIL-01", "HR-SRV-01", "HR-SRV-01", "DC-01"]
FILE_SERVERS = ["HR-SRV-01"] * 5 + ["FIN-SRV-02"]
CONN_TARGETS = ["MAIL-01", "HR-SRV-01", "BKP-01", "PRINT-02"]


def clock(ts):
    return ts.strftime("%H:%M:%S")


def random_time(rng):
    return clock(WINDOW_START + timedelta(seconds=rng.randrange(WINDOW_SECONDS)))


def night_workers(company):
    return [u for u in company["users"] if u["hours"] == NIGHT_HOURS]


def home_ips(company):
    # Each night worker connects from one fixed home address (198.18.0.0/15 is a reserved test range).
    return {u["name"]: f"198.18.0.{10 + i}" for i, u in enumerate(night_workers(company))}


def normal_events(rng, company):
    """NOISE_COUNT everyday events, spread evenly over 03:00 to 04:30."""
    workers = night_workers(company)
    homes = home_ips(company)
    machines = list(company["machines"])
    workstations = [m for m in machines if m.startswith("WS-") and m != "WS-PRIYA-014"]

    events = backup_job()
    kinds, weights = list(KINDS), list(KINDS.values())
    while len(events) < NOISE_COUNT:
        kind = rng.choices(kinds, weights)[0]
        t = random_time(rng)
        user = rng.choice(workers)
        name = user["name"]
        if kind == "health":
            m = rng.choice(machines)
            events.append(event(t, m, "HEALTH_OK", host=m))
        elif kind == "cron":
            m = rng.choice(SERVERS)
            events.append(event(t, m, "CRON", host=m, job=rng.choice(["logrotate", "tmp-clean", "print-clean"])))
        elif kind == "dns":
            events.append(event(t, "fw-edge", "DNS_QUERY", src=rng.choice(machines)))
        elif kind == "mail":
            action = rng.choice(["MAIL_RECV", "MAIL_SEND"])
            events.append(event(t, "MAIL-01", action, user=name, host="MAIL-01"))
        elif kind == "relay":
            action = rng.choice(["CONN_OPEN", "CONN_CLOSE"])
            extra = {"bytes_out": rng.randint(20_000, 5_000_000)} if action == "CONN_CLOSE" else {}
            events.append(event(t, "fw-edge", action, src="MAIL-01", dst=MAIL_RELAY_IP, **extra))
        elif kind == "vpn":
            events.append(event(t, "vpn-gw", "AUTH_OK", user=name, src=homes[name], geo="IN"))
        elif kind == "logon":
            host = user["workstation"] if user["workstation"] and rng.random() < 0.5 else rng.choice(LOGON_SERVERS)
            events.append(event(t, "dc", "LOGON", user=name, host=host, src=homes[name], type="network"))
        elif kind == "file":
            host = rng.choice(FILE_SERVERS)
            action = rng.choice(["SMB_SESSION", "FILE_READ"])
            extra = {"path": "/shared/ops", "files": rng.randint(1, 60)} if action == "FILE_READ" else {}
            events.append(event(t, "files", action, user=name, host=host, src=homes[name], **extra))
        elif kind == "internal_conn":
            action = rng.choice(["CONN_OPEN", "CONN_CLOSE"])
            extra = {"bytes_out": rng.randint(1_000, 2_000_000)} if action == "CONN_CLOSE" else {}
            events.append(event(t, "fw-edge", action, src=rng.choice(workstations), dst=rng.choice(CONN_TARGETS), **extra))
    return events


def backup_job():
    """The 03:20 backup verify. Only JOB_START and JOB_END, which the 'Wrong time' rule ignores."""
    return [
        event("03:20:00", "BKP-01", "JOB_START", user=SERVICE_ACCOUNT, host="BKP-01", src="BKP-01", job="backup-verify"),
        event("03:27:41", "BKP-01", "JOB_END", user=SERVICE_ACCOUNT, host="BKP-01", src="BKP-01", job="backup-verify"),
    ]


def lone_oddities(rng, company):
    """25 events, each breaking exactly one rule for something unrelated to the attack.

    Users who get an oddity that reaches 0.30 are all different, so no two oddities can link
    into a group spanning two stages, which would look like a second chain.
    """
    workers = night_workers(company)
    day_users = [u["name"] for u in company["users"] if u["hours"] != NIGHT_HOURS and u["name"] != "priya.s"]
    picked = rng.sample([u["name"] for u in workers], 10)
    with_ws = [u for u in workers if u["workstation"]]

    oddities = []
    # New country for this user (0.34), from five different night workers.
    for i, (name, geo) in enumerate(zip(picked[:5], ["SG", "AE", "GB", "US", "DE"])):
        oddities.append(event(random_time(rng), "vpn-gw", "AUTH_OK", user=name, src=f"203.0.113.{110 + i}", geo=geo))
    # Large read of files (0.30), from five other night workers, on HR-SRV-01.
    for name in picked[5:]:
        oddities.append(event(random_time(rng), "files", "FILE_READ", user=name, host="HR-SRV-01",
                              path="/hr/archive", files=rng.randint(500, 900)))
    # Outside the usual hours (0.28), day users signing in at night.
    for i, name in enumerate(rng.sample(day_users, 5)):
        oddities.append(event(random_time(rng), "vpn-gw", "AUTH_OK", user=name, src=f"203.0.113.{120 + i}", geo="IN"))
    # Lookup command for groups (0.25), on night workers' own machines.
    for _ in range(5):
        user = rng.choice(with_ws)
        oddities.append(event(random_time(rng), user["workstation"], "PROC_START", user=user["name"],
                              host=user["workstation"], cmd=rng.choice(["whoami", "nltest"])))
    # First outside connection (0.33), the printer calling home.
    for i in range(3):
        oddities.append(event(random_time(rng), "fw-edge", "CONN_OPEN", src="PRINT-02", dst=f"203.0.113.{200 + i}"))
    # Upload far above normal (0.30), the printer sending a big spool file to the backup server.
    for _ in range(2):
        oddities.append(event(random_time(rng), "fw-edge", "CONN_CLOSE", src="PRINT-02", dst="BKP-01",
                              bytes_out=rng.randint(150, 300) * 1024**2))
    return oddities
