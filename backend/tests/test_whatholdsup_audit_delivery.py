"""The audit's empty-document defect (WHU-P02 practice run, 2026-10-20).

trim() returned "" when the windows around a long text's terms merged past
MAX_DOC_CHARS, so the reader was shown an empty document, called it unheld, and
the ruling model cut the sentence. Now trim() is never empty for a non-empty
text; every batch is checked before any call (held and delivered characters,
every bound span inside what was delivered) and stops with
DOCUMENT_NOT_DELIVERED otherwise; and a finding that says its document was
empty or unavailable never reaches the ruling model.
"""
import importlib.util
import json
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
spec = importlib.util.spec_from_file_location("audit_stage_delivery_t", WHU / "audit_stage.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
spec = importlib.util.spec_from_file_location("audit_test_fixtures_t", Path(__file__).parent / "test_whatholdsup_audit_stage.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

SPAN = "226 detected an adenoma (28.4%)"


def _long_text(n=159_009):
    """Terms every ~2,000 characters across the whole text: every window merges
    into one run far past MAX_DOC_CHARS -- the shape that returned ""."""
    para = ("Endoscopists reviewed colonoscopies and recorded adenoma detection in the registry. "
            "Filler sentence about procedures and scheduling follows here. ") * 13
    out, i = [], 0
    while sum(map(len, out)) < n:
        out.append(para)
        if i == 40:
            out.append(" Of 795 colonoscopies before AI was introduced, %s. " % SPAN)
        i += 1
    return "".join(out)[:n]


# --- 1. trim -------------------------------------------------------------------

def test_a_long_text_whose_windows_merge_past_the_limit_is_never_empty():
    text = _long_text()
    assert len(text) == 159_009
    out, cut = A.trim(text, ["adenoma", "colonoscopies", SPAN[:60]], [SPAN[:60]])
    assert cut and 0 < len(out) <= A.MAX_DOC_CHARS
    assert SPAN in out and "adenoma" in out and "colonoscopies" in out


def test_without_a_bound_span_the_cut_is_centred_on_the_terms():
    text = "x" * 100_000 + " adenoma detection " * 20 + "y" * 100_000
    out, _ = A.trim(text, ["adenoma"])
    assert 0 < len(out) <= A.MAX_DOC_CHARS and "adenoma" in out


def test_a_long_text_with_no_hit_keeps_its_opening_not_nothing():
    out, cut = A.trim("z" * 200_000, ["adenoma"])
    assert cut and len(out) == A.MAX_DOC_CHARS


def test_short_texts_pass_through_unchanged():
    assert A.trim(T.DOC, ["adenoma"]) == (T.DOC, False)
    assert A.trim("", ["x"]) == ("", False)


# --- 2. fail closed before any call ---------------------------------------------

def _run(tmp_path, fake, **kw):
    u = T._unit("u1", "The study found 226 of 795 detected an adenoma (28.4%).")
    return A.run("demo", out_dir=tmp_path, ask=fake, held=kw.pop("held", T.HELD), unit_list=[u], cap=1.0,
                 licensed=set(), **kw)


def test_a_planted_empty_delivery_stops_the_run_before_any_paid_call(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "trim", lambda text, wanted, must=(): ("", True))
    fake = T.FakeModel()
    m = _run(tmp_path, fake)
    assert fake.prompts == []                                     # no reader, no ruling
    assert m["status"] == "failed" and m["failure"].startswith("DOCUMENT_NOT_DELIVERED")
    d = m["deliveries"][0]
    assert d["source"] == "S021" and d["held_chars"] == len(T.DOC) and d["delivered_chars"] == 0
    assert json.loads((tmp_path / "manifest.json").read_text())["deliveries"][0]["delivered_chars"] == 0


def test_a_bound_span_missing_from_the_delivery_stops_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "trim", lambda text, wanted, must=(): ("The study is retrospective.", True))
    fake = T.FakeModel()
    m = _run(tmp_path, fake)
    assert fake.prompts == [] and m["failure"].startswith("DOCUMENT_NOT_DELIVERED")
    assert m["deliveries"][0]["spans_inside"] is False


def test_a_good_delivery_is_recorded_and_the_run_proceeds(tmp_path):
    fake = T.FakeModel(always_finding=False)
    m = _run(tmp_path, fake)
    assert m["status"] == "complete", m.get("failure")
    d = m["deliveries"][0]
    assert d["delivered_chars"] == d["held_chars"] == len(T.DOC) and d["spans_inside"] is True


# --- 3. ruling isolation ----------------------------------------------------------

class SaysEmpty(T.FakeModel):
    """A reader that reports its document as empty."""

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        if "THE SENTENCES TO READ" in prompt:
            import re
            ids = re.findall(r"^\[(u\d+)\]", prompt, re.M)
            out = {"verdicts": [{"id": i, "verdict": "finding", "kind": "Rested on a document we do not hold",
                                 "evidence": [], "proposed_text": "",
                                 "reason": "The document provided for S021 is empty, so nothing supports it."}
                                for i in ids]}
            return json.dumps(out), {"input": 1, "output": 1, "usd": 0.0}
        raise AssertionError("the ruling model was called")


def test_a_finding_that_says_its_document_was_empty_never_reaches_the_ruling_model(tmp_path):
    fake = SaysEmpty()
    m = _run(tmp_path, fake)
    assert m["status"] == "failed" and m["failure"].startswith("DOCUMENT_NOT_DELIVERED")
    assert not any("THE FINDING:" in p for p in fake.prompts)


@pytest.mark.parametrize("reason,hit", [
    ("The document provided is empty.", True),
    ("The source text was not provided.", True),
    ("Could not read the document.", True),
    ("The paper reports 22.4%, not 28.4%.", False),
    ("Overstates: the authors say the study is vulnerable to confounding.", False),
])
def test_what_counts_as_saying_a_document_was_missing(reason, hit):
    assert A.says_document_missing({"kind": "Overstated", "reason": reason}) is hit


# --- the reader is shown the text the bindings were checked against (2026-10-20) ---

def test_a_bound_span_absent_from_the_held_text_stops_the_run(tmp_path):
    # The binding was checked against one extraction and the reader would be
    # shown another that lacks the span: fail closed, before any call.
    held = {"demo:S021": T.DOC.replace("226 detected an adenoma (28.4%)", "226 de- tected an adenoma (28.4%)")}
    fake = T.FakeModel()
    m = _run(tmp_path, fake, held=held)
    assert fake.prompts == [] and m["failure"].startswith("DOCUMENT_NOT_DELIVERED")
    assert m["deliveries"][0]["spans_inside"] is False


def test_the_audit_reads_the_extraction_the_binding_checks_use(monkeypatch):
    import source_store
    import spancheck
    monkeypatch.setattr(source_store, "held", lambda slug: {"S1": {}, "S2": {}})
    monkeypatch.setattr(spancheck, "_text", lambda slug, sid: {"S1": "reading-order text"}.get(sid))
    assert A.held_for_audit("demo") == {"S1": "reading-order text"}


def _p02_case():
    """WHU-P02's u23/u41 and S008, only where they exist (held documents and a
    study issue's bindings are private and never committed)."""
    try:
        us = [u for u in A.units("ultra-processed-foods") if u["id"] in ("u23", "u41")]
    except BaseException:
        return None
    spans = [x["span"] for u in us for x in [u["row"] or {}] + ((u["row"] or {}).get("also_rests_on") or [])
             + ((u["row"] or {}).get("premises") or []) if x.get("source_id") == "S008" and x.get("span")]
    return spans or None


def test_the_real_case_s008_spans_are_in_the_audit_text_and_not_in_the_layout_text():
    spans = _p02_case()
    if not spans:
        pytest.skip("WHU-P02's bindings or S008 are not held here")
    import subprocess
    import source_store as store
    audit = A.held_for_audit("ultra-processed-foods").get("S008") or ""
    assert audit and all(A.norm(s) in A.norm(audit) for s in spans)        # the fix
    # the defect: `pdftotext -layout`, which nothing a model reads uses any more
    rec = (store.held("ultra-processed-foods") or {}).get("S008") or {}
    pdf, exe = store.LIB / (rec.get("file") or ""), store.pdftotext_path()
    if exe and pdf.suffix == ".pdf" and pdf.exists():
        layout = " ".join(subprocess.run([exe, "-layout", str(pdf), "-"], capture_output=True,
                                         text=True).stdout.split())
        assert not any(A.norm(s) in A.norm(layout) for s in spans)
