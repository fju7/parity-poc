"""Three check fixes from deskilling batch 2 (2026-10-18).

  1  B19 significance qualifier: the evidence says "no significant change" or
     "did not significantly decline"; the sentence says "no change" / "did not
     fall" with no significance word -> WARN "significance qualifier dropped",
     disposable through hedge_dispositions on "significant".
  2  citation furniture: "2025;10(10):896-903", "2025;15(1):6", "2023;30(10):1684"
     are a journal's address, not figures -- for rule 1, B13 and B12. Only that
     shape: a figure after an ordinary semicolon is still a figure.
  3  SSRN's download watermark: removed from SSRN-sourced text before span and
     quotation matching, with an INFO note; never from other text.

Fixtures only. Nothing here reads an issue directory or loads publish.py.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


B = _load("bindings")
FT = _load("figure_text")
SC = _load("spancheck")

# --- 1: B19 significance qualifier ----------------------------------------

S043_SPAN = ("There was no significant change between phases 1 and 3 (31.9% [216/678] "
             "to 36.3% [173/476]; OR 1.03, 95%CI 0.79-1.34).")
S017_SPAN = ("Within the AI-Assisted condition, confidence did not significantly decline as "
             "the number of faulty trials increased (β = -1.14, SE = 0.89, p = 0.202).")


def row(sentence, span, **extra):
    r = {"sentence": sentence, "bucket": "deterministic", "on_page": True,
         "source_id": "S043", "span": span}
    r.update(extra)
    return r


def sig(r):
    return [f for f in B.b19_significance_dropped(dict(r))]


def test_no_change_for_no_significant_change_warns():
    found = sig(row("After the AI was removed it was 36.3% against the 31.9% baseline, "
                    "which is no change.", S043_SPAN))
    assert [f["verdict"] for f in found] == ["significance qualifier dropped"]
    assert B.CALIBRATION_SEVERITY["significance qualifier dropped"] == B.WARN
    assert "'no change'" in found[0]["why"] and "no significant" in found[0]["why"]


def test_did_not_fall_for_did_not_significantly_decline_warns():
    found = sig(row("Their confidence did not fall as they met more wrong answers.", S017_SPAN))
    assert [f["verdict"] for f in found] == ["significance qualifier dropped"]


@pytest.mark.parametrize("sentence", [
    "It was 36.3% against 31.9%, not a statistically significant change.",
    "Their confidence did not fall significantly as they met more wrong answers.",
])
def test_a_sentence_that_keeps_the_qualifier_does_not_warn(sentence):
    assert sig(row(sentence, S043_SPAN + " " + S017_SPAN)) == []


def test_a_sentence_claiming_no_change_against_a_plain_span_does_not_warn():
    assert sig(row("It was 36.3%, which is no change.", "It was 36.3% in phase 3.")) == []


def test_the_disposition_turns_it_into_info():
    d = [{"word": "significant", "why": "reason", "by": "Fred Ugast", "on": "2026-10-18"}]
    found = sig(row("which is no change.", S043_SPAN, hedge_dispositions=d))
    assert [f["verdict"] for f in found] == ["evidence hedge disposed"]
    assert "Fred Ugast" in found[0]["why"]


def test_it_runs_as_part_of_the_calibration_checks():
    verdicts = [f["verdict"] for f in B.calibration_findings(
        row("which is no change.", S043_SPAN), "testissue")]
    assert "significance qualifier dropped" in verdicts


# --- 2: citation furniture ---------------------------------------------------

@pytest.mark.parametrize("cite", ["2025;10(10):896–903", "2025;15(1):6", "2023;30(10):1684",
                                  "2023;30(10):1684–1692", "2025;227:105224", "2020;8:e10325",
                                  "2025;316(1):e243688", "2026;12:100693"])
def test_a_citation_address_is_blanked(cite):
    out = FT.strip_citations("Lancet Gastroenterol Hepatol %s Source of" % cite)
    assert cite not in out and len(out) == len("Lancet Gastroenterol Hepatol %s Source of" % cite)


@pytest.mark.parametrize("text", ["the rate rose 20%; 12.5 percent fell",
                                  "in 2025; 40 of 669 were excluded",
                                  "a ratio of 1.03; 0.79 to 1.34"])
def test_a_figure_after_an_ordinary_semicolon_is_kept(text):
    assert FT.strip_citations(text) == text


def test_rule_1_does_not_claim_citation_pages_as_figures():
    figs = B._claim_figures("Lancet Gastroenterol Hepatol 2025;10(10):896–903 Source of the "
                            "28.4% to 22.4% fall")
    assert not ({"896", "903", "896–903"} & figs)
    assert any(f.startswith("28.4") for f in figs) and any(f.startswith("22.4") for f in figs)


def test_b13_does_not_read_a_citation_address(monkeypatch):
    b13 = _load("b13")
    monkeypatch.setattr(b13.B, "page_sentences",
                        lambda slug: ["Societies 2025;15(1):6 Source of the 666 valid responses of 669."])
    figs = [f for f, _s in b13.figures_on_page("testissue")]
    assert "666" in figs and "669" in figs and "2025" not in figs and "6" not in figs


# --- 3: SSRN watermark ---------------------------------------------------------

SSRN = ("suggesting a er r ev negative impact on endoscopist performance. Key words: colonoscopy, "
        "Pr ep rin tn ot pe deskilling 5 This preprint research paper has not been peer reviewed. "
        "Electronic copy available at: https://ssrn.com/abstract=5070304 iew ed Introduction")


def test_strip_ssrn_removes_the_footer_and_the_watermark():
    out = SC.strip_ssrn(SSRN)
    assert "a negative impact on endoscopist performance" in out
    assert "Electronic copy" not in out and "iew ed" not in out and "Pr ep" not in out


def test_non_ssrn_text_is_left_alone():
    assert SC.strip_ssrn("Electronic copy available at: the publisher's site. er r ev") is None


@pytest.fixture
def held(monkeypatch):
    files = {}
    monkeypatch.setattr(SC, "_text", lambda slug, sid: files.get(sid, (None, None))[1])
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [files[sid]] if sid in files else [])
    monkeypatch.setattr(SC.store, "held", lambda slug: {sid: {"file": f} for sid, (f, _t) in files.items()})
    return files


def test_b2_matches_across_the_watermark_with_an_info_note(held):
    held["S048"] = ("docs/ad/ad9b.pdf", SSRN)
    ok, why = SC.b2_present("a negative impact on endoscopist performance", "t", "S048",
                            trust_canary=False)
    assert ok is True and SC.SSRN_NOTE in why and "INFO" in why


def test_b2_does_not_strip_a_non_ssrn_document(held):
    held["S001"] = ("docs/aa/aaaa.pdf", SSRN.replace("https://ssrn.com/abstract=5070304", "the journal"))
    ok, _why = SC.b2_present("a negative impact on endoscopist performance", "t", "S001",
                             trust_canary=False)
    assert ok is False


def test_a_quotation_matches_across_the_watermark_with_an_info_row(monkeypatch):
    Q = _load("quotations")
    monkeypatch.setitem(sys.modules, "spancheck", SC)
    monkeypatch.setattr(Q, "attestations_on_file", lambda slug, page=None: [])
    monkeypatch.setattr(Q, "_held_ids", lambda slug: {"S048"})
    monkeypatch.setattr(Q, "_sources", lambda slug: {"S048": {"access": {"state": "full_text_held"}}})
    monkeypatch.setattr(Q, "load", lambda slug: {"quotations": [{
        "id": "Q-36", "quote": "a negative impact on endoscopist performance", "source_id": "S048",
        "verbatim": "suggesting a negative impact on endoscopist performance."}]})
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("docs/ad/ad9b.pdf", SSRN)])
    page = "<html><body><p>It found <q>a negative impact on endoscopist performance</q>.</p></body></html>"
    rows = {n: (s, d) for n, s, d in Q.preflight_rows("t", page)}
    assert rows["quotations match the source"][0] == Q.OK
    st, d = rows["quotations matched after removing SSRN's watermark"]
    assert st == Q.OK and d.startswith("INFO") and "Q-36" in d
