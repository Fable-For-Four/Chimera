import json
from datetime import date

from api.parse_logs import MAX_LINE, main, parse_text

DAY = date(2026, 11, 14)

EVENT_KEYS = {
    "id",
    "ts",
    "received_at",
    "source",
    "action",
    "user",
    "host",
    "src",
    "dst",
    "attrs",
    "raw",
}
GENERATOR_LINE = "03:12:17 vpn-gw AUTH_OK user=priya.s src=203.0.113.47 geo=RO"


def parse_one(line):
    events, unparsed, _ = parse_text(line, DAY)
    assert unparsed == []
    assert len(events) == 1
    return events[0]


def test_generator_line_parses_to_full_event():
    event = parse_one(GENERATOR_LINE)
    assert event == {
        "id": "L-0001",
        "ts": "2026-11-14T03:12:17Z",
        "received_at": "2026-11-14T03:12:17Z",
        "source": "vpn-gw",
        "action": "AUTH_OK",
        "user": "priya.s",
        "host": None,
        "src": "203.0.113.47",
        "dst": None,
        "attrs": {"geo": "RO"},
        "raw": GENERATOR_LINE,
    }


def test_every_event_has_exactly_the_event_keys_and_received_at_equals_ts():
    text = "\n".join(
        [
            GENERATOR_LINE,
            '{"timestamp": "2026-11-14T04:00:00Z", "event": "x"}',
            "<34>Nov 14 05:00:00 h1 sshd[1]: user=bob",
        ]
    )
    events, unparsed, _ = parse_text(text, DAY)
    assert unparsed == []
    assert len(events) == 3
    for event in events:
        assert set(event) == EVENT_KEYS
        assert event["received_at"] == event["ts"]


def test_json_aliases_map_and_offset_converts_to_utc():
    line = (
        '{"timestamp": "2026-11-14T08:42:17+05:30", "username": "bob",'
        ' "client_ip": "10.0.0.5", "event": "login failed"}'
    )
    event = parse_one(line)
    assert event["ts"] == "2026-11-14T03:12:17Z"
    assert event["user"] == "bob"
    assert event["src"] == "10.0.0.5"
    assert event["action"] == "LOGIN_FAILED"
    assert event["source"] == "unknown"


def test_whole_numbers_in_text_become_numbers_but_codes_stay_text():
    event = parse_one("03:00:00 files FILE_READ user=a files=1412 bytes_out=0 zip=007 ratio=1.5")
    assert event["attrs"] == {"files": 1412, "bytes_out": 0, "zip": "007", "ratio": "1.5"}


def test_json_numbers_stay_numbers_and_nested_dict_becomes_compact_string():
    line = '{"ts": "2026-11-14T03:00:00Z", "port": 443, "ratio": 1.5, "meta": {"a": 1, "b": [2]}}'
    event = parse_one(line)
    assert event["attrs"]["port"] == 443
    assert isinstance(event["attrs"]["port"], int)
    assert event["attrs"]["ratio"] == 1.5
    assert event["attrs"]["meta"] == '{"a":1,"b":[2]}'


def test_json_array_goes_to_unparsed():
    events, unparsed, _ = parse_text('["a", "b"]', DAY)
    assert events == []
    assert len(unparsed) == 1


def test_invalid_json_goes_to_unparsed():
    events, unparsed, _ = parse_text('{"ts": "03:00:00", ', DAY)
    assert events == []
    assert len(unparsed) == 1
    assert unparsed[0]["line"] == 1


def test_deeply_nested_json_goes_to_unparsed_without_crash():
    events, unparsed, _ = parse_text("[" * 100000, DAY)
    assert events == []
    assert len(unparsed) == 1

    nested = '{"ts": "03:00:00", "a": ' + "[" * 30000
    events, unparsed, _ = parse_text(nested, DAY)
    assert events == []
    assert len(unparsed) == 1


def test_syslog_3164_takes_year_from_day():
    event = parse_one("<34>Nov 14 03:12:17 host1 sshd[123]: Failed password user=bob src=1.2.3.4")
    assert event["ts"] == "2026-11-14T03:12:17Z"
    assert event["host"] == "host1"
    assert event["source"] == "sshd"
    assert event["user"] == "bob"
    assert event["src"] == "1.2.3.4"


def test_syslog_5424_drops_fraction_and_maps_pairs():
    event = parse_one("<165>1 2026-11-14T03:12:17.987Z host2 myapp - - - action=login user=al")
    assert event["ts"] == "2026-11-14T03:12:17Z"
    assert event["host"] == "host2"
    assert event["source"] == "myapp"
    assert event["action"] == "LOGIN"
    assert event["user"] == "al"


