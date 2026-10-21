"""One ruling per sentence (GAP-019, 2026-10-21).

On WHU-P02 two advocate objections on one sentence (S005-11 and S005-12) were
ruled in separate calls and could come back with two different texts for the
one sentence. Now every ruling.py mode groups its findings by the sentence they
target and sends them in one call, which returns one decision and one text;
every finding is recorded with it, the log says which findings the ruling
covers, and applied_check expects that one text. No model is called.
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


R = _load("ruling_group_t", WHU / "ruling.py")

DOC = ("Background text. The randomised trial found that the intervention reduced "
       "weight by 2 kg over 12 weeks compared with control. Further text follows here.")
HELD = {"S5": DOC}
SPAN = "the intervention reduced weight by 2 kg over 12 weeks"
SENTENCE = "The trial showed the intervention cut weight by 2 kg in 12 weeks."
OTHER = "A second sentence about something else entirely, at some length."
ROW = {"sentence": SENTENCE, "on_page": True, "source_id": "S5", "span": SPAN}
ROW2 = {"sentence": OTHER, "on_page": True, "source_id": "S5", "span": "Further text follows here"}
TEXT = "The trial found the intervention reduced weight by 2 kg over 12 weeks."


class Fake:
    def __init__(self, reply):
        self.prompts, self.reply = [], reply

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        r = self.reply(len(self.prompts)) if callable(self.reply) else self.reply
        return json.dumps(r), {"input": 10, "output": 5, "usd": 0.0}


@pytest.fixture
def study(tmp_path, monkeypatch):
    d = tmp_path / "WHU-P99-xq"
    d.mkdir()
    import source_store, source_advocate
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    monkeypatch.setattr(source_advocate.sl, "case_dir", lambda slug: d)
    return d, types.SimpleNamespace(is_study=lambda slug: slug == "xq")


def _log(d):
    return [json.loads(l) for l in (d / "rulings" / "rulings.jsonl").read_text().splitlines()]


def _page(*sentences):
    return "<html><body><p>%s</p></body></html>" % " ".join(sentences)


def _advocate(d, objections):
    import source_advocate as SA
    briefs = [{"source": "S5", "title": "T", "principal": "p", "state": "machine-readable",
               "mode": "objections", "objections": objections}]
    (d / "advocate").mkdir(exist_ok=True)
    (d / "advocate" / "2026-10-21-briefs.json").write_text(json.dumps(briefs))
    SA.write_template("xq", "2026-10-21", briefs)
    return SA, d / "advocate" / "2026-10-21-adjudication.md"


TWO_ON_ONE = [
    {"severity": "SERIOUS", "claim_quoted": "cut weight by 2 kg", "objection": "The paper says 'reduced', not 'cut'.",
     "why": "wording", "source_says": "the intervention reduced weight by 2 kg"},
    {"severity": "MINOR", "claim_quoted": "in 12 weeks", "objection": "The paper says 'over 12 weeks'.",
     "why": "duration", "source_says": "over 12 weeks compared with control"}]


def test_two_findings_on_one_sentence_are_one_call_and_one_text(study):
    d, P = study
    SA, adj = _advocate(d, TWO_ON_ONE)
    fake = Fake({"ruling": "amend", "text": TEXT, "reason": "1 right, 2 right: Quotation 1 says reduced, over."})
    done = R.rule_advocate("xq", fake, P=P, rows={"k1": ROW}, held=HELD, case=d)
    assert len(fake.prompts) == 1 and len(done) == 2
    pr = fake.prompts[0]
    assert "Finding 1" in pr and "Finding 2" in pr                        # every finding listed
    assert "'reduced', not 'cut'" in pr and "'over 12 weeks'" in pr
    assert "Quotations it rests on: 1, 2" in pr and "Quotations it rests on: 1, 3" in pr
    assert pr.count("Quotation 1:") == 1                                  # the shared span shown once
    assert "S5" not in pr                                                 # no source id travels
    assert "one text of that sentence" in pr
    # one record, saying which findings it covers
    [rec] = _log(d)
    assert tuple(rec["inputs"]) == R.GROUP_FIELDS and rec["text"] == TEXT
    assert [c["advocate_item"] for c in rec["covers"]] == ["S5-01", "S5-02"]
    assert rec["prompt"] == "audit_prompts/rule_group.md"
    assert rec["prompt_sha256"] == R.GROUP_PROMPT_SHA256["rule_group.md"]
    # both items closed with the same text
    text = adj.read_text()
    for head in ("S5-01", "S5-02"):
        chunk = [c for c in text.split("### ")[1:] if c.startswith(head)][0]
        assert SA._closed("### " + chunk, "objections")
        assert json.dumps(TEXT) in chunk and "together with every finding on this sentence (S5-01, S5-02)" in chunk
    assert R.advocate_items("xq", d) == []


def test_applied_check_expects_that_one_text(study):
    d, P = study
    _advocate(d, TWO_ON_ONE)
    R.rule_advocate("xq", Fake({"ruling": "amend", "text": TEXT, "reason": "r"}), P=P,
                    rows={"k1": ROW}, held=HELD, case=d)
    import applied_check as AC
    ok = AC.check(d, _page(TEXT, OTHER))
    assert len(ok["checked"]) == 1 and ok["mismatches"] == []
    assert ok["checked"][0]["expected"] == [TEXT]
    bad = AC.check(d, _page("The trial found the intervention reduced weight by 2 kg in 12 weeks.", OTHER))
    assert len(bad["mismatches"]) == 1 and bad["mismatches"][0]["missing"] == [TEXT]


def test_findings_on_different_sentences_are_separate_calls_with_the_unchanged_prompt(study):
    d, P = study
    _advocate(d, [TWO_ON_ONE[0], dict(TWO_ON_ONE[1], claim_quoted="something else entirely")])
    fake = Fake({"ruling": "reject", "text": None, "reason": "r"})
    R.rule_advocate("xq", fake, P=P, rows={"k1": ROW, "k2": ROW2}, held=HELD, case=d)
    assert len(fake.prompts) == 2
    recs = _log(d)
    assert [r["row"] for r in recs] == ["k1", "k2"]
    for r in recs:
        assert tuple(r["inputs"]) == R.RULE_FIELDS and r["prompt"] == "audit_prompts/rule.md"
        assert r["prompt_sha256"] == hashlib.sha256((WHU / "audit_prompts" / "rule.md").read_bytes()).hexdigest()
        assert len(r["covers"]) == 1


def test_a_gate_group_cites_a_quotation_numbered_across_the_group(study):
    d, P = study
    import findings as F
    F.save("xq", {"findings": [
        {"id": "obj-1", "kind": "fairness", "gate_verdict": "omission", "gate_said": "overstates", "decision": ""},
        {"id": "obj-2", "kind": "fairness", "gate_verdict": "overreach", "gate_said": "says showed", "decision": ""}]})
    report = {"objections": [{"quote": "cut weight by 2 kg", "fix": "A."}, {"quote": "in 12 weeks", "fix": "B."}]}
    fake = Fake({"ruling": "amend", "text": TEXT, "reason": "Quotation 1.", "quotation": 1})
    R.rule_gate("xq", fake, P=P, report=report, rows={"k1": ROW}, held=HELD)
    assert len(fake.prompts) == 1 and "Reader's proposed text: A." in fake.prompts[0] \
        and "Reader's proposed text: B." in fake.prompts[0]
    fs = F.load("xq")["findings"]
    assert {f["decision"] for f in fs} == {"accepted"} and {f["ruling_text"] for f in fs} == {TEXT}
    assert all(f["source_id"] == "S5" and f["quote"] == SPAN for f in fs)
    assert all(f["ruled_together"] == ["obj-1", "obj-2"] for f in fs)
    assert _log(d)[0]["prompt_sha256"] == R.GROUP_PROMPT_SHA256["rule_group_cite.md"]
    with pytest.raises(R.RulingError):                                   # quotation 9 of 1
        F.save("xq", {"findings": [dict(f, decision="") for f in fs]})
        R.rule_gate("xq", Fake({"ruling": "reject", "text": None, "reason": "r", "quotation": 9}),
                    P=P, report=report, rows={"k1": ROW}, held=HELD)


def test_two_changecheck_findings_on_one_sentence_are_one_disposition_text(study, monkeypatch):
    d, P = study
    import changecheck as C
    monkeypatch.setattr(C, "record_path", lambda slug: d / "change-reviews.json")
    page = _page(SENTENCE)
    fs = [{"sentence": SENTENCE, "kind": "NEW_AND_UNBOUND", "why": "a", "other": ""},
          {"sentence": SENTENCE, "kind": "CHANGED_MEANING", "why": "b", "other": "the old one"}]
    (d / "change-reviews.json").write_text(json.dumps({"reviews": [{"sha": C.page_sha(page), "findings": fs}]}))
    fake = Fake({"ruling": "amend", "text": TEXT, "reason": "r"})
    done = R.rule_changecheck("xq", fake, P=P, rows={"k1": ROW}, held=HELD, page_html=page)
    assert len(fake.prompts) == 1 and len(done) == 2
    assert {x["ruling_text"] for x in done} == {TEXT} and all(len(x["ruled_together"]) == 2 for x in done)
    assert R.rule_changecheck("xq", fake, P=P, rows={"k1": ROW}, held=HELD, page_html=page) == []


def test_two_dangling_terms_in_one_sentence_are_one_call_and_not_ruled_again(study):
    d, P = study
    old = "In the UPDATE trial by Hall, the intervention cut weight by 2 kg in 12 weeks."
    new = "In the trial, the intervention cut weight by 2 kg in 12 weeks."
    later = "The UPDATE authors and Hall call the effect modest."
    (d / "rulings").mkdir(exist_ok=True)
    (d / "rulings" / "rulings.jsonl").write_text(json.dumps(
        {"at": "2026-10-21T10:00:00+00:00", "ruling_kind": "conclusion", "ruling": "amend", "text": new,
         "inputs": {"sentence": old}}) + "\n")
    page = "<html><body><p>An opening sentence stands here.</p><p>%s %s</p></body></html>" % (new, later)
    fake = Fake({"ruling": "amend", "text": "Its authors call the effect modest.", "reason": "r"})
    done = R.rule_dangling("xq", fake, P=P, rows={"k1": dict(ROW, sentence=later)}, held=HELD,
                           page_html=page, case=d)
    assert sorted(x["term"] for x in done) == ["Hall", "UPDATE"] and len(fake.prompts) == 1
    assert sorted(c["term"] for c in _log(d)[-1]["covers"]) == ["Hall", "UPDATE"]
    assert R.rule_dangling("xq", fake, P=P, rows={"k1": dict(ROW, sentence=later)}, held=HELD,
                           page_html=page, case=d) == []


def test_the_stage_cap_counts_one_unit_per_sentence(study, monkeypatch):
    d, P = study
    _advocate(d, TWO_ON_ONE + [dict(TWO_ON_ONE[1], claim_quoted="something else entirely")])
    import bindings as B
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": {"k1": ROW, "k2": ROW2}})
    assert R.pending("advocate", "xq", P=P) == 2                          # three objections, two sentences


def test_the_group_prompts_are_frozen_by_sha256():
    for name, want in R.GROUP_PROMPT_SHA256.items():
        assert hashlib.sha256((WHU / "audit_prompts" / name).read_bytes()).hexdigest() == want, name
    group = (WHU / "audit_prompts" / "rule_group.md").read_text()
    for f in R.GROUP_FIELDS:
        assert "{%s}" % f in group
    # the gate's variant is the same prompt plus the one "quotation" field
    cite = (WHU / "audit_prompts" / "rule_group_cite.md").read_text()
    assert cite.replace(', "quotation": <the number of the quotation your reason chiefly cites, '
                        'or null if none does>', "") == group
