import json

from engine.intake import (
    alert_rules,
    build_intake,
    is_late,
    latest_events,
    most_failed_sign_ins,
    read_events,
    summarize,
    volume_by_five_minutes,
)


def event(
    event_id,
    ts,
    received_at,
    source="vpn-gw",
    raw="example log line",
    action="HEALTH_OK",
    user=None,
    attrs=None,
):
    return {
        "id": event_id,
        "ts": ts,
        "received_at": received_at,
        "source": source,
        "action": action,
        "user": user,
        "host": None,
        "src": None,
        "dst": None,
        "attrs": attrs or {},
        "raw": raw,
    }


def test_read_events_keeps_jsonl_arrival_order_and_ignores_blank_lines(tmp_path):
    path = tmp_path / "events.jsonl"
    first = event("L-0002", "2026-11-14T03:05:00Z", "2026-11-14T03:05:01Z")
    second = event("L-0001", "2026-11-14T03:00:00Z", "2026-11-14T03:06:00Z")
    path.write_text(
        json.dumps(first) + "\n\n" + json.dumps(second) + "\n",
        encoding="utf-8",
    )

    events = read_events(path)

    assert [item["id"] for item in events] == ["L-0002", "L-0001"]


def test_late_means_strictly_more_than_two_minutes():
    exactly_two_minutes = event(
        "L-0001",
        "2026-11-14T03:00:00Z",
        "2026-11-14T03:02:00Z",
    )
    over_two_minutes = event(
        "L-0002",
        "2026-11-14T03:00:00Z",
        "2026-11-14T03:02:01Z",
    )

    assert not is_late(exactly_two_minutes)
    assert is_late(over_two_minutes)


def test_summary_counts_only_the_four_log_sources():
    events = [
        event("L-0001", "2026-11-14T03:00:00Z", "2026-11-14T03:00:01Z", "vpn-gw"),
        event("L-0002", "2026-11-14T03:00:01Z", "2026-11-14T03:00:02Z", "files"),
        event("L-0003", "2026-11-14T03:00:02Z", "2026-11-14T03:03:00Z", "MAIL-01"),
    ]

    result = summarize(events, alerts_fired=1)

    assert result == {"events": 3, "sources": 2, "late": 1, "alerts_fired": 1}


def test_volume_uses_source_time_and_includes_empty_buckets():
    events = [
        event("L-0001", "2026-11-14T03:00:02Z", "2026-11-14T03:00:03Z"),
        event("L-0002", "2026-11-14T03:09:59Z", "2026-11-14T03:10:00Z"),
        event("L-0003", "2026-11-14T03:15:00Z", "2026-11-14T03:15:01Z"),
    ]

    assert volume_by_five_minutes(events) == [
        {"start": "03:00", "count": 1},
        {"start": "03:05", "count": 1},
        {"start": "03:10", "count": 0},
        {"start": "03:15", "count": 1},
    ]


def test_volume_is_empty_when_there_are_no_events():
    assert volume_by_five_minutes([]) == []


def test_latest_events_uses_arrival_order_and_stops_at_eight():
    events = [
        event(
            f"L-{index:04d}",
            f"2026-11-14T03:00:{index:02d}Z",
            f"2026-11-14T03:00:{index + 1:02d}Z",
            raw=f"log {index}",
        )
        for index in range(1, 10)
    ]

    latest = latest_events(events)

    assert len(latest) == 8
    assert [item["id"] for item in latest] == [f"L-{index:04d}" for index in range(1, 9)]
    assert latest[0] == {
        "id": "L-0001",
        "time": "03:00:01",
        "source": "vpn-gw",
        "raw": "log 1",
    }


def test_failed_sign_ins_use_the_busiest_user_and_rolling_sixty_seconds():
    events = [
        event(
            f"L-{index:04d}",
            f"2026-11-14T03:00:{second:02d}Z",
            f"2026-11-14T03:01:{second:02d}Z",
            action="AUTH_FAIL",
            user="priya.s",
        )
        for index, second in enumerate((0, 15, 30, 45, 59), 1)
    ]
    events.append(
        event(
            "L-0006",
            "2026-11-14T03:02:00Z",
            "2026-11-14T03:02:01Z",
            action="AUTH_FAIL",
            user="another.user",
        )
    )

    assert most_failed_sign_ins(reversed(events)) == 5


def test_alert_rules_fire_when_their_thresholds_are_crossed():
    events = [
        event(
            f"L-{index:04d}",
            f"2026-11-14T03:00:{index:02d}Z",
            f"2026-11-14T03:00:{index + 1:02d}Z",
            action="AUTH_FAIL",
            user="priya.s",
        )
        for index in range(1, 6)
    ]
    events.extend(
        [
            event(
                "L-0006",
                "2026-11-14T03:01:00Z",
                "2026-11-14T03:01:01Z",
                source="fw-edge",
                action="CONN_CLOSE",
                attrs={"bytes_out": 5 * 1024**3 + 1},
            ),
            event(
                "L-0007",
                "2026-11-14T03:02:00Z",
                "2026-11-14T03:02:01Z",
                action="AUTH_OK",
                user="priya.s",
                attrs={"geo": "IR"},
            ),
            event(
                "L-0008",
                "2026-11-14T03:03:00Z",
                "2026-11-14T03:03:01Z",
                source="dc",
                action="GROUP_ADD",
                attrs={"actor": "intruder", "group": "Domain-Admins"},
            ),
        ]
    )

    rules = alert_rules(events, {"users": {"priya.s": {}}})

    assert [rule["fired"] for rule in rules] == [True, True, True, True]
    assert [rule["ratio"] for rule in rules] == [1, 1, 1.0, 1.0]


def test_transfer_rule_means_strictly_over_five_gigabytes():
    transfer = event(
        "L-0001",
        "2026-11-14T03:00:00Z",
        "2026-11-14T03:00:01Z",
        source="fw-edge",
        action="CONN_CLOSE",
        attrs={"bytes_out": 5 * 1024**3},
    )

    rule = alert_rules([transfer], {"users": {}})[1]

    assert rule["ratio"] == 1
    assert not rule["fired"]


def test_generated_data_stays_below_all_old_alert_limits():
    events = read_events("data/events.jsonl")
    with open("data/history.json", encoding="utf-8") as source:
        history = json.load(source)

    intake = build_intake(events, history)

    assert intake["summary"] == {
        "events": 5124,
        "sources": 4,
        "late": 212,
        "alerts_fired": 0,
    }
    assert [rule["fired"] for rule in intake["alert_rules"]] == [False] * 4
    assert intake["alert_rules"][0]["seen"] == "saw 1 of 5"
    assert intake["alert_rules"][1]["seen"] == "saw 2.1 GB of 5 GB"
    assert len(intake["latest"]) == 8
