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
    # Both findings are on the one sentence: one call, one ruling for both (GAP-019).
    assert len(done) == 2 and len(fake.prompts) == 1
    _no_leaks(fake.prompts)
    for f in F.load("xq")["findings"]:
        assert f["decision"] == "rejected" and f["source_id"] == "S-SECRET-7" and f["quote"] == SPAN
        assert f["by"] == "ruling model claude-opus-5-5" and "_fill_in" not in f
        assert f["ruled_together"] == ["c1", "obj-1"]
    [rec] = _log(d)
    assert rec["by"] == "ruling model claude-opus-5-5" and rec["model"] == "claude-opus-5-5"
    assert rec["at"] and rec["ruling_kind"] == "gate"
    assert rec["prompt_sha256"] == hashlib.sha256((WHU / "audit_prompts" / "rule_group_cite.md").read_bytes()).hexdigest()
    assert tuple(rec["inputs"]) == R.GROUP_FIELDS
    assert [c["finding_id"] for c in rec["covers"]] == ["c1", "obj-1"]


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


# --- changecheck findings and source-advocate objections (2026-10-20) ---------

LEAKS2 = LEAKS + ["LEAK-AGAINST", "LEAK-CCMODEL", "LEAK-PRINCIPAL", "LEAK-LOCATOR", "LEAK-STATE",
                  "LEAK-TITLE", "LEAK-NOTE"]


def _no_leaks2(prompts):
    for p in prompts:
        for leak in LEAKS2:
            assert leak not in p, leak
        assert "S-SECRET" not in p


def test_a_changecheck_finding_is_ruled_with_only_the_allowed_inputs_and_disposed(study, monkeypatch):
    d, P = study
    import changecheck as C
    monkeypatch.setattr(C, "record_path", lambda slug: d / "change-reviews.json")
    page = "<html><body><p>%s</p></body></html>" % SENTENCE
    f = {"sentence": SENTENCE, "kind": "NEW_AND_UNBOUND", "why": "carries 2 and rests on nothing",
         "other": "", "source_id": "S-SECRET-7", "model": "LEAK-CCMODEL"}
    (d / "change-reviews.json").write_text(json.dumps({"reviews": [
        {"sha": C.page_sha(page), "against": "LEAK-AGAINST", "findings": [f, {"sentence": "", "kind": "UNRUN"}]}]}))
    fake = Fake({"ruling": "reject", "text": None, "reason": "Quotation 1 carries the figure."})
    done = R.rule_changecheck("xq", fake, P=P, rows={"k1": ROW}, held=HELD, page_html=page)
    assert len(done) == 1 and len(fake.prompts) == 1            # UNRUN is not ruled
    _no_leaks2(fake.prompts)
    disp = json.loads((d / "change-reviews.json").read_text())["dispositions"]
    assert disp[0]["key"] == C.finding_key(f) and disp[0]["decision"] == "reject"
    assert disp[0]["by"] == "ruling model claude-opus-5-5"
    rec = _log(d)[-1]
    assert rec["ruling_kind"] == "changecheck" and tuple(rec["inputs"]) == R.RULE_FIELDS
    assert rec["prompt_sha256"] == hashlib.sha256((WHU / "audit_prompts" / "rule.md").read_bytes()).hexdigest()
    # A second run rules nothing: the finding is disposed.
    assert R.rule_changecheck("xq", fake, P=P, rows={"k1": ROW}, held=HELD, page_html=page) == []


def _advocate(d, monkeypatch, says):
    import source_advocate as SA
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: d)
    briefs = [{"source": "S-SECRET-7", "title": "LEAK-TITLE", "principal": "LEAK-PRINCIPAL",
               "state": "LEAK-STATE", "mode": "objections", "note": "LEAK-NOTE",
               "objections": [{"severity": "SERIOUS", "claim_quoted": "cut weight by 2 kg",
                               "objection": "The paper says 'reduced', not 'cut'.", "why": "wording",
                               "source_says": says, "locator": "LEAK-LOCATOR"}]}]
    (d / "advocate").mkdir(exist_ok=True)
    (d / "advocate" / "2026-10-21-briefs.json").write_text(json.dumps(briefs))
    SA.write_template("xq", "2026-10-21", briefs)
    return SA, d / "advocate" / "2026-10-21-adjudication.md"


