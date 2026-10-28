"""Gate findings on a protected sentence settle as not_ruled_protected.

Post-study, mid-rerun tool fix (2026-10-28). A gate finding whose target is a
protected sentence was routed to a person (ruling.split_protected) and left with
no decision, so "gate findings settled" stopped the preflight on it for good; a
recency finding with one protected body sentence among several could never
settle either. ruling.py gate now records the protected target not_ruled_protected
(as fix 7 closes advocate and omission items) and still rules the finding's other
targets; findings.check accepts not_ruled_protected only while every target it
names is protected.

The issue is test_whatholdsup_recency_routing's synthetic one (two body sentences
resting on S1), with BODY2's binding row marked protected. The model is a stub;
the real rule_gate, _settle_recency, findings.scan and findings.check decide.

COUNTERFACTUAL. Route protected items without recording them (drop the
`for it in person` block) and t_mixed, t_all and t_single go red; settle a
recency finding on its ruled sentences only (no `if not srs` branch) and t_all
goes red; accept not_ruled_protected without checking its targets and
t_targets_must_still_be_protected goes red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import bindings as B                                 # noqa: E402
import ruling as R                                    # noqa: E402
import test_whatholdsup_recency_routing as RR         # noqa: E402
from test_whatholdsup_recency_routing import issue    # noqa: E402,F401  (a fixture)

REJECT = {"ruling": "reject", "text": None, "reason": "Quotation 1 is current.", "quotation": 1}


def _rows(*protected):
    """RR.ROWS keyed as bindings.json keys them (bindings.fingerprint), PROTECTED
    ("b1", "b2") marked "reading"."""
    rows = json.loads(json.dumps(RR.ROWS))
    for k in protected:
        rows[k]["protected"] = "reading"
    return {B.fingerprint(r["sentence"]): r for r in rows.values()}


FP1, FP2 = B.fingerprint(RR.BODY1), B.fingerprint(RR.BODY2)


def _write(d, rows):
    (d / "bindings.json").write_text(json.dumps({"bindings": rows}))


def _row(rows, label):
    return [r for r in rows if r[0] == label][0]


def _gate(issue, report, rows):
    import findings as F
    d, P = issue
    _write(d, rows)
    F.scan("xq", report)
    fake = RR.Fake(REJECT)
    R.rule_gate("xq", fake, P=P, report=report, rows=rows, held=RR.HELD)
    return fake, F.load("xq")["findings"][0], F.check("xq", report)


def test_mixed_recency_finding_rules_the_unprotected_sentence_and_settles(issue):
    import findings as F
    fake, f, rows = _gate(issue, RR.REPORT, _rows("b2"))
    assert len(fake.prompts) == 1 and RR.BODY1 in fake.prompts[0]     # BODY2 never reaches the model
    by_row = {x["row"]: x for x in f["sentence_rulings"]}
    assert by_row[FP2]["decision"] == F.NOT_RULED_PROTECTED and by_row[FP2]["protected"] == "reading"
    assert f["decision"] == "rejected" and f["source_id"] == "S1" and f["quote"]   # ruled normally
    assert f["protected_targets"] == [RR.BODY2]
    assert _row(rows, "gate findings settled")[1] == F.OK
    for_person = (issue[0] / "rulings" / R.FOR_PERSON).read_text()
    assert RR.BODY2 in for_person


def test_all_targets_protected_settles_as_not_ruled_protected(issue):
    import findings as F
    fake, f, rows = _gate(issue, RR.REPORT, _rows("b1", "b2"))
    assert fake.prompts == []
    assert f["decision"] == F.NOT_RULED_PROTECTED
    assert sorted(f["protected_targets"]) == sorted([RR.BODY1, RR.BODY2])
    assert _row(rows, "gate findings settled")[1] == F.OK
    assert _row(rows, "findings settled by a document")[1] == F.OK


def test_single_target_gate_finding_on_a_protected_sentence(issue):
    import findings as F
    report = {"sha256": RR.REPORT["sha256"], "objections": [
        {"severity": "SERIOUS", "class": "fairness", "objection": "o", "quote": RR.BODY2, "fix": ""}]}
    fake, f, rows = _gate(issue, report, _rows("b2"))
    assert fake.prompts == []
    assert f["id"] == "obj-1" and f["decision"] == F.NOT_RULED_PROTECTED
    assert f["protected_targets"] == [RR.BODY2] and f["by"] == R.BY_PROTECTED
    assert _row(rows, "gate findings settled")[1] == F.OK
    assert _row(rows, "findings settled by a document")[1] == F.OK


def test_an_unprotected_single_target_is_still_ruled(issue):
    report = {"sha256": RR.REPORT["sha256"], "objections": [
        {"severity": "SERIOUS", "class": "fairness", "objection": "o", "quote": RR.BODY2, "fix": ""}]}
    fake, f, _rows_ = _gate(issue, report, _rows())
    assert len(fake.prompts) == 1 and f["decision"] == "rejected"


def test_targets_must_still_be_protected(issue):
    import findings as F
    d, _P = issue
    _gate(issue, RR.REPORT, _rows("b1", "b2"))
    _write(d, _rows())                                   # the markers are gone
    rows = F.check("xq", RR.REPORT)
    r = _row(rows, "findings settled by a document")
    assert r[1] == F.BAD and F.NOT_RULED_PROTECTED in r[2]
