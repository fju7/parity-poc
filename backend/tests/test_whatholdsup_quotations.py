"""The quotation matcher must catch an altered quotation.

A control nobody has seen fail is a control nobody knows works. The
counterexample hunter was built, wired in, and never once run against the page
it was built for -- it passed every gate by having no input. So this file does
not test that the matcher runs; it tests that it BLOCKS, on each of the four
ways a quotation goes wrong, and that it stays quiet on the one case that looks
like a defect and is not.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "backend" / "scripts" / "whatholdsup" / "quotations.py"

spec = importlib.util.spec_from_file_location("quotations", MOD)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

BLOCKED = "BLOCKED"

PAGE = """<html><body>
<p>The trial report says the
&ldquo;statistical comparison was made by 1-sided stratified log-rank test&rdquo;
and the authors note that
&ldquo;the final analysis was planned after at least 390 events&rdquo;.</p>
<p>Nobody serious argues that &ldquo;palbociclib does not work&rdquo; here.</p>
</body></html>"""


def _case(tmp_path, monkeypatch, quotations, sources=None):
    """Stand a fake issue directory up and point the module at it."""
    case = tmp_path / "WHU-999-testissue"
    case.mkdir()
    (case / "quotations.json").write_text(
        json.dumps({"quotations": quotations}), encoding="utf-8")
    (case / "sources.json").write_text(json.dumps({"sources": sources or [
        {"id": "S001", "title": "Trial report", "access": {"state": "machine_read"}},
    ]}), encoding="utf-8")
    monkeypatch.setattr(q, "CASES", tmp_path)
    return case


def states(rows):
    return {name: state for name, state, _detail in rows}


def test_extracts_only_real_quotations():
    got = q.extract(PAGE)
    assert "statistical comparison was made by 1-sided stratified log-rank test" in got
    assert "palbociclib does not work" in got
    # "and the authors note that" is not quoted; nothing outside the marks.
    assert not any("authors note" in g for g in got)


def test_missing_file_blocks(tmp_path, monkeypatch):
    case = tmp_path / "WHU-999-testissue"
    case.mkdir()
    monkeypatch.setattr(q, "CASES", tmp_path)
    rows = q.preflight_rows("testissue", PAGE)
    assert rows[0][1] == BLOCKED
    assert "no quotations.json" in rows[0][2]


def test_unrecorded_quotation_blocks(tmp_path, monkeypatch):
    """The page quotes something the record does not mention at all."""
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "In this analysis the statistical comparison was made by 1-sided stratified log-rank test."},
    ])
    rows = q.preflight_rows("testissue", PAGE)
    assert states(rows)["every quotation is recorded"] == BLOCKED


def test_altered_quotation_blocks(tmp_path, monkeypatch):
    """THE CASE THIS FILE EXISTS FOR.

    The page says '1-sided'. The source says '2-sided'. Every other word
    matches, the source is real, it was opened, and the quotation is recorded.
    One digit is wrong and it reverses what the trial reported.
    """
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "The statistical comparison was made by 2-sided stratified log-rank test."},
        {"id": "Q-02", "quote": "the final analysis was planned after at least 390 events",
         "source_id": "S001",
         "verbatim": "the final analysis was planned after at least 390 events had occurred"},
        {"id": "Q-03", "quote": "palbociclib does not work",
         "kind": "rhetorical", "why": "our own framing of a position we then reject"},
    ])
    rows = q.preflight_rows("testissue", PAGE)
    st = states(rows)
    assert st["every quotation is recorded"] == "ok"
    assert st["quotations match the source"] == BLOCKED
    detail = [d for n, _s, d in rows if n == "quotations match the source"][0]
    assert "Q-01" in detail


def test_quotation_from_an_unopened_source_blocks(tmp_path, monkeypatch):
    """An accurate quotation from a source nobody opened is still not checked.

    source_ledger's rule, one level down: an unread source is not a source that
    agrees with us. If nobody opened it, the 'verbatim' field is somebody's
    recollection, and comparing a quotation against a recollection is not
    verification.
    """
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "The statistical comparison was made by 1-sided stratified log-rank test."},
        {"id": "Q-02", "quote": "the final analysis was planned after at least 390 events",
         "source_id": "S001",
         "verbatim": "the final analysis was planned after at least 390 events had occurred"},
        {"id": "Q-03", "quote": "palbociclib does not work",
         "kind": "rhetorical", "why": "our own framing"},
    ], sources=[{"id": "S001", "title": "Trial report", "access": {"state": "not_opened"}}])
    rows = q.preflight_rows("testissue", PAGE)
    assert states(rows)["quotation sources were opened"] == BLOCKED


def test_accurate_page_passes(tmp_path, monkeypatch):
    """The one case that must stay quiet.

    A check that fires on a correct page gets switched off, and then it protects
    nothing. Two accurate quotations from an opened source, one declared as the
    page's own voice.
    """
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "In this analysis, the statistical comparison was made by 1-sided "
                     "stratified log-rank test, with the stratification factors as randomised."},
        {"id": "Q-02", "quote": "the final analysis was planned after at least 390 events",
         "source_id": "S001",
         "verbatim": "the final analysis was planned after at least 390 events had occurred"},
        {"id": "Q-03", "quote": "palbociclib does not work",
         "kind": "rhetorical", "why": "our own framing of a position the piece then rejects"},
    ])
    rows = q.preflight_rows("testissue", PAGE)
    assert BLOCKED not in states(rows).values(), rows


def test_curly_and_straight_quotes_are_the_same_quotation(tmp_path, monkeypatch):
    """Punctuation is not identity — the lesson counterexample._key was built on.

    The page renders a curly apostrophe; a passage pasted from a PDF carries a
    straight one. Two of nine claims on issue three were once unmatchable for
    exactly this, so it is asserted here rather than assumed.
    """
    page = "<p>&ldquo;the trial’s final analysis was planned after 390 events&rdquo;</p>"
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "the trial's final analysis was planned after 390 events",
         "source_id": "S001",
         "verbatim": "the trial's final analysis was planned after 390 events had occurred"},
    ])
    rows = q.preflight_rows("testissue", page)
    assert BLOCKED not in states(rows).values(), rows
