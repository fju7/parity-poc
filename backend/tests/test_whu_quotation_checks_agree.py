"""The preflight row "quotations match the source" uses match_held's character equivalence (advisor's ruling 4 on
P118-P121, 2026-11-25): the ASCII hyphen, U+2010 and U+2011 are one character; U+2212 MINUS SIGN, U+2013 EN DASH and
U+2014 EM DASH are distinct. norm()'s default (which folds the en and em dash) is unchanged for its other callers.

Before this the row compared through norm()'s default and spancheck._norm's default, which folded U+2212, U+2013 and
U+2014 to "-", while match_held (P119) did not: a quotation differing from its source only by an en dash passed the
row and failed match_held. Held text here is constructed, never a source's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import quotations as Q     # noqa: E402
import spancheck as SC     # noqa: E402

ROW = "quotations match the source"
EN, EM, MINUS, HYPHEN, NB = "–", "—", "−", "‐", "‑"
TAIL = "the follow-up ran for weeks 10%s12 of the trial in every school district"


@pytest.fixture
def row(monkeypatch):
    monkeypatch.setattr(Q, "attestations_on_file", lambda slug, page=None: [])
    monkeypatch.setattr(Q, "_held_ids", lambda slug: {"S001"})
    monkeypatch.setattr(Q, "_sources", lambda slug: {"S001": {"access": {"state": "full_text_held"}}})

    def run(quote, verbatim, held):
        monkeypatch.setattr(Q, "load", lambda slug: {"quotations": [{
            "id": "Q-01", "quote": quote, "source_id": "S001", "verbatim": verbatim}]})
        monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("docs/aa/aa.txt", held)])
        page = "<html><body><p>The review says <q>%s</q> [1].</p></body></html>" % quote
        return {n: (st, d) for n, st, d in Q.preflight_rows("testissue", page)}[ROW]
    return run


def _match_held(tmp_path, monkeypatch, quote, held):
    import source_store as store
    case = tmp_path / "WHU-X-demo"
    (case / "draft").mkdir(parents=True)
    (case / "issue.json").write_text(json.dumps({"question": "A question?"}))
    page = case / "draft" / "demo.html"
    page.write_text("<p>The review says that “%s” [1].</p>" % quote, encoding="utf-8")
    monkeypatch.setattr(Q, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "held", lambda slug: {"S001": {"sha256": "0" * 64}})
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("s001.txt", held)])
    return Q.match_held("demo", page)


@pytest.mark.parametrize("page_c,held_c", [(EN, "-"), ("-", EN), (EM, "-"), (MINUS, "-"), (EN, MINUS)])
def test_a_quotation_differing_only_by_a_dash_fails_both_checks(row, tmp_path, monkeypatch, page_c, held_c):
    quote, held = TAIL % page_c, "Methods. In short, %s, as planned." % (TAIL % held_c)
    assert Q.norm(quote) == Q.norm(TAIL % held_c) or page_c == MINUS or held_c == MINUS   # the default would fold
    st, why = row(quote, TAIL % held_c, held)                     # the recorded verbatim is the source's wording
    assert st == Q.BAD and "Q-01" in why
    st, why = row(quote, quote, held)                             # a verbatim typed to match the page: the bytes
    assert st == Q.BAD and "not in S001 as printed" in why
    got = _match_held(tmp_path, monkeypatch, quote, held)
    assert got["unmatched"]


@pytest.mark.parametrize("page_c,held_c", [("-", HYPHEN), (HYPHEN, "-"), ("-", NB), (EN, EN), (MINUS, MINUS)])
def test_hyphens_are_one_character_and_a_dash_matches_itself_in_both(row, tmp_path, monkeypatch, page_c, held_c):
    quote, held = TAIL % page_c, "Methods. In short, %s, as planned." % (TAIL % held_c)
    st, why = row(quote, TAIL % held_c, held)
    assert st == Q.OK, why
    assert _match_held(tmp_path, monkeypatch, quote, held)["unmatched"] == []


def test_the_default_norm_is_unchanged_for_other_callers():
    assert Q.norm("a %s b %s c" % (EN, EM)) == "a - b - c"
    assert SC._norm("a %s3" % MINUS) == "a -3"