def test_syslog_5424_dash_header_values_become_none_and_unknown():
    event = parse_one("<165>1 2026-11-14T03:12:17Z - - - - - user=al")
    assert event["host"] is None
    assert event["source"] == "unknown"


def test_csv_header_maps_columns_and_is_not_an_event():
    text = (
        "Time,Event Type,User Name,Client IP\n"
        "03:12:17,login ok,bob,1.2.3.4\n"
        "03:13:00,logout,amy,5.6.7.8\n"
    )
    events, unparsed, formats = parse_text(text, DAY)
    assert unparsed == []
    assert formats == {"csv": 2}
    assert [event["id"] for event in events] == ["L-0002", "L-0003"]
    assert events[0]["ts"] == "2026-11-14T03:12:17Z"
    assert events[0]["action"] == "LOGIN_OK"
    assert events[0]["user"] == "bob"
    assert events[0]["src"] == "1.2.3.4"


def test_csv_row_with_wrong_column_count_goes_to_unparsed_with_reason():
    text = "Time,Event Type,User Name,Client IP\n03:12:17,login ok,bob,1.2.3.4\n03:13:00,logout\n"
    events, unparsed, _ = parse_text(text, DAY)
    assert len(events) == 1
    assert len(unparsed) == 1
    assert unparsed[0]["line"] == 3
    assert unparsed[0]["raw"] == "03:13:00,logout"
    assert "2 columns" in unparsed[0]["reason"]


def test_quoted_value_keeps_its_space():
    event = parse_one('03:12:17 host1 PROC_START user=bob cmd="net use x"')
    assert event["attrs"]["cmd"] == "net use x"


def test_windows_path_value_keeps_backslashes():
    path = "C:\\Windows\\System32\\cmd.exe"
    event = parse_one(f"03:12:17 host1 PROC_START user=bob path={path}")
    assert event["attrs"]["path"] == path


def test_epoch_seconds_and_milliseconds_timestamps():
    seconds = parse_one("ts=1700000000 action=X")
    millis = parse_one("ts=1700000000000 action=X")
    assert seconds["ts"] == "2023-11-14T22:13:20Z"
    assert millis["ts"] == "2023-11-14T22:13:20Z"


def test_line_without_time_goes_to_unparsed_with_reason():
    events, unparsed, _ = parse_text("vpn-gw AUTH_OK user=bob", DAY)
    assert events == []
    assert unparsed[0]["reason"] == "no readable time"


def test_line_without_pairs_is_unknown_format():
    events, unparsed, _ = parse_text("just some words here", DAY)
    assert events == []
    assert unparsed[0]["reason"] == "unknown format"


def test_overlong_line_is_unparsed_and_raw_is_capped():
    line = "a" * (MAX_LINE + 1)
    events, unparsed, _ = parse_text(line, DAY)
    assert events == []
    assert unparsed[0]["reason"] == "line too long"
    assert len(unparsed[0]["raw"]) == MAX_LINE


def test_blank_lines_and_bom_are_skipped():
    text = "\ufeff\n" + GENERATOR_LINE + "\n\n   \n"
    events, unparsed, _ = parse_text(text, DAY)
    assert unparsed == []
    assert len(events) == 1
    assert events[0]["id"] == "L-0002"
    assert events[0]["raw"] == GENERATOR_LINE


def test_windows_line_endings_work():
    text = GENERATOR_LINE + "\r\n03:13:00 vpn-gw AUTH_OK user=amy\r\n"
    events, unparsed, _ = parse_text(text, DAY)
    assert unparsed == []
    assert len(events) == 2
    assert events[0]["raw"] == GENERATOR_LINE
    assert events[1]["user"] == "amy"


def test_events_keep_file_order_even_when_times_go_backwards():
    text = "05:00:00 a X user=late\n03:00:00 a X user=early\n"
    events, _, _ = parse_text(text, DAY)
    assert [event["user"] for event in events] == ["late", "early"]
    assert [event["id"] for event in events] == ["L-0001", "L-0002"]


def test_date_and_time_as_two_leading_words_make_one_timestamp():
    event = parse_one("2026-11-14 03:12:17 vpn-gw AUTH_OK user=priya.s src=1.2.3.4")
    assert event["ts"] == "2026-11-14T03:12:17Z"
    assert (event["source"], event["action"]) == ("vpn-gw", "AUTH_OK")
    assert "message" not in event["attrs"]


def test_a_date_without_a_time_is_not_a_timestamp():
    events, unparsed, _ = parse_text("date=2026-11-14 user=bob\n", DAY)
    assert events == []
    assert unparsed[0]["reason"] == "no readable time"


def test_separate_date_and_time_csv_columns_use_the_time():
    text = "Date,Time,User\n2026-11-14,03:12:17,bob\n"
    events, _, _ = parse_text(text, DAY)
    assert events[0]["ts"] == "2026-11-14T03:12:17Z"


