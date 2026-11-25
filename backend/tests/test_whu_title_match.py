"""WHU's identity matching (title_match.py) is verify/search.py's rule, ported (advisor's ruling 1 after the P091
build, 2026-11-24). WHU's modules may not import verify; this test may, and checks the port three ways:

  * the golden set of tests/verify/golden_search.json, replayed from tests/verify/fixtures/http, gives the same
    results with WHU's functions put in verify.search's place (known_good resolve to the same identifiers, the
    PriorixTetra near-miss is never minted);
  * the ported functions agree with verify's on every title and author the recorded replies carry;
  * the near-miss pairs' ratios and shared words are pinned, and the KV3.1 correction-notice case is refused.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts" / "whatholdsup"))
FIX = BACKEND / "tests" / "verify" / "fixtures" / "http"
GOLDEN = json.loads((BACKEND / "tests" / "verify" / "golden_search.json").read_text())

import title_match as TM  # noqa: E402


@pytest.fixture
def vs(monkeypatch):
    monkeypatch.setenv("VERIFY_CACHE_DIR", str(FIX))
    import verify.search as vs_
    return vs_


def test_the_port_carries_verifys_constants_and_boilerplate(vs):
    from verify import text as vt
    assert TM.MATCH_RATIO == vs.MATCH_RATIO == 0.6 and TM.MATCH_MIN == vs.MATCH_MIN == 3
    assert TM.LITERATURE_BOILERPLATE == vt.LITERATURE_BOILERPLATE


def _ported(monkeypatch, vs):
    monkeypatch.setattr(vs, "_title_matches", TM.title_matches)
    monkeypatch.setattr(vs, "_author_ok", TM.author_ok)
    monkeypatch.setattr(vs, "_year_ok", TM.year_ok)


@pytest.mark.parametrize("entry", GOLDEN["known_good"], ids=[e["expect"] for e in GOLDEN["known_good"]])
def test_known_good_resolve_the_same_under_the_ported_rule(entry, vs, monkeypatch):
    _ported(monkeypatch, vs)
    r = vs.search(entry["title"], entry["first_author"], entry["year"], entry["kind"])
    assert isinstance(r, vs.Found) and "%s:%s" % (r.identifier.system, r.identifier.value) == entry["expect"]
    assert r.registry == entry["registry"]


@pytest.mark.parametrize("entry", GOLDEN["known_bad"], ids=[f'{e["first_author"]}-{e["year"]}-{e["kind"]}'
                                                           for e in GOLDEN["known_bad"]])
def test_the_near_miss_is_never_minted_under_the_ported_rule(entry, vs, monkeypatch):
    _ported(monkeypatch, vs)
    r = vs.search(entry["title"], entry["first_author"], entry["year"], entry["kind"])
    got = "%s:%s" % (r.identifier.system, r.identifier.value) if isinstance(r, vs.Found) else None
    assert got != entry["forbid"]


@pytest.mark.parametrize("pair", GOLDEN["near_miss_pairs"], ids=lambda p: p["proposed"][:40])
def test_the_near_miss_pairs_arithmetic_is_pinned(pair):
    ok, ratio, shared = TM.title_matches(pair["proposed"], pair["registry_title"])
    assert abs(ratio - pair["ratio_on_2026_09_15"]) < 1e-9 and sorted(shared) == pair["shared_on_2026_09_15"]
    # WHU asks no trial registry: an article rule match, never an NCT (orch/resolve.py takes DOI / PMID / PMCID)
    assert ok


def _recorded_titles_and_authors():
    titles, authors = set(), set()
    for meta in FIX.glob("*.meta"):
        body = FIX / (meta.stem + ".bin")
        try:
            d = json.loads(body.read_bytes().decode("utf-8", "replace"))
        except (ValueError, OSError):
            continue
        for r in ((d.get("resultList") or {}).get("result") or []) if isinstance(d, dict) else []:
            titles.add(r.get("title") or "")
            authors.add((r.get("authorString") or "").split(",")[0].strip())
        for m in ((d.get("message") or {}).get("items") or []) if isinstance(d, dict) and \
                isinstance(d.get("message"), dict) else []:
            titles.add((m.get("title") or [""])[0])
            for a in m.get("author") or []:
                authors.add(a.get("family") or "")
    return sorted(t for t in titles if t), sorted(a for a in authors if a)


def test_the_port_agrees_with_verify_on_every_recorded_title_and_author(vs):
    titles, authors = _recorded_titles_and_authors()
    assert len(titles) >= 20 and len(authors) >= 20
    proposals = [e["title"] for e in GOLDEN["known_good"] + GOLDEN["known_bad"]]
    for p in proposals:
        for t in titles:
            assert TM.title_matches(p, t) == vs._title_matches(p, t), (p, t)
    for e in GOLDEN["known_good"] + GOLDEN["known_bad"]:
        for a in authors:
            assert TM.author_ok(e["first_author"], a) == vs._author_ok(e["first_author"], a), (e["first_author"], a)
            assert TM.surname_tokens(a) == vs.surname_tokens(a)
    for p, f in ((2020, 2021), (2020, 2022), (None, 2020), (2019, None)):
        assert TM.year_ok(p, f) == vs._year_ok(p, f)


def test_compound_surnames_agree_as_verify_rules():
    assert TM.author_ok("Di Pietrantonj", "Di Pietrantonj C") and TM.author_ok("Pietrantonj", "Di Pietrantonj C")
    assert TM.author_ok("van der Linden", "van der Linden S") and TM.author_ok("Ben-Shlomo", "Ben-Shlomo Y")
    assert TM.author_ok("Benshlomo", "Ben-Shlomo Y") and TM.author_ok("del Rio", "Del Rio C")
    assert not TM.author_ok("Demicheli", "Di Pietrantonj C") and not TM.author_ok("Zimmerman", "Di Pietrantonj C")


KV31 = ("Correction: KV3.1 channel modulation: a systematic review of pharmacological intervention strategies")
PROPOSAL = ("Inclusive Strategies for Children With Developmental Disabilities in Mainstream Classrooms in Africa: "
            "A systematic review")


def test_the_kv3_1_correction_notice_is_refused_by_the_title_rule_itself():
    """Attempt-24 rehearsal, 2026-11-24: Crossref returned this notice and find_access.titles_agree passed it on
    'strategies', 'systematic', 'review'. Under the ported rule they share one distinctive word."""
    ok, ratio, shared = TM.title_matches(PROPOSAL, KV31)
    assert not ok and shared == {"strategies"} and ratio < TM.MATCH_RATIO
    import find_access as FA
    assert FA.titles_agree(PROPOSAL, KV31)[0]                          # what the old rule did
    agrees, why = TM.check(PROPOSAL, None, 2025, {"title": KV31, "authorString": "", "pubYear": "2025"})
    assert not agrees and why.startswith("title does not agree")


def test_resolve_uses_the_ported_rule_with_the_kind_rule_off(monkeypatch):
    from orch import resolve as RV
    monkeypatch.setattr(RV, "_best_first", lambda records, title: list(records))
    got = RV._checked({"title": KV31, "authorString": "Smith J", "pubYear": "2025", "doi": "10.3389/x"},
                      PROPOSAL, None, 2025, registry="crossref")
    assert isinstance(got, RV.Unresolved) and "title does not agree" in got.reason


def test_the_first_author_is_the_records_first_not_any_author():
    rec = {"title": "Measles, Mumps, Rubella Vaccination and Autism: A Nationwide Cohort Study",
           "authorString": "Hviid A, Hansen JV, Frisch M, Melbye M", "pubYear": "2019"}
    t = "Measles, Mumps, Rubella Vaccination and Autism: A Nationwide Cohort Study"
    assert TM.check(t, "Hviid", 2019, rec)[0]
    assert not TM.check(t, "Melbye", 2019, rec)[0]                    # the old rule took any author
    assert not TM.check(t, "Hviid", 2015, rec)[0]
