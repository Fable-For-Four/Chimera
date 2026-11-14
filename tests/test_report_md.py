import copy
import json
from pathlib import Path

from api.report_md import build, md

SAMPLE = json.loads(
    (Path(__file__).parent / "fixtures" / "case.sample.json").read_text(encoding="utf-8")
)
NOW = "2026-11-14 10:00 UTC"


def sample():
    return copy.deepcopy(SAMPLE)


def test_report_has_every_section_with_citations():
    text = build(sample(), {}, None, NOW)
    assert text.startswith("# Incident report: Likely attack\n")
    for heading in [
        "## What happened",
        "## Timeline",
        "## What the logs cannot prove",
        "## Response actions",
    ]:
        assert heading in text
    first = SAMPLE["report"][0]
    assert f"({', '.join(f'`{c}`' for c in first['cites'])})" in text
    assert f"- **Confidence:** {SAMPLE['verdict']['confidence']}%" in text
    assert f"- **Exported:** {NOW}" in text
    assert text.count("\n| ") == len(SAMPLE["chain"]) + 1


def test_approved_and_waiting_actions_are_checkboxes():
    first, second = SAMPLE["actions"][0], SAMPLE["actions"][1]
    approvals = {first["id"]: {"approved_by": "Ana", "approved_at": "2026-11-14T09:00:00+00:00"}}
    text = build(sample(), approvals, None, NOW)
    assert f"- [x] {first['kind']}: " in text
    assert "approved by Ana at 2026-11-14T09:00:00+00:00" in text
    assert f"- [ ] {second['kind']}: " in text


def test_log_text_cannot_inject_markdown_or_html():
    case = sample()
    case["report"][0]["text"] = (
        "user=<script>alert(1)</script> | [click](http://x) *bold*\n# heading"
    )
    case["chain"][0]["what"] = "a | b"
    text = build(case, {}, None, NOW)
    assert "<script>" not in text
    assert "\\<script\\>" in text
    assert "\\[click\\]" in text
    assert "\n# heading" not in text
    assert "a \\| b" in text


def test_inferred_step_and_deleted_evidence_are_marked():
    case = sample()
    case["chain"][2]["inferred"] = True
    for exhibit in case["chain"][2]["exhibits"]:
        exhibit["present"] = False
    row = next(line for line in build(case, {}, None, NOW).splitlines() if line.startswith("| 3 |"))
    assert "(inferred, its log is missing)" in row
    assert row.endswith("| none |")


def test_stress_level_and_upload_source_are_stated():
    case = sample()
    case["level"], case["deleted"] = 20, 1025
    source = {"kind": "upload", "name": "night.log", "events": 5124, "unparsed": 3}
    text = build(case, {}, source, NOW)
    assert "- **Stress test:** 20% of logs deleted (1,025 events)" in text
    assert "from the uploaded file night.log, 3 lines could not be read" in text


def test_no_chain_case_has_no_empty_sections():
    case = sample()
    case.update(report=[], chain=[], limits=[], actions=[])
    case["verdict"].update(label="No chain found", confidence=0)
    text = build(case, {}, None, NOW)
    assert "No attack chain was found" in text
    for heading in ["## Timeline", "## What the logs cannot prove", "## Response actions"]:
        assert heading not in text


def test_md_flattens_newlines_and_escapes_specials():
    assert md("a\n\nb  c") == "a b c"
    assert md("svc_backup `x`") == "svc\\_backup \\`x\\`"
