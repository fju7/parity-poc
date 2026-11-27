"""The shared reply rule (advisor's ruling 1 on the 04h fork, 2026-11-27): exactly one top-level JSON value of the
required type, at most a short non-JSON lead-in before it, nothing after it, parsed whole as given (no repair).
$0, offline."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import reply_json as RJ  # noqa: E402

OBJ = {"verdicts": [{"id": "u76", "verdict": "not_a_correction", "kind": None, "evidence": [],
                     "proposed_text": None, "reason": "a heading-like line"}]}
J = json.dumps(OBJ)


def _04h_replies():
    p = ROOT / "issues" / "WHU-OT1-04h-whu-lean-orch-t1-q1-04h" / "audit"
    f = next(iter(sorted(p.glob("*/unparsed_replies.jsonl"))), None) if p.exists() else None
    if not f:
        f = Path(os.path.expanduser("~/Projects/whu-study-private/audit_runs/whu-lean-orch-t1-q1-04h"))
        f = next(iter(sorted(f.glob("*/unparsed_replies.jsonl"))), None) if f.exists() else None
    if not f:
        pytest.skip("04h's recorded replies not present (local only)")
    return [json.loads(l)["text"] for l in f.read_text().splitlines() if l.strip()]


def test_04h_two_replies_pass():
    rs = _04h_replies()
    assert len(rs) == 2
    for r in rs:
        v = RJ.value(r, "object")
        assert v["verdicts"][0]["id"] == "u76"


@pytest.mark.parametrize("text,why", [
    ('The verdict is below.\n\n%s\n\nThat is all.' % J, "text or a second value after"),           # prose after
    ('%s\n%s' % (J, J), "text or a second value after"),                                            # two objects
    ('Lead-in.\n\n' + J[:-5], "does not parse whole"),                                              # truncated
    ('{"a": 1} and then {"b": 2}', "text or a second value after"),
    ('x' * 700 + J, "longer than a short lead-in"),
    ('Here is {"a": 1} inline. %s' % J, "text or a second value after"),
    ('No JSON at all.', "no JSON value"),
])
def test_invalid_replies(text, why):
    with pytest.raises(RJ.Invalid) as e:
        RJ.value(text, "object")
    assert why in str(e.value)


def test_valid_forms():
    assert RJ.value(J) == OBJ                                       # the bare value, as before
    assert RJ.value("```json\n%s\n```" % J) == OBJ                  # fenced
    assert RJ.value("A short lead-in.\n```json\n%s\n```\n" % J) == OBJ
    assert RJ.value("As the page cites [1] and [2, 4], the answer: %s" % J) == OBJ   # citation markers in the lead-in
    assert RJ.value("[1, 2]", "array") == [1, 2]
    with pytest.raises(RJ.Invalid):
        RJ.value("```json\n%s\n```\nAnd a note after." % J)        # nothing after the fence either
    with pytest.raises(RJ.Invalid):
        RJ.value(J, "array")                                         # the wrong type


def test_every_strict_call_site_uses_the_shared_parser():
    srcs = {"orch/model_steps.py": 'RJ.value(text, "object")', "audit_stage.py": 'RJ.value(text, "object")',
            "ruling.py": 'RJ.ok(text, "object")', "orch/overstatement.py": 'RJ.value(reply, "object")'}
    for f, needle in srcs.items():
        assert needle in (W / f).read_text(encoding="utf-8"), f
    fc = (ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py").read_text(encoding="utf-8")
    assert "v, lead = RJ.parts(reply, kind)" in fc


def test_orchestrator_steps_now_refuse_text_after_the_object():
    from orch import model_steps as M
    assert M.parse_json("Lead.\n%s" % J) == OBJ
    with pytest.raises(M.Malformed):
        M.parse_json("%s\nSome prose after." % J)


def test_the_audit_accepts_04h_and_refuses_trailing_prose():
    import audit_stage as A
    assert A.one_object("Lead-in sentence. %s" % J) == OBJ
    assert A.one_object("%s trailing" % J) is None
