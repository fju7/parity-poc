"""The sender refuses a gate report that is about a different body.

On 2026-09-11 send_broadcast.require_gate refused the correction email with
"records a FAILED run" while reading run 3's report -- a report about draft
sha 947317ce, a body that no longer existed. The refusal was right by
accident: passed:false was consulted before the sha, so a stale PASSING
report would have reached the sha check as its only guard, and a stale
FAILING one was reported for the wrong reason with neither sha named.

The report's `sha256` is sha256 of the rendered HTML file's bytes at gate
time; the sender hashes the HTML text it is about to send, re-encoded UTF-8,
which is the same bytes. These four cases are the whole truth table.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "site" / "whatholdsup" / "email" / "send_broadcast.py"


def _load():
    spec = importlib.util.spec_from_file_location("send_broadcast_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["send_broadcast_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


SB = _load()
BODY = "<p>the body about to be sent {{{RESEND_UNSUBSCRIBE_URL}}}</p>"
OTHER = "<p>a body that no longer exists</p>"


def _report(tmp_path, content, passed):
    p = tmp_path / "x.html.gate.json"
    p.write_text(json.dumps({"sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                             "passed": passed, "checked_at": "2026-09-11"}))
    return p


def _refusal(tmp_path, content, passed):
    with pytest.raises(SystemExit) as e:
        SB.require_gate(BODY, _report(tmp_path, content, passed), None, "the body")
    return str(e.value)


def test_stale_passing_report_is_refused_and_names_both_shas(tmp_path):
    msg = _refusal(tmp_path, OTHER, passed=True)
    assert "is not about the body" in msg
    assert hashlib.sha256(OTHER.encode()).hexdigest()[:16] in msg
    assert hashlib.sha256(BODY.encode()).hexdigest()[:16] in msg


def test_stale_failing_report_is_refused_for_being_stale_not_for_failing(tmp_path):
    msg = _refusal(tmp_path, OTHER, passed=False)
    assert "is not about the body" in msg
    assert "FAILED run" not in msg
    assert hashlib.sha256(OTHER.encode()).hexdigest()[:16] in msg
    assert hashlib.sha256(BODY.encode()).hexdigest()[:16] in msg


def test_matching_passing_report_is_accepted(tmp_path, capsys):
    SB.require_gate(BODY, _report(tmp_path, BODY, passed=True), None, "the body")
    assert "sha matches" in capsys.readouterr().out


def test_matching_failing_report_is_refused_as_failed(tmp_path):
    msg = _refusal(tmp_path, BODY, passed=False)
    assert "FAILED run" in msg
    assert hashlib.sha256(BODY.encode()).hexdigest()[:16] in msg


def test_the_report_on_disk_today_is_about_a_different_body():
    """Run 3's report against the HTML beside it: the case that was live."""
    rep = ROOT / "site/whatholdsup/email/corrections/2026-09-10-corrections.html.gate.json"
    html = ROOT / "site/whatholdsup/email/corrections/2026-09-10-corrections.html"
    if not (rep.exists() and html.exists()):
        pytest.skip("archived")
    r = json.loads(rep.read_text())
    assert r["sha256"] != hashlib.sha256(html.read_bytes()).hexdigest()
