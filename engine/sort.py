"""Stage 1: put events in time order and flag the ones that arrived late (PLAN 6.2)."""

from datetime import datetime

LATE_AFTER_SECONDS = 120


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


def sort_events(events):
    out = [
        {
            **e,
            "late": (parse(e["received_at"]) - parse(e["ts"])).total_seconds() > LATE_AFTER_SECONDS,
        }
        for e in events
    ]
    out.sort(key=lambda e: (e["ts"], e["id"]))  # ISO timestamps sort correctly as text
    return out, f"{sum(e['late'] for e in out)} late events moved"