def test_an_advocate_objection_is_ruled_with_only_the_allowed_inputs_and_closed(study, monkeypatch):
    d, P = study
    SA, adj = _advocate(d, monkeypatch, "the intervention reduced weight by 2 kg over 12 weeks compared "
                                        "with control")          # IS in the held text, word for word
    fake = Fake({"ruling": "amend", "text": "The trial found the intervention reduced weight by 2 kg in 12 weeks.",
                 "reason": "Quotation 2 says reduced."})
    done = R.rule_advocate("xq", fake, P=P, rows={"k1": ROW}, held=HELD, case=d)
    assert len(done) == 1
    _no_leaks2(fake.prompts)
    assert "Quotation 2" in fake.prompts[0]                       # the verified advocate quotation
    chunk = [c for c in adj.read_text().split("### ")[1:] if c.startswith("S-SECRET-7-01")][0]
    assert SA._closed("### " + chunk, "objections")
    assert "MERIT:  yes" in chunk and "EFFECT: corrects" in chunk and "reduced weight by 2 kg" in chunk
    assert R.advocate_items("xq", d) == []                        # closed: nothing left to rule
    rec = _log(d)[-1]
    assert rec["ruling_kind"] == "advocate" and rec["by"] == "ruling model claude-opus-5-5"


def test_an_advocate_quotation_not_in_the_held_text_is_not_shown_as_source_text(study, monkeypatch):
    d, P = study
    _advocate(d, monkeypatch, "a sentence the paper does not contain")
    fake = Fake({"ruling": "reject", "text": None, "reason": "Quotation 1 supports the sentence."})
    R.rule_advocate("xq", fake, P=P, rows={"k1": ROW}, held=HELD, case=d)
    assert "a sentence the paper does not contain" not in fake.prompts[0]
    assert "not in the held text" in fake.prompts[0] and "Quotation 2" not in fake.prompts[0]


# --- one extraction for everything a model reads (2026-10-20) -------------------

