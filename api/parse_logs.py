import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

FIELD_ALIASES = {
    "ts": ("ts", "timestamp", "@timestamp", "time", "eventtime", "event_time", "datetime", "date"),
    "source": ("source", "log_source", "logsource", "sourcetype", "app", "program"),
    "action": ("action", "event", "event_type", "eventname", "event_name", "activity", "act"),
    "user": ("user", "username", "user_name", "account", "usr", "userprincipalname"),
    "host": ("host", "hostname", "computer", "computer_name", "device", "machine"),
    "src": ("src", "src_ip", "source_ip", "client_ip", "clientip", "remote_addr", "ip"),
    "dst": ("dst", "dst_ip", "dest", "dest_ip", "destination", "destination_ip", "server_ip"),
}
ALIAS_TO_FIELD = {alias: field for field, aliases in FIELD_ALIASES.items() for alias in aliases}
MAX_LINE = 65536

KV_TOKEN = re.compile(r'([^\s="]+)=("([^"]*)"|\S*)|(\S+)')
TIME_OF_DAY = re.compile(r"^\d{2}:\d{2}:\d{2}$")
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
EPOCH = re.compile(r"^\d{9,13}(\.\d+)?$")
SYSLOG_5424 = re.compile(r"^<\d{1,3}>1 (\S+) (\S+) (\S+) \S+ \S+ (-|(?:\[[^\]]*\])+) ?(.*)$")
SYSLOG_3164 = re.compile(
    r"^<\d{1,3}>([A-Z][a-z]{2} [ \d]\d \d{2}:\d{2}:\d{2}) (\S+) ([^:\[\s]+)(?:\[\d+\])?: ?(.*)$"
)
HEADER_CELL = re.compile(r"^[A-Za-z_@][\w.@ -]*$")


def normalize_key(key):
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")


def iso_utc(moment):
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC)
    return moment.replace(tzinfo=None, microsecond=0).isoformat() + "Z"


def parse_time(value, day):
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        value = str(value)
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        if TIME_OF_DAY.match(value):
            return iso_utc(datetime.combine(day, datetime.strptime(value, "%H:%M:%S").time()))
        if EPOCH.match(value):
            seconds = float(value)
            if seconds >= 1e12:
                seconds /= 1000
            return iso_utc(datetime.fromtimestamp(seconds, UTC))
        if ":" not in value:
            return None
        return iso_utc(datetime.fromisoformat(value))
    except (ValueError, OverflowError, OSError):
        return None


def as_text(value):
    if isinstance(value, dict | list):
        return json.dumps(value, separators=(",", ":"))
    return str(value).strip()


def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())


def to_event(fields, raw, number, day):
    event = {
        "id": f"L-{number:04d}",
        "ts": None,
        "received_at": None,
        "source": None,
        "action": None,
        "user": None,
        "host": None,
        "src": None,
        "dst": None,
        "attrs": {},
        "raw": raw,
    }
    for key, value in fields.items():
        if is_empty(value):
            continue
        name = normalize_key(key)
        field = ALIAS_TO_FIELD.get(name)
        if field == "ts" and event["ts"] is None:
            event["ts"] = parse_time(value, day)
            if event["ts"] is not None:
                continue
        elif field and field != "ts" and event[field] is None:
            event[field] = as_text(value)
            continue
        event["attrs"][name] = as_text(value) if isinstance(value, dict | list) else value
    if event["ts"] is None:
        raise ValueError("no readable time")
    event["received_at"] = event["ts"]
    event["source"] = event["source"] or "unknown"
    action = re.sub(r"[^A-Z0-9]+", "_", (event["action"] or "").upper()).strip("_")
    event["action"] = action or "UNKNOWN"
    return event


def kv_pairs(text):
    lead, pairs, words = [], {}, []
    for match in KV_TOKEN.finditer(text):
        key, value, quoted, word = match.groups()
        if word is not None:
            (words if pairs else lead).append(word)
        elif key not in pairs:
            pairs[key] = quoted if quoted is not None else value
    return lead, pairs, words


def parse_kv(line, day):
    lead, pairs, words = kv_pairs(line)
    if not pairs:
        raise ValueError("unknown format")
    fields = {}
    if len(lead) > 1 and DATE_ONLY.match(lead[0]) and TIME_OF_DAY.match(lead[1]):
        lead[:2] = [f"{lead[0]}T{lead[1]}"]
    if lead and parse_time(lead[0], day) is not None:
        fields["ts"] = lead.pop(0)
    for name in ("source", "action"):
        if lead:
            fields[name] = lead.pop(0)
    for key, value in pairs.items():
        fields.setdefault(key, value)
    message = " ".join(lead + words)
    if message:
        fields.setdefault("message", message)
    return fields


