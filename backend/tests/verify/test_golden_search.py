"""verify.search golden set: the registry lookup that replaced the model's identifier slot.

known_good  the 15 proposals of the mmr-vaccine-autism scratch discovery run
            (2026-09-15) that the registries resolved; each must still resolve
            to the same identifier.
known_bad   the PriorixTetra near-miss: a Cochrane review title that word-
            matched a GSK MMRV trial at 0.8 and minted NCT01506193, in every
            form the model produced it (wrong author, right author, declared a
            trial, not declared a trial). None may return that trial.

The trial-registry rule is pinned by value, and the near-miss pair's ratio is
pinned too, so loosening the rule OR changing the tokeniser such that the
pair drifts above it fails here rather than in a discovery run.

Replayed from tests/verify/fixtures/http (recorded live 2026-09-15).
Run: python3 -m pytest backend/tests/verify/test_golden_search.py -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("VERIFY_CACHE_DIR", str(Path(__file__).parent / "fixtures" / "http"))

import verify.search as vs  # noqa: E402

GOLDEN = json.loads((Path(__file__).parent / "golden_search.json").read_text())


def _ident(r) -> str | None:
    return f"{r.identifier.system}:{r.identifier.value}" if isinstance(r, vs.Found) else None


def test_trial_rule_is_pinned():
    rule = GOLDEN["trial_rule"]
    assert vs.TRIAL_MATCH_RATIO == rule["TRIAL_MATCH_RATIO"] == 0.9
    assert vs.TRIAL_MATCH_MIN == rule["TRIAL_MATCH_MIN"] == 4
    assert vs.TRIAL_MATCH_RATIO > vs.MATCH_RATIO and vs.TRIAL_MATCH_MIN > vs.MATCH_MIN


@pytest.mark.parametrize("pair", GOLDEN["near_miss_pairs"], ids=lambda p: p["proposed"][:40])
def test_near_miss_pair_sits_below_the_trial_rule_and_above_the_article_rule(pair):
    """The pairs are the reason the rule exists. If the tokeniser ever moves a
    ratio to >= 0.9 the rule no longer covers it and this says so. Note the
    varicella pair shares FIVE words at 0.833: the word floor alone would not
    have refused it; the ratio does."""
    ok, ratio, shared = vs._title_matches(pair["proposed"], pair["registry_title"])
    assert ok and abs(ratio - pair["ratio_on_2026_09_15"]) < 1e-9, (ratio, shared)   # the article rule accepts it...
    assert sorted(shared) == pair["shared_on_2026_09_15"]
    assert not (ratio >= vs.TRIAL_MATCH_RATIO and len(shared) >= vs.TRIAL_MATCH_MIN)  # ...the trial rule does not


def test_ctgov_is_never_consulted_for_an_article(monkeypatch):
    calls = []
    monkeypatch.setattr(vs, "_ctgov", lambda *a, **k: calls.append(a) or None)
    monkeypatch.setattr(vs, "_epmc", lambda *a, **k: None)
    monkeypatch.setattr(vs, "_crossref", lambda *a, **k: None)
    assert isinstance(vs.search("Vaccines for measles, mumps and rubella in children", "Taylor", 2014, kind=None), vs.Unresolved)
    assert isinstance(vs.search("Vaccines for measles, mumps and rubella in children", "Taylor", 2014, kind="article"), vs.Unresolved)
    assert calls == []
    vs.search("Vaccines for measles, mumps and rubella in children", "Taylor", 2014, kind="trial")
    assert len(calls) == 1


@pytest.mark.parametrize("entry", GOLDEN["known_good"], ids=[e["expect"] for e in GOLDEN["known_good"]])
def test_known_good_still_resolves_to_the_same_identifier(entry):
    r = vs.search(entry["title"], entry["first_author"], entry["year"], entry["kind"])
    assert _ident(r) == entry["expect"], r
    assert r.registry == entry["registry"]
    assert r.identifier.provenance.name == "SEARCHED"


@pytest.mark.parametrize("entry", GOLDEN["known_bad"], ids=[f'{e["first_author"]}-{e["year"]}-{e["kind"]}' for e in GOLDEN["known_bad"]])
def test_the_near_miss_is_never_minted(entry):
    r = vs.search(entry["title"], entry["first_author"], entry["year"], entry["kind"])
    got = _ident(r)
    assert got != entry["forbid"], r
    if got is not None:
        assert r.identifier.system != "nct", r                  # a review is not a trial, whatever the model said
    else:
        # unresolved: the near-miss is reported to a reviewer, not written
        assert isinstance(r, vs.Unresolved) and r.reason.startswith("no registry title"), r


def test_all_fifteen_resolve_under_the_tightened_rule():
    n = sum(1 for e in GOLDEN["known_good"]
            if _ident(vs.search(e["title"], e["first_author"], e["year"], e["kind"])) == e["expect"])
    assert n == len(GOLDEN["known_good"]) == 15
