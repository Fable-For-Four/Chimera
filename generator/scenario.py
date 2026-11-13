"""The fixed part of the fake company Acme.

People, machines, baselines, graph layout and the planted attack. Normal noise is made in
noise.py. IDs and the raw log text are added in __main__.py when the files are written.
"""

from datetime import UTC, datetime, timedelta

WINDOW_START = datetime(2026, 11, 14, 3, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 11, 14, 4, 30, tzinfo=UTC)

DAY_HOURS = [9, 19]
NIGHT_HOURS = [22, 6]

NAMED_USERS = ["priya.s", "arjun.m", "neha.k"]
FIRST_NAMES = [
    "aarav",
    "aditi",
    "akash",
    "ananya",
    "anil",
    "deepa",
    "divya",
    "farah",
    "gaurav",
    "isha",
    "karan",
    "kavya",
    "lakshmi",
    "manoj",
    "meera",
    "nikhil",
    "pooja",
    "rahul",
    "ravi",
    "riya",
    "rohan",
    "sanjay",
    "sneha",
    "suresh",
    "tanvi",
    "uday",
    "varun",
    "vikram",
    "yash",
    "zoya",
]

SERVERS = ["MAIL-01", "DC-01", "FIN-SRV-02", "HR-SRV-01", "BKP-01", "PRINT-02"]
SERVICE_ACCOUNT = "svc-backup"
SERVICE_ACCOUNT_REACH = ["BKP-01", "FIN-SRV-02", "HR-SRV-01", "DC-01"]

ATTACKER_IP = "203.0.113.47"
EXFIL_IP = "198.51.100.23"
MAIL_RELAY_IP = "192.0.2.25"
DOS_IP = "203.0.113.77"

DAY_ACTIONS = ["AUTH_OK", "MAIL_RECV", "MAIL_SEND"]
NIGHT_ACTIONS = ["AUTH_OK", "LOGON", "MAIL_RECV", "MAIL_SEND", "SMB_SESSION", "FILE_READ"]

UPLOAD_MB = {
    "MAIL-01": 400,
    "DC-01": 30,
    "FIN-SRV-02": 50,
    "HR-SRV-01": 40,
    "BKP-01": 200,
    "PRINT-02": 5,
}
WORKSTATION_UPLOAD_MB = 20

# Positions on the 860 x 480 graph canvas (PLAN section 5). The attack path reads left to right.
LAYOUT = {
    "203.0.113.47": [70, 240],
    "priya.s": [190, 240],
    "WS-PRIYA-014": [310, 240],
    "DC-01": [430, 160],
    "svc-backup": [430, 320],
    "FIN-SRV-02": [570, 240],
    "198.51.100.23": [760, 240],
    "HR-SRV-01": [570, 400],
    "MAIL-01": [190, 80],
    "arjun.m": [330, 80],
    "PRINT-02": [690, 80],
    "BKP-01": [310, 400],
    "neha.k": [800, 400],
    "WS-NEHA-022": [690, 400],
}


def build_company(rng):
    """50 users (12 night workers), 20 machines with inside addresses, and one service account."""
    taken = set(NAMED_USERS)
    candidates = [
        f"{first}.{letter}" for first in FIRST_NAMES for letter in "abcdefghijklmnopqrstuvwxyz"
    ]
    generated = rng.sample([c for c in candidates if c not in taken], 47)

    night = {"arjun.m", "neha.k", *rng.sample(generated, 10)}

    workstations = {"priya.s": "WS-PRIYA-014", "neha.k": "WS-NEHA-022"}
    numbers = rng.sample([n for n in range(1, 1000) if n not in (14, 22)], 12)
    for name, number in zip(["arjun.m", *rng.sample(generated, 11)], numbers, strict=False):
        workstations[name] = f"WS-{name.split('.')[0].upper()}-{number:03d}"

    users = [
        {
            "name": name,
            "hours": NIGHT_HOURS if name in night else DAY_HOURS,
            "workstation": workstations.get(name),
        }
        for name in NAMED_USERS + generated
    ]

    machines = {name: f"10.0.1.{10 + i}" for i, name in enumerate(SERVERS)}
    for i, user in enumerate(u for u in users if u["workstation"]):
        machines[user["workstation"]] = f"10.0.2.{10 + i}"

    return {"users": users, "machines": machines, "service_accounts": [SERVICE_ACCOUNT]}


def user_hosts(user):
    # Only 14 of the 50 users have a workstation. Everyone uses mail.
    return [user["workstation"], "MAIL-01"] if user["workstation"] else ["MAIL-01"]