def test_the_ruling_context_for_s008_shows_u23s_span_whole_where_layout_splices_it():
    """WHU-P02's u23 and S008, only where they exist (private: never committed).
    No source text here: the spans come from the bindings at run time."""
    import audit_stage as AS
    try:
        u = [x for x in AS.units("ultra-processed-foods") if x["id"] == "u23"][0]
    except BaseException:
        pytest.skip("WHU-P02's bindings are not here")
    held = R.held_texts("ultra-processed-foods")
    if "S008" not in held:
        pytest.skip("S008 is not held here")
    quotes = [q for q in R.quotations(u["row"], held) if q[0] == "S008"]
    assert quotes
    p = R.payload(u["sentence"], "k", "r", "", quotes, held)
    import reachability
    old_layout = subprocess_layout = None
    for sid, span in quotes:
        assert AS.norm(span) in AS.norm(p["quoted_source_text"])        # shown whole, in context
        window = p["quoted_source_text"].split("In its document: ...", 1)[1]
        assert len(window) > len(span) + 200                            # real context, not the quote alone
    # and the -layout extraction the model used to be shown splits that span
    import subprocess
    import source_store as store
    rec = (store.held("ultra-processed-foods") or {}).get("S008") or {}
    pdf, exe = store.LIB / (rec.get("file") or ""), store.pdftotext_path()
    if exe and pdf.suffix == ".pdf" and pdf.exists():
        layout = subprocess.run([exe, "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        assert not any(AS.norm(span) in AS.norm(" ".join(layout.split())) for _sid, span in quotes)


def test_no_model_facing_text_is_extracted_with_layout():
    import inspect
    import reachability
    src = inspect.getsource(reachability.held_text)
    assert "-layout" not in src.replace("`pdftotext -layout`", "")
    assert "held_texts(slug)" in inspect.getsource(R.rule_advocate)


# --- GAP-014: a recency study that is not CURRENT is a finding (study issues) ----

REPORT_REC = {"recency": {"studies": [
    {"name": "The trial", "status": "UNKNOWN", "draft_uses": "the 12-week readout",
     "latest_known": "could not establish", "what_changed": None},
    {"name": "Another study", "status": "CURRENT"}]}}


def test_a_recency_study_not_current_is_a_finding_on_every_issue(study):
    d, P = study
    import findings as F
    (d / "issue.json").write_text(json.dumps({"slug": "xq", "study": True}))
    ids = [f["id"] for f in F._opens("xq", REPORT_REC)]
    assert ids == ["rec-1"]
    row = [r for r in F.check("xq", REPORT_REC) if r[0] == "gate findings settled"][0]
    assert row[1] == F.BAD and "rec-1" in row[2]
    (d / "issue.json").write_text(json.dumps({"slug": "xq"}))          # a published issue: the same
    assert [f["id"] for f in F._opens("xq", REPORT_REC)] == ["rec-1"]


def test_a_recency_finding_goes_to_the_ruling_model_with_the_sentence_and_the_bound_passages(study):
    d, P = study
    import findings as F
    (d / "issue.json").write_text(json.dumps({"slug": "xq", "study": True}))
    F.scan("xq", REPORT_REC)
    row = dict(ROW, sentence="The trial showed the intervention cut weight by 2 kg in 12 weeks.")
    fake = Fake({"ruling": "reject", "text": None, "reason": "Quotation 1 is the readout.", "quotation": 1})
    done = R.rule_gate("xq", fake, P=P, report=REPORT_REC, rows={"k1": row}, held=HELD)
    assert len(done) == 1 and done[0]["decision"] == "rejected"
    pr = fake.prompts[0]
    assert "The trial showed the intervention" in pr                   # the sentence
    assert "UNKNOWN" in pr and "the 12-week readout" in pr             # the recency result
    assert "Quotation 1" in pr and "reduced weight by 2 kg" in pr      # the bound passage, in context
    _no_leaks(fake.prompts)


def test_a_dangling_reference_goes_to_the_ruling_model_with_both_sentences(study):
    d, P = study
    old = "In the UPDATE trial, the intervention cut weight by 2 kg in 12 weeks."
    new = "In the trial, the intervention cut weight by 2 kg in 12 weeks."
    later = "The UPDATE authors call the effect modest."
    (d / "rulings").mkdir(exist_ok=True)
    (d / "rulings" / "rulings.jsonl").write_text(json.dumps(
        {"at": "2026-10-21T10:00:00+00:00", "ruling_kind": "conclusion", "ruling": "amend", "text": new,
         "inputs": {"sentence": old}}) + "\n")
    page = "<html><body><p>An opening sentence stands here.</p><p>%s %s</p></body></html>" % (new, later)
    rows = {"k1": dict(ROW, sentence=later)}
    fake = Fake({"ruling": "amend", "text": "Its authors call the effect modest.", "reason": "r"})
    done = R.rule_dangling("xq", fake, P=P, rows=rows, held=HELD, page_html=page, case=d)
    assert [x["term"] for x in done] == ["UPDATE"] and len(fake.prompts) == 1
    assert later in fake.prompts[0] and new in fake.prompts[0]          # both sentences
    assert "reduced weight by 2 kg" in fake.prompts[0]                  # the later sentence's passages
    _no_leaks(fake.prompts)
    rec = _log(d)[-1]
    assert rec["ruling_kind"] == "dangling" and rec["term"] == "UPDATE"
    # ruled once: the same (term, sentence) is not ruled again
    assert R.rule_dangling("xq", fake, P=P, rows=rows, held=HELD, page_html=page, case=d) == []
