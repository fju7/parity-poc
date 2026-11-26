"""findings.quote_is_in_source and bindings.b22_wording_claim use match_held's character equivalence (advisor's
ruling 4 on the P122-P124 findings, 2026-11-26): the ASCII hyphen, U+2010 and U+2011 are one character; U+2212 MINUS
SIGN, U+2013 EN DASH and U+2014 EM DASH are distinct.

Reported with P124: these two callers compared through norm()'s default and spancheck._norm's default, which fold the
en and em dash (and _norm the minus sign) to "-", so a quotation differing from its source only by a dash passed them
while it failed match_held and the preflight row. The constructed held texts here are not a source's; the Q-01 test
reads 02zc's S001 from the local trial library (gitignored) and skips elsewhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"
SLUG = "whu-lean-orch-t1-q1-02zc"

import bindings as B       # noqa: E402
import findings as F       # noqa: E402
import spancheck as SC     # noqa: E402

EN, EM, MINUS, HYPHEN = "–", "—", "−", "‐"
TAIL = "the follow-up ran for weeks 10%s12 of the trial in every school district"


@pytest.fixture
def held(monkeypatch):
    import source_store as store

    def use(text):
        monkeypatch.setattr(store, "held", lambda slug: {"S001": {"sha256": "0" * 64}})
        monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("s001.txt", text)])
        monkeypatch.setattr(SC, "defective_renditions", lambda slug, sid: (False, ""))
        monkeypatch.setattr(B, "_marked_page", lambda slug: None)
    return use


def _b22(quote):
    return B.b22_wording_claim({"sentence": 'In their own words, "%s".' % quote, "source_id": "S001"}, "demo")


@pytest.mark.parametrize("page_c,held_c", [(EN, "-"), ("-", EN), (EM, "-"), (MINUS, "-"), (EN, MINUS)])
def test_a_quotation_differing_only_by_a_dash_fails_both(held, page_c, held_c):
    held("Methods. In short, %s, as planned." % (TAIL % held_c))
    quote = TAIL % page_c
    ok, why = F.quote_is_in_source("demo", "S001", quote)
    assert ok is False and why == "not in S001 as printed"
    assert _b22(quote), "B22 passed a quotation that differs from the source by a dash"


@pytest.mark.parametrize("page_c,held_c", [("-", HYPHEN), (HYPHEN, "-"), ("-", "‑"), (EN, EN), (MINUS, MINUS)])
def test_hyphens_are_one_character_and_a_dash_matches_itself_in_both(held, page_c, held_c):
    held("Methods. In short, %s, as planned." % (TAIL % held_c))
    quote = TAIL % page_c
    assert F.quote_is_in_source("demo", "S001", quote)[0] is True
    assert _b22(quote) == []


def test_02zc_q01_still_passes_both_and_its_en_dash_variant_fails_both():
    import source_store as store
    from orch import run_env as RE
    if not store.LIB_TRIAL.exists():
        pytest.skip("the trial library is local only (gitignored)")
    q01 = next(q for q in json.loads((CASE / "quotations.json").read_text())["quotations"] if q["id"] == "Q-01")
    quote = q01["quote"]
    assert "twin-track" in quote                                    # ASCII on the page; S001 prints U+2010
    snap = RE.snapshot()
    try:
        RE.use(CASE)
        if "S001" not in store.held(SLUG):
            pytest.skip("S001's held text is not in this library")
        assert any("twin‐track" in t for _f, t in SC._texts(SLUG, "S001"))
        assert F.quote_is_in_source(SLUG, "S001", quote)[0] is True
        row = {"sentence": 'In their own words, "%s".' % quote, "source_id": "S001"}
        orig = B._marked_page
        B._marked_page = lambda slug: None
        try:
            assert B.b22_wording_claim(row, SLUG) == []
            dashed = quote.replace("twin-track", "twin" + EN + "track")
            assert F.quote_is_in_source(SLUG, "S001", dashed)[0] is False
            assert B.b22_wording_claim(dict(row, sentence='In their own words, "%s".' % dashed), SLUG)
        finally:
            B._marked_page = orig
    finally:
        RE.restore(snap)
