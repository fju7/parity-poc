"""The readers' list: a standard phrase for a located reason; the quotation from the span.

Post-study, mid-rerun tool fix (2026-10-28). On WHU-S01r a ruling's reason quoted
the source, omissions.redact replaced the quotation with its location
("[S003@120-260]"), and the readers' list printed the location to readers. With
no reason_for_reader, a reason carrying a location tag now gives the outcome's
standard phrase ("Judged outside this question" / "Judged not material"; a
not_added_cap line names its cap as before). The quotation always comes from the
finding's own source span, cut at 25 words with a trailing "…", never from the
reason. The line stays one sentence and its quotation passes quotations.py.

The records are written by the real omissions.record (which redacts the reason
against the held text) and coverage_check.declare; the lines by the real
coverage_check.declarations; the quotation is read back by the real
quotations.extract and checked with quotations.quoted_in.

COUNTERFACTUAL. Drop the tag test in line_reason (return the text) and
t_located_reason goes red; put back the first-sentence short_span (a cut with no
ellipsis) and t_two_sentences goes red; drop the cut-at-the-full-stop step in
declaration_sentence and t_two_sentences goes red.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import coverage_check as C    # noqa: E402
import omissions as O         # noqa: E402
import quotations as Q        # noqa: E402
import source_ledger as L     # noqa: E402

LONG = ("Investment in public transport can further support a shift to less intensive modes in large "
        "cities, where most daily trips are short and frequent services can replace private cars for "
        "commuting and errands alike (high confidence).")                              # 37 words, one sentence
TWO = ("Some changes could lead to induced demand in growing suburbs (medium confidence). "
       "The effect is smaller where pricing is in place.")
TEXT = "Section 1. Preamble text here. " + LONG + " " + TWO + " Closing text."
HELD = {"S003": TEXT}
REASON_QUOTING = ("Step 1: in scope. The finding says investment in public transport can further support "
                  "a shift to less intensive modes, which concerns transit, not layout.")


def _f(span):
    a = TEXT.index(span)
    return {"source": "S003", "at": [a, a + len(span)], "held_quote": span, "origin": "S003-01"}


@pytest.fixture
def case(tmp_path, monkeypatch):
    import source_store
    monkeypatch.setattr(source_store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S003", "title": "WGII Chapter 6"}])
    return tmp_path


def _line(case):
    [d] = C.declarations("x", HELD, case)
    return d["sentence"]


def _quotation_passes(line, span):
    [q] = Q.extract(line)
    assert Q.quoted_in(Q.norm(q), Q.norm(TEXT)) and Q.quoted_in(Q.norm(q), Q.norm(span))
    assert len(L.sentences(line)) == 1
    return q


@pytest.mark.parametrize("outcome,phrase", [(O.OUT_OF_SCOPE, "Judged outside this question"),
                                            (O.NOT_MATERIAL, "Judged not material")])
def test_located_reason_gives_the_standard_phrase(case, outcome, phrase):
    e = O.record(case, _f(LONG), outcome=outcome, reason=REASON_QUOTING, by="p", held_text=TEXT,
                 element="layout and pricing")
    assert "[S003@" in e["reason"]                     # the real redaction put a location in it
    line = _line(case)
    assert line.endswith("; %s." % phrase) and "[S003@" not in line and "transit" not in line
    _quotation_passes(line, LONG)


def test_reason_for_reader_is_used_even_when_the_reason_is_located(case):
    O.record(case, _f(LONG), outcome=O.NOT_MATERIAL, reason=REASON_QUOTING, by="p", held_text=TEXT,
             reason_for_reader="the page already reports this")
    assert _line(case).endswith("; the page already reports this.")


def test_unlocated_reason_is_unchanged(case):
    O.record(case, _f(LONG), outcome=O.NOT_MATERIAL, reason="It concerns transit, not layout.", by="p",
             held_text=TEXT)
    assert _line(case).endswith("; It concerns transit, not layout.")


def test_not_added_cap_keeps_its_cap_phrase(case):
    O.record(case, _f(LONG), outcome=O.NOT_ADDED_CAP, reason="Over the additions budget. " + REASON_QUOTING,
             by="p", held_text=TEXT)
    assert _line(case).endswith("; the page's limit for additions was reached.")


def test_quotation_is_the_span_cut_at_25_words(case):
    C.declare("x", "S003@%d-%d" % tuple(_f(LONG)["at"]), "not_material", "[S003@1-2] says so", "p", case=case)
    line = _line(case)
    q = _quotation_passes(line, LONG)
    assert q == " ".join(LONG.split()[:25]) + " …"
    assert line.endswith("; Judged not material.")


def test_two_sentences_keep_the_first_whole_and_say_they_were_cut(case):
    C.declare("x", "S003@%d-%d" % tuple(_f(TWO)["at"]), "out_of_scope", "about suburbs", "p",
              element="layout and pricing", case=case)
    q = _quotation_passes(_line(case), TWO)
    assert q == "Some changes could lead to induced demand in growing suburbs (medium confidence) …"