def test_unicode_line_separators_stay_inside_the_raw_line():
    line = "03:00:00 a X user=u msg=a b\x0cc"
    events, unparsed, _ = parse_text(line + "\n", DAY)
    assert unparsed == []
    assert events[0]["raw"] == line


def test_a_huge_comma_first_line_does_not_crash():
    text = "x" * 200000 + ",y\n03:00:00 a X user=u\n"
    events, unparsed, _ = parse_text(text, DAY)
    assert unparsed[0]["reason"] == "line too long"
    assert events[0]["user"] == "u"


def test_nan_and_infinity_in_json_go_to_unparsed():
    text = '{"ts": "03:00:00", "n": NaN}\n{"ts": "03:00:00", "n": -Infinity}\n'
    events, unparsed, _ = parse_text(text, DAY)
    assert events == []
    assert [row["reason"] for row in unparsed] == [
        "JSON value NaN is not allowed",
        "JSON value -Infinity is not allowed",
    ]


def test_old_syslog_from_december_read_in_january_gets_last_year():
    events, _, _ = parse_text("<34>Dec 31 23:59:00 h su: user=bob\n", date(2027, 1, 1))
    assert events[0]["ts"] == "2026-12-31T23:59:00Z"


def test_old_syslog_feb_29_uses_the_last_leap_year_it_fits():
    events, _, _ = parse_text("<34>Feb 29 10:00:00 h su: user=bob\n", date(2025, 3, 1))
    assert events[0]["ts"] == "2024-02-29T10:00:00Z"


def test_old_syslog_with_an_unknown_month_is_unparsed():
    _, unparsed, _ = parse_text("<34>Foo 11 10:00:00 h su: user=bob\n", DAY)
    assert unparsed[0]["reason"] == "unreadable syslog time"


def test_cli_requires_a_date(tmp_path, capsys):
    log = tmp_path / "a.log"
    log.write_text("03:00:00 a X user=u\n", encoding="utf-8")
    try:
        main([str(log), "--out", str(tmp_path / "out")])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected the CLI to exit")


def test_no_line_is_dropped():
    text = "\n".join(
        [
            "Time,Event Type,User Name",
            "03:00:00,a,bob",
            "bad,row",
            "",
            "03:01:00,b,amy",
            "x,y,z,w",
        ]
    )
    events, unparsed, _ = parse_text(text, DAY)
    assert len(events) + len(unparsed) == 4

    mixed = "\n".join([GENERATOR_LINE, "", "hello there", "vpn AUTH user=a", '{"a": 1}', "[1]"])
    events, unparsed, _ = parse_text(mixed, DAY)
    assert len(events) + len(unparsed) == 5


def test_missing_source_and_action_default():
    event = parse_one("ts=03:12:17 user=bob")
    assert event["source"] == "unknown"
    assert event["action"] == "UNKNOWN"


def test_duplicate_alias_keeps_first_and_other_goes_to_attrs():
    event = parse_one("03:12:17 vpn-gw AUTH_OK user=first username=second")
    assert event["user"] == "first"
    assert event["attrs"]["username"] == "second"


def test_same_input_gives_same_output():
    text = "\n".join([GENERATOR_LINE, "junk", '{"ts": "2026-11-14T01:00:00Z", "event": "e"}'])
    assert parse_text(text, DAY) == parse_text(text, DAY)


def test_cli_writes_both_files_and_prints_summary(tmp_path, capsys):
    source = tmp_path / "in.log"
    source.write_text(GENERATOR_LINE + "\nnot a log line\n", encoding="utf-8")
    out = tmp_path / "out"
    code = main([str(source), "--out", str(out), "--date", "2026-11-14"])
    assert code == 0
    events = [json.loads(row) for row in (out / "events.jsonl").read_text().splitlines()]
    unparsed = [json.loads(row) for row in (out / "unparsed.jsonl").read_text().splitlines()]
    assert len(events) == 1
    assert events[0]["id"] == "L-0001"
    assert len(unparsed) == 1
    assert unparsed[0]["line"] == 2
    printed = capsys.readouterr().out
    assert "1 events" in printed
    assert "1 unparsed" in printed


def test_cli_returns_1_when_no_events(tmp_path):
    source = tmp_path / "in.log"
    source.write_text("nothing useful\n", encoding="utf-8")
    out = tmp_path / "out"
    code = main([str(source), "--out", str(out), "--date", "2026-11-14"])
    assert code == 1
    assert (out / "events.jsonl").read_text() == ""
    assert (out / "unparsed.jsonl").exists()


def test_cli_returns_1_when_file_is_missing(tmp_path):
    missing = str(tmp_path / "missing.log")
    code = main([missing, "--out", str(tmp_path / "out"), "--date", "2026-11-14"])
    assert code == 1