def build_history(company):
    """The 30-day baselines the engine compares every event against (history.json)."""
    users = {
        u["name"]: {
            "countries": ["IN"],
            "hours": u["hours"],
            "hosts": user_hosts(u),
            "actions": NIGHT_ACTIONS if u["hours"] == NIGHT_HOURS else DAY_ACTIONS,
        }
        for u in company["users"]
    }
    service_accounts = {
        SERVICE_ACCOUNT: {
            "logon_types": ["batch"],
            "sources": ["BKP-01"],
            "job_hours": [1],
            "admin": False,
        },
    }
    hosts = {
        name: {
            "outside_peers": [MAIL_RELAY_IP] if name == "MAIL-01" else [],
            "daily_upload_mb": UPLOAD_MB.get(name, WORKSTATION_UPLOAD_MB),
        }
        for name in company["machines"]
    }
    return {"users": users, "service_accounts": service_accounts, "hosts": hosts}


def build_access(company):
    """Which account can reach which machine (access.json), used for the blast radius."""
    access = {u["name"]: user_hosts(u) for u in company["users"]}
    access[SERVICE_ACCOUNT] = list(SERVICE_ACCOUNT_REACH)
    return access


def at(clock):
    """'03:12:17' -> that time on the scenario night, in UTC."""
    h, m, s = (int(part) for part in clock.split(":"))
    return WINDOW_START.replace(hour=h, minute=m, second=s)


def event(clock, source, action, user=None, host=None, src=None, dst=None, late_by=None, **attrs):
    ts = at(clock)
    return {
        "ts": ts,
        "received_at": ts + (late_by or timedelta(seconds=2)),
        "source": source,
        "action": action,
        "user": user,
        "host": host,
        "src": src,
        "dst": dst,
        "attrs": attrs,
    }


def attack_events():
    """The 12 planted events, in step order (PLAN section 5).

    Each step stays under the old alert limits.
    """
    return [
        # Step 1, initial access: two failures then a success, from Romania.
        event("03:09:40", "vpn-gw", "AUTH_FAIL", user="priya.s", src=ATTACKER_IP, geo="RO"),
        event("03:10:55", "vpn-gw", "AUTH_FAIL", user="priya.s", src=ATTACKER_IP, geo="RO"),
        event("03:12:17", "vpn-gw", "AUTH_OK", user="priya.s", src=ATTACKER_IP, geo="RO"),
        # Step 2, privilege escalation: look up groups, then add svc-backup to Domain Admins.
        event(
            "03:38:05",
            "WS-PRIYA-014",
            "PROC_START",
            user="priya.s",
            host="WS-PRIYA-014",
            cmd="net-group",
        ),
        event(
            "03:41:22",
            "dc",
            "GROUP_ADD",
            user="priya.s",
            host="DC-01",
            actor="priya.s",
            member="svc-backup",
            group="Domain-Admins",
        ),
        # Step 3, lateral movement. The logon arrives 6 minutes late, after the ticket request.
        event(
            "03:44:10",
            "dc",
            "LOGON",
            user="svc-backup",
            host="DC-01",
            src="WS-PRIYA-014",
            late_by=timedelta(minutes=6),
            type="interactive",
        ),
        event(
            "03:45:02",
            "dc",
            "TICKET_REQ",
            user="svc-backup",
            host="DC-01",
            src="WS-PRIYA-014",
            service="cifs/FIN-SRV-02",
        ),
        # Step 4, collection: read the payroll share.
        event(
            "03:52:30",
            "files",
            "SMB_SESSION",
            user="svc-backup",
            host="FIN-SRV-02",
            src="WS-PRIYA-014",
        ),
        event(
            "03:53:12",
            "files",
            "FILE_READ",
            user="svc-backup",
            host="FIN-SRV-02",
            src="WS-PRIYA-014",
            path="/finance/payroll/2026",
            files=1412,
        ),
        # Step 5, exfiltration. The DNS lookup matches no rule; it is the event we expect to miss.
        event("04:05:40", "fw-edge", "DNS_QUERY", src="FIN-SRV-02"),
        event("04:06:01", "fw-edge", "CONN_OPEN", src="FIN-SRV-02", dst=EXFIL_IP),
        event(
            "04:19:33",
            "fw-edge",
            "CONN_CLOSE",
            src="FIN-SRV-02",
            dst=EXFIL_IP,
            bytes_out=2_254_857_830,
        ),
    ]


def dos_events(count=1800):
    """Connection flood on MAIL-01.

    One outside address opens ~10 connections a second for 3 minutes.
    """

    def clock(i):
        t = 4 * 3600 + i // 10
        return f"{t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"

    return [
        event(clock(i), "fw-edge", "CONN_OPEN", src=DOS_IP, dst="MAIL-01") for i in range(count)
    ]
