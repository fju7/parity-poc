"""Every ruling mode shows each quotation in its context (2026-10-20).

ruling.payload shows each quoted passage with QUOTE_AROUND characters of its
document either side. Until 2026-10-20 the held texts were keyed
"<issue>:<source>" and looked up by bare id, so no context was ever found and
the model saw the quotation alone. This drives every mode -- gate,
conclusions, changecheck, advocate, dangling -- through a fake model and
asserts that every quotation in every prompt arrives with a window of its
document longer than the quotation, containing it.

Self-contained: no other test module is imported.
"""
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

spec = importlib.util.spec_from_file_location("ruling_context_t", WHU / "ruling.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

BEFORE = "Participants were adults recruited from two clinics in the spring. " * 3
AFTER = " Adverse events were rare and similar between groups in both arms. " * 3
SPAN = "the intervention reduced weight by 2 kg over 12 weeks"
ADV = "compared with control, and the effect persisted at follow-up"
DOC = BEFORE + "The randomised trial found that %s %s." % (SPAN, ADV) + AFTER
HELD = {"S7": DOC}
SENTENCE = "The trial showed the intervention cut weight by 2 kg in 12 weeks."
ROW = {"sentence": SENTENCE, "sentence_sha": "k1", "on_page": True, "source_id": "S7", "span": SPAN}
SHOWN = re.compile(r'Quotation (\d+): "(.*?)"\nIn its document: \.\.\.(.*?)\.\.\.(?:\n|$)', re.S)


class Fake:
    def __init__(self, reply):
        self.prompts, self.reply = [], reply

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        return json.dumps(self.reply), {"input": 1, "output": 1, "usd": 0.0}


@pytest.fixture
def study(tmp_path, monkeypatch):
    d = tmp_path / "WHU-P99-xq"
    d.mkdir()
    import source_store
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    return d, types.SimpleNamespace(is_study=lambda slug: slug == "xq")


def _norm(s):
    return " ".join(s.split())


def assert_in_context(prompts, want=1):
    assert prompts, "the ruling model was never called"
    for p in prompts:
        shown = SHOWN.findall(p)
        assert len(shown) >= want, "a quotation is missing from the prompt"
        for n, quote, window in shown:
            import audit_stage as A                       # the audit's own comparison
            assert A.quoted_in(quote, window), "quotation %s is not in its window" % n
            assert len(_norm(window)) > len(_norm(quote)), "quotation %s has no context" % n
            assert len(_norm(window)) > len(_norm(quote)) + 20


def test_gate(study):
    d, P = study
    import findings as F
    F.save("xq", {"findings": [{"id": "obj-1", "kind": "fairness", "gate_verdict": "omission",
                                "gate_said": "overstates", "decision": ""}]})
    report = {"objections": [{"quote": "cut weight by 2 kg", "severity": "SERIOUS"}]}
    fake = Fake({"ruling": "reject", "text": None, "reason": "r", "quotation": 1})
    R.rule_gate("xq", fake, P=P, report=report, rows={"k1": ROW}, held=HELD)
    assert_in_context(fake.prompts)


def test_conclusions(study):
    d, P = study
    import conclusion_judge as CJ
    CJ.save_review("xq", {"sentences": {"k1": {
        "sentence_sha": CJ.fingerprint(SENTENCE), "sentence": SENTENCE, "label": "OVERSTATES",
        "reason": "says showed", "flagged": True, "decision": CJ.empty_decision()}}})
    fake = Fake({"ruling": "reject", "text": None, "reason": "r"})
    R.rule_conclusions("xq", fake, P=P, rows={"k1": ROW}, held=HELD)
    assert_in_context(fake.prompts)


def test_changecheck(study, monkeypatch):
    d, P = study
    import changecheck as C
    monkeypatch.setattr(C, "record_path", lambda slug: d / "change-reviews.json")
    page = "<html><body><p>%s</p></body></html>" % SENTENCE
    f = {"sentence": SENTENCE, "kind": "UNSOURCED", "why": "w", "other": ""}
    (d / "change-reviews.json").write_text(json.dumps({"reviews": [
        {"sha": C.page_sha(page), "against": "x", "findings": [f]}]}))
    fake = Fake({"ruling": "reject", "text": None, "reason": "r"})
    R.rule_changecheck("xq", fake, P=P, rows={"k1": ROW}, held=HELD, page_html=page)
    assert_in_context(fake.prompts)


def test_advocate_the_row_span_and_the_advocates_own_quotation(study, monkeypatch):
    d, P = study
    import source_advocate as SA
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: d)
    briefs = [{"source": "S7", "title": "t", "mode": "objections",
               "objections": [{"severity": "SERIOUS", "claim_quoted": "cut weight by 2 kg",
                               "objection": "o", "why": "w", "source_says": ADV}]}]
    (d / "advocate").mkdir()
    (d / "advocate" / "2026-10-21-briefs.json").write_text(json.dumps(briefs))
    SA.write_template("xq", "2026-10-21", briefs)
    fake = Fake({"ruling": "reject", "text": None, "reason": "r"})
    R.rule_advocate("xq", fake, P=P, rows={"k1": ROW}, held=HELD, case=d)
    assert_in_context(fake.prompts, want=2)                     # the span AND the advocate's quotation