def reject_constant(name):
    raise ValueError(f"JSON value {name} is not allowed")


def parse_json(line):
    try:
        record = json.loads(line, parse_constant=reject_constant)
    except RecursionError:
        raise ValueError("JSON nested too deep") from None
    if not isinstance(record, dict):
        raise ValueError("JSON line is not an object")
    return record


def syslog_3164_time(stamp, day):
    month_name, day_of_month, clock = stamp.split()
    if month_name not in MONTHS:
        raise ValueError("unreadable syslog time")
    hour, minute, second = (int(part) for part in clock.split(":"))
    month = MONTHS.index(month_name) + 1
    for year in (day.year, day.year - 1):
        try:
            moment = datetime(year, month, int(day_of_month), hour, minute, second)
        except ValueError:
            continue
        if moment.date() <= day + timedelta(days=1):
            return iso_utc(moment)
    raise ValueError("unreadable syslog time")


def parse_syslog(line, day):
    match = SYSLOG_5424.match(line)
    if match:
        stamp, host, app, _, message = match.groups()
        ts = None if stamp == "-" else stamp
    else:
        match = SYSLOG_3164.match(line)
        if not match:
            raise ValueError("unreadable syslog header")
        stamp, host, app, message = match.groups()
        ts = syslog_3164_time(stamp, day)
    fields = {"ts": ts}
    fields["host"] = None if host == "-" else host
    fields["source"] = None if app == "-" else app
    _, pairs, _ = kv_pairs(message)
    for key, value in pairs.items():
        fields.setdefault(key, value)
    fields["message"] = message
    return fields


def csv_header(lines):
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if len(line) > MAX_LINE or line.lstrip().startswith(("{", "<")):
            return None
        if "=" in line or "," not in line:
            return None
        cells = [cell.strip() for cell in next(csv.reader([line]))]
        if not all(HEADER_CELL.match(cell) for cell in cells):
            return None
        if not any(normalize_key(cell) in ALIAS_TO_FIELD for cell in cells):
            return None
        return number, cells
    return None


def read_line(line, columns, day):
    if columns is not None:
        try:
            cells = next(csv.reader([line]))
        except csv.Error as exc:
            raise ValueError(f"unreadable CSV row: {exc}") from None
        if len(cells) != len(columns):
            raise ValueError(f"{len(cells)} columns, header has {len(columns)}")
        return "csv", dict(zip(columns, cells, strict=True))
    stripped = line.strip()
    if stripped.startswith("{"):
        return "json", parse_json(stripped)
    if re.match(r"^<\d{1,3}>", stripped):
        return "syslog", parse_syslog(stripped, day)
    return "key=value", parse_kv(stripped, day)


def parse_text(text, day):
    lines = [line.removesuffix("\r") for line in text.lstrip("﻿").split("\n")]
    header = csv_header(lines)
    header_line, columns = header if header else (None, None)
    events, unparsed, formats = [], [], Counter()
    for number, line in enumerate(lines, start=1):
        if not line.strip() or number == header_line:
            continue
        try:
            if len(line) > MAX_LINE:
                raise ValueError("line too long")
            kind, fields = read_line(line, columns, day)
            event = to_event(fields, line, number, day)
        except ValueError as exc:
            unparsed.append({"line": number, "reason": str(exc), "raw": line[:MAX_LINE]})
            continue
        formats[kind] += 1
        events.append(event)
    return events, unparsed, dict(formats)


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Turn a raw log file into Chimera events.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        required=True,
        help="UTC day for lines that carry only a time of day, and the year for old syslog",
    )
    args = parser.parse_args(argv)
    try:
        text = args.file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"Cannot read {args.file}: {exc.strerror}", file=sys.stderr)
        return 1
    events, unparsed, formats = parse_text(text, args.date)
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "events.jsonl", events)
    write_jsonl(args.out / "unparsed.jsonl", unparsed)
    kinds = ", ".join(f"{kind} {count}" for kind, count in sorted(formats.items())) or "none"
    print(f"{len(events)} events ({kinds}), {len(unparsed)} unparsed lines")
    if unparsed:
        print(f"Unparsed lines are in {args.out / 'unparsed.jsonl'}")
    return 0 if events else 1


if __name__ == "__main__":
    sys.exit(main())
