import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

LOG_SOURCES = {"vpn-gw", "dc", "files", "fw-edge"}
FAILED_SIGN_IN_LIMIT = 5
FAILED_SIGN_IN_WINDOW = timedelta(seconds=60)
TRANSFER_LIMIT_BYTES = 5 * 1024**3
BLOCKED_COUNTRIES = {"KP", "IR"}


def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_events(path):
    events = []
    with Path(path).open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                events.append(json.loads(line))
    return events


def is_late(event):
    received_at = parse_timestamp(event["received_at"])
    event_time = parse_timestamp(event["ts"])
    return received_at - event_time > timedelta(minutes=2)


def summarize(events, alerts_fired=0):
    sources = {event["source"] for event in events if event["source"] in LOG_SOURCES}
    return {
        "events": len(events),
        "sources": len(sources),
        "late": sum(is_late(event) for event in events),
        "alerts_fired": alerts_fired,
    }


def volume_by_five_minutes(events):
    if not events:
        return []

    counts = {}
    for event in events:
        event_time = parse_timestamp(event["ts"])
        bucket = event_time.replace(
            minute=(event_time.minute // 5) * 5,
            second=0,
            microsecond=0,
        )
        counts[bucket] = counts.get(bucket, 0) + 1

    first = min(counts)
    last = max(counts)
    volume = []
    current = first
    while current <= last:
        volume.append({"start": current.strftime("%H:%M"), "count": counts.get(current, 0)})
        current += timedelta(minutes=5)
    return volume


def latest_events(events, limit=8):
    return [
        {
            "id": event["id"],
            "time": parse_timestamp(event["ts"]).strftime("%H:%M:%S"),
            "source": event["source"],
            "raw": event["raw"],
        }
        for event in events[:limit]
    ]


def most_failed_sign_ins(events):
    failures = defaultdict(list)
    for event in events:
        if event["action"] == "AUTH_FAIL" and event.get("user"):
            failures[event["user"]].append(parse_timestamp(event["ts"]))

    most = 0
    for times in failures.values():
        window = deque()
        for event_time in sorted(times):
            window.append(event_time)
            while event_time - window[0] > FAILED_SIGN_IN_WINDOW:
                window.popleft()
            most = max(most, len(window))
    return most


def largest_outbound_transfer(events):
    return max(
        (
            event.get("attrs", {}).get("bytes_out", 0)
            for event in events
            if event["action"] == "CONN_CLOSE"
        ),
        default=0,
    )


def display_gigabytes(byte_count):
    value = byte_count / 1024**3
    return f"{value:.1f}".rstrip("0").rstrip(".")


def alert_rules(events, history):
    failed_sign_ins = most_failed_sign_ins(events)
    largest_transfer = largest_outbound_transfer(events)
    blocked_sign_ins = sum(
        event["action"] == "AUTH_OK" and event.get("attrs", {}).get("geo") in BLOCKED_COUNTRIES
        for event in events
    )
    known_users = set(history.get("users", {}))
    unknown_admin_changes = sum(
        event["action"] == "GROUP_ADD" and event.get("attrs", {}).get("actor") not in known_users
        for event in events
    )

    return [
        {
            "name": "5 failed sign-ins in a minute",
            "seen": f"saw {failed_sign_ins} of {FAILED_SIGN_IN_LIMIT}",
            "ratio": round(min(failed_sign_ins / FAILED_SIGN_IN_LIMIT, 1), 2),
            "fired": failed_sign_ins >= FAILED_SIGN_IN_LIMIT,
        },
        {
            "name": "Outbound transfer over 5 GB",
            "seen": f"saw {display_gigabytes(largest_transfer)} GB of 5 GB",
            "ratio": round(min(largest_transfer / TRANSFER_LIMIT_BYTES, 1), 2),
            "fired": largest_transfer > TRANSFER_LIMIT_BYTES,
        },
        {
            "name": "Sign-in from a blocked country",
            "seen": "saw none" if blocked_sign_ins == 0 else f"saw {blocked_sign_ins}",
            "ratio": 0.0 if blocked_sign_ins == 0 else 1.0,
            "fired": blocked_sign_ins > 0,
        },
        {
            "name": "Admin group changed by an unknown account",
            "seen": "saw none" if unknown_admin_changes == 0 else f"saw {unknown_admin_changes}",
            "ratio": 0.0 if unknown_admin_changes == 0 else 1.0,
            "fired": unknown_admin_changes > 0,
        },
    ]


def build_intake(events, history):
    rules = alert_rules(events, history)
    return {
        "summary": summarize(events, sum(rule["fired"] for rule in rules)),
        "alert_rules": rules,
        "volume": volume_by_five_minutes(events),
        "latest": latest_events(events),
    }
