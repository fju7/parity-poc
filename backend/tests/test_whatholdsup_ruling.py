"""The ruling model, everywhere the study's protocol assigns it (rev 27).

Gate findings and conclusion-judge flags on a study issue are ruled by the same
ruling model as audit findings and second-reader disagreements. Every ruling's
payload holds only the finding, the sentence and the quoted source text; every
ruling is logged with its time, model, prompt sha256 and inputs, attributed
"ruling model claude-opus-5-5". The forbidden fields below are planted on every
record a payload is built from, and none may reach the model.
"""
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R = _load("ruling_t", WHU / "ruling.py")
A = _load("audit_stage_ruling_t", WHU / "audit_stage.py")

DOC = ("Background text. The randomised trial found that the intervention reduced "
       "weight by 2 kg over 12 weeks compared with control. Further text follows here.")
HELD = {"S-SECRET-7": DOC}
SPAN = "the intervention reduced weight by 2 kg over 12 weeks"
SENTENCE = "The trial showed the intervention cut weight by 2 kg in 12 weeks."
LEAKS = ["LEAK-STEP", "LEAK-FLAG", "LEAK-VERDICT", "LEAK-WHY-BOUND", "S-SECRET-7", "LEAK-URL",
         "LEAK-ATTR", "LEAK-ACTUAL", "LEAK-BY", "LEAK-MODEL", "LEAK-RAW", "LEAK-PREV", "LEAK-SIGNER",
         "LEAK-CLASS", "LEAK-WHY-OBJ"]

ROW = {"sentence": SENTENCE, "sentence_sha": "k1", "on_page": True, "bucket": "judgement",
       "source_id": "S-SECRET-7", "span": SPAN, "premises": [{"source_id": "S-SECRET-7", "span": SPAN}],
       "step": "LEAK-STEP", "check_flags": [{"check": "B19", "why": "LEAK-FLAG"}],
       "verdicts": {"locatable": {"by": "LEAK-SIGNER"}, "faithful": "LEAK-VERDICT"},
       "why_bound": "LEAK-WHY-BOUND", "url": "LEAK-URL", "attested_by": "LEAK-SIGNER"}


class Fake:
    def __init__(self, reply):
        self.prompts, self.reply = [], reply

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        return json.dumps(self.reply), {"input": 10, "output": 5, "usd": 0.0}


@pytest.fixture
def study(tmp_path, monkeypatch):
    d = tmp_path / "WHU-P99-xq"
    d.mkdir()
    import source_store, findings, conclusion_judge
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    P = types.SimpleNamespace(is_study=lambda slug: slug == "xq")
    return d, P


def _no_leaks(prompts):
    for p in prompts:
        for leak in LEAKS:
            assert leak not in p, leak
        assert "S-SECRET" not in p


def _log(d):
    return [json.loads(l) for l in (d / "rulings" / "rulings.jsonl").read_text().splitlines()]


def test_the_payload_is_the_allow_list_and_nothing_else():
    p = R.payload(SENTENCE, "k", "r", "", R.quotations(ROW, HELD), HELD)
    assert tuple(p) == R.RULE_FIELDS
    assert "Quotation 1" in p["quoted_source_text"] and "S-SECRET" not in json.dumps(p)


def test_a_gate_finding_is_ruled_with_only_the_allowed_inputs_and_recorded(study):
    d, P = study
    import findings as F
    report = {"claims": [{"id": "c1", "claim": SENTENCE, "attributed_to": "LEAK-ATTR"}],
              "verdicts": {"c1": {"id": "c1", "verdict": "NOT_FOUND", "found_value": "no 2 kg figure",
                                  "actual_source": "LEAK-ACTUAL"}},
              "objections": [{"quote": "cut weight by 2 kg", "objection": "overstates", "severity": "SERIOUS",
                              "class": "LEAK-CLASS", "why": "LEAK-WHY-OBJ", "fix": "A narrower sentence."}]}
    F.save("xq", {"findings": [
        {"id": "c1", "kind": "claim", "gate_verdict": "NOT_FOUND", "gate_said": "no 2 kg figure",
         "decision": "", "by": "LEAK-BY", "_fill_in": "x"},
        # gate_verdict IS the finding (its verdict or class) and is sent as its kind;
        # the report's own "class" field below is not, and must not arrive.
        {"id": "obj-1", "kind": "fairness", "gate_verdict": "omission", "gate_said": "overstates",
         "decision": ""}]})
    fake = Fake({"ruling": "reject", "text": None, "reason": "Quotation 1 says 2 kg.", "quotation": 1})
    done = R.rule_gate("xq", fake, P=P, report=report, rows={"k1": ROW}, held=HELD)
    assert len(done) == 2 and len(fake.prompts) == 2
    _no_leaks(fake.prompts)
    for f in F.load("xq")["findings"]:
        assert f["decision"] == "rejected" and f["source_id"] == "S-SECRET-7" and f["quote"] == SPAN
        assert f["by"] == "ruling model claude-opus-5-5" and "_fill_in" not in f
    for rec in _log(d):
        assert rec["by"] == "ruling model claude-opus-5-5" and rec["model"] == "claude-opus-5-5"
        assert rec["at"] and rec["ruling_kind"] == "gate"
        assert rec["prompt_sha256"] == hashlib.sha256((WHU / "audit_prompts" / "rule_cite.md").read_bytes()).hexdigest()
        assert tuple(rec["inputs"]) == R.RULE_FIELDS


