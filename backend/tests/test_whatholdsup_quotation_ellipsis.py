"""quotations: a quotation with an ellipsis is the source's words if every
segment between the ellipses is in the held source verbatim, in order.

Post-study, mid-rerun tool fix (2026-10-28). WHU-S01r and WHU-S07r quoted with
"…" and "..." and the matcher called every such quotation altered: it asked
whether the whole string, ellipsis included, was in the source.

The fakes stand in for storage only (which sources are held, and their text);
preflight_rows runs whole, so the real norm(), the real comparison against the
recorded verbatim and the real comparison against the held bytes all apply.

COUNTERFACTUAL. Replace quoted_in's body with `return quote in body` and the
two passing cases go red; drop the in-order cursor (`at = i + len(s)` -> keep
`at = 0`) and t_out_of_order goes red.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import quotations as Q        # noqa: E402
import spancheck as SC        # noqa: E402

SOURCE = ("Across the 14 cohorts, the effect of the intervention was large in adults "
          "over 40. It was small in children under five, and absent in infants. "
          "Confidence in the adult estimate is high.")


def _case(tmp_path, monkeypatch, quote, verbatim=SOURCE, source=SOURCE):
    case = tmp_path / "WHU-999-testissue"
    case.mkdir()
    (case / "quotations.json").write_text(json.dumps({"quotations": [
        {"id": "Q-01", "quote": quote, "source_id": "S001", "verbatim": verbatim}]}),
        encoding="utf-8")
    (case / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "title": "Review", "access": {"state": "full_text_held"}}]}),
        encoding="utf-8")
    monkeypatch.setattr(Q, "CASES", tmp_path)
    monkeypatch.setattr(Q, "_held_ids", lambda slug: {"S001"})
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("S001.txt", source)])
    page = "<p>The review says &ldquo;%s&rdquo;.</p>" % quote
    return {n: (s, d) for n, s, d in Q.preflight_rows("testissue", page)}


def test_unicode_ellipsis_segments_in_order_pass(tmp_path, monkeypatch):
    rows = _case(tmp_path, monkeypatch,
                 "the effect of the intervention was large in adults … "
                 "small in children under five")
    assert rows["quotations match the source"][0] == Q.OK, rows


def test_three_dot_ellipsis_segments_in_order_pass(tmp_path, monkeypatch):
    rows = _case(tmp_path, monkeypatch,
                 "the effect of the intervention was large in adults... "
                 "absent in infants... Confidence in the adult estimate is high")
    assert rows["quotations match the source"][0] == Q.OK, rows


def test_out_of_order_segments_fail(tmp_path, monkeypatch):
    rows = _case(tmp_path, monkeypatch,
                 "small in children under five … the effect of the intervention "
                 "was large in adults")
    assert rows["quotations match the source"][0] == Q.BAD, rows


def test_a_segment_not_in_the_source_fails(tmp_path, monkeypatch):
    rows = _case(tmp_path, monkeypatch,
                 "the effect of the intervention was large in adults … "
                 "moderate in children under five")
    assert rows["quotations match the source"][0] == Q.BAD, rows


def test_a_segment_only_in_the_typed_verbatim_still_fails_against_the_bytes(
        tmp_path, monkeypatch):
    """The recorded verbatim agrees with the page; the held bytes do not."""
    altered = SOURCE.replace("small in children", "moderate in children")
    rows = _case(tmp_path, monkeypatch,
                 "the effect of the intervention was large in adults … "
                 "moderate in children under five", verbatim=altered)
    assert rows["quotations match the source"][0] == Q.BAD, rows


def test_quoted_in_unit():
    body = Q.norm(SOURCE)
    assert Q.quoted_in(Q.norm("large in adults … absent in infants"), body)
    assert not Q.quoted_in(Q.norm("absent in infants … large in adults"), body)
    assert not Q.quoted_in(Q.norm("large in adults absent in infants"), body)
    assert not Q.quoted_in(Q.norm("…"), body)
    # a segment may not reuse the text the previous one matched
    assert not Q.quoted_in("abc ... abc", "xx abc yy")