def test_dangling(study):
    d, P = study
    old = "In the UPDATE trial, the intervention cut weight by 2 kg in 12 weeks."
    new = "In the trial, the intervention cut weight by 2 kg in 12 weeks."
    later = "The UPDATE authors call the effect modest."
    (d / "rulings").mkdir()
    (d / "rulings" / "rulings.jsonl").write_text(json.dumps(
        {"at": "2026-10-21T10:00:00+00:00", "ruling_kind": "conclusion", "ruling": "amend",
         "text": new, "inputs": {"sentence": old}}) + "\n")
    page = "<html><body><p>An opening sentence stands here.</p><p>%s %s</p></body></html>" % (new, later)
    fake = Fake({"ruling": "reject", "text": None, "reason": "r"})
    R.rule_dangling("xq", fake, P=P, rows={"k1": dict(ROW, sentence=later)}, held=HELD,
                    page_html=page, case=d)
    assert_in_context(fake.prompts)


def test_a_quotation_whose_line_breaks_differ_from_the_held_text_still_gets_context():
    # The held text is extracted from a PDF and wraps where the bound span does not.
    wrapped = {"S7": DOC.replace("the intervention reduced", "the\nintervention  reduced")}
    p = R.payload(SENTENCE, "k", "r", "", [("S7", SPAN)], wrapped)
    assert_in_context([R.build_prompt("audit", p)])


def test_curly_quotes_dashes_and_enclosing_marks_are_located_too():
    held = {"S7": DOC.replace("2 kg", "2\u00a0kg").replace("over 12", "over\n  12")}
    p = R.payload(SENTENCE, "k", "r", "", [("S7", "\u201c%s\u201d" % SPAN)], held)
    assert_in_context([R.build_prompt("audit", p)])


def test_locate_maps_back_to_the_documents_own_offsets():
    import audit_stage as A
    for hay in (DOC, DOC.replace(" ", "\n "), "\u00c9tude: " + DOC.replace("reduced", "re\u0301duced")):
        for s in (hay, hay.upper()):
            assert A.norm_map(s)[0] == A.norm(s)
    hay = "x " * 50 + "the\nintervention   reduced weight" + " y" * 50
    a, b = A.locate("The intervention reduced weight", hay)
    assert hay[a:b] == "the\nintervention   reduced weight"
    assert A.locate("not there at all", hay) is None


def _p02():
    import bindings as B
    try:
        rows = B.load("ultra-processed-foods").get("bindings") or {}
        held = R.held_texts("ultra-processed-foods")
    except BaseException:
        return None
    return (rows, held) if rows and held else None


def test_every_wHU_P02_bound_quotation_is_shown_in_context():
    """Private files, only where they exist; no source text is committed."""
    got = _p02()
    if not got:
        pytest.skip("WHU-P02's bindings or held documents are not here")
    rows, held = got
    import audit_stage as A
    quotes = [(sid, q) for r in rows.values() if r.get("on_page") for sid, q in R.quotations(r, held)]
    assert quotes
    missing = [(sid, len(q)) for sid, q in quotes if A.locate(q, held.get(sid) or "") is None]
    assert missing == []
    row = rows.get("a211e776da17684b")
    if row:
        qs = [x for x in R.quotations(row, held) if x[0] == "S012"]
        assert qs
        assert_in_context([R.build_prompt("audit", R.payload(row["sentence"], "k", "r", "", qs, held))])