def test_a_gate_ruling_that_cites_no_quotation_is_a_judgement(study):
    d, P = study
    import findings as F
    F.save("xq", {"findings": [{"id": "obj-1", "kind": "fairness", "gate_said": "x", "decision": ""}]})
    report = {"objections": [{"quote": "cut weight by 2 kg", "severity": "SERIOUS"}]}
    R.rule_gate("xq", Fake({"ruling": "reject", "text": None, "reason": "r", "quotation": None}),
                P=P, report=report, rows={"k1": ROW}, held=HELD)
    assert F.load("xq")["findings"][0]["decision"] == "judgement"


def test_a_conclusion_flag_is_ruled_and_decided_by_the_ruling_model(study):
    d, P = study
    import conclusion_judge as CJ
    sha = CJ.fingerprint(SENTENCE)
    CJ.save_review("xq", {"sentences": {"k1": {
        "sentence_sha": sha, "sentence": SENTENCE, "label": "OVERSTATES", "reason": "says showed",
        "model": "LEAK-MODEL", "raw": "LEAK-RAW", "flagged": True,
        "decision": CJ.empty_decision(), "previous": [{"decision": {"why": "LEAK-PREV"}}]}}})
    fake = Fake({"ruling": "amend", "text": "The trial found the intervention cut weight by 2 kg in 12 weeks.",
                 "reason": "Quotation 1 says found, not showed."})
    R.rule_conclusions("xq", fake, P=P, rows={"k1": ROW}, held=HELD)
    _no_leaks(fake.prompts)
    e = CJ.load_review("xq")["sentences"]["k1"]
    assert CJ.decided(e) and e["decision"]["decision"] == "accepted"
    assert e["decision"]["by"] == "ruling model claude-opus-5-5" and "New text" in e["decision"]["why"]
    rec = _log(d)[0]
    assert rec["ruling_kind"] == "conclusion" and rec["prompt_sha256"] == \
        hashlib.sha256((WHU / "audit_prompts" / "rule.md").read_bytes()).hexdigest()


def test_a_published_issue_is_refused(study):
    _d, P = study
    with pytest.raises(SystemExit):
        R.rule_gate("melanoma", Fake({}), P=P, report={}, rows={}, held={})
    with pytest.raises(SystemExit):
        R.rule_conclusions("melanoma", Fake({}), P=P, rows={}, held={})


def test_an_unusable_reply_stops_and_records_nothing(study):
    d, P = study
    import findings as F
    F.save("xq", {"findings": [{"id": "obj-1", "kind": "fairness", "gate_said": "x", "decision": ""}]})
    with pytest.raises(R.RulingError):
        R.rule_gate("xq", Fake({"ruling": "maybe"}), P=P,
                    report={"objections": [{"quote": "cut weight", "severity": "SERIOUS"}]},
                    rows={"k1": ROW}, held=HELD)
    assert F.load("xq")["findings"][0]["decision"] == ""


def test_audit_rulings_are_logged_with_time_model_prompt_sha_and_inputs(tmp_path):
    # The audit stage's own rulings (findings and second-reader disagreements).
    T = _load("audit_test_mod_ruling_t", ROOT / "backend" / "tests" / "test_whatholdsup_audit_stage.py")
    u = T._unit("u1", "The study proves that AI deskills doctors.")
    m = A.run("demo", out_dir=tmp_path, ask=T.FakeModel(always_finding=True), held=T.HELD,
              unit_list=[u], cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    recs = [json.loads(l) for l in (tmp_path / "rulings.jsonl").read_text().splitlines()]
    assert recs
    for r in recs:
        assert r["at"] and r["by"] == "ruling model claude-opus-5-5" and r["model"] == "claude-opus-5-5"
        assert r["prompt_sha256"] == hashlib.sha256((WHU / "audit_prompts" / "rule.md").read_bytes()).hexdigest()
        assert tuple(r["inputs"]) == A.RULE_FIELDS
