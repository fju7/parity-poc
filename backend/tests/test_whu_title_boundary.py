"""A title match exactly at the limits needs an equal year or an equal container (advisor's ruling 1 on P118-P121,
2026-11-25; title_match.check, at_boundary, boundary_ok). WHU's port only: verify/search.py and its golden set are
unchanged, and title_matches() still equals verify's (test_whu_title_match.py).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): S007 was proposed as Hunt 2020, "Inclusive education:
children with disabilities (Background paper for the 2020 Global Education Monitoring Report)", container "UNESCO /
Global Education Monitoring Report Team"; confirm attached Crossref's Hunt 2019, "Inclusive Education as Global
Development Policy", a chapter of The Sage Handbook of Inclusion and Diversity in Education (doi
10.4135/9781526470430.n12), on 3 of 5 distinctive words = 0.6 against MATCH_RATIO 0.6 and MATCH_MIN 3.

Records: the committed folders issues/WHU-OT1-02zc-... and issues/WHU-OT1-02z-... (read only).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import title_match as TM          # noqa: E402
from orch import resolve as RV    # noqa: E402
import orchestrator as O          # noqa: E402

C02ZC = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"
C02Z = ROOT / "issues" / "WHU-OT1-02z-whu-lean-orch-t1-q1-02z"


def _src(case, sid):
    return next(s for s in json.loads((case / "sources.json").read_text())["sources"] if s["id"] == sid)


def _record(rr, doi=None):
    """A source's recorded registry_record in the fields resolve's checks read (Crossref's record shape)."""
    return {"title": rr["title"], "authorString": ", ".join(rr.get("authors") or []),
            "pubYear": str(rr.get("year") or ""), "journalTitle": rr.get("container"), "doi": doi,
            "registry": "crossref"}


def test_02zc_s007_is_a_boundary_match_and_is_refused():
    s = _src(C02ZC, "S007")
    p, rec = s["proposed"], _record(s["registry_record"], s["doi"])
    ok, ratio, shared = TM.title_matches(p["title"], rec["title"])
    assert ok and ratio == TM.MATCH_RATIO and len(shared) == TM.MATCH_MIN and TM.at_boundary(ratio, shared)
    assert TM.check(p["title"], p["first_author"], p["year"], rec)[0] is False
    agrees, why = TM.check(p["title"], p["first_author"], p["year"], rec, proposed_container=s["container"])
    assert not agrees and "boundary match" in why and "2020 vs 2019" in why
    got = RV._checked(rec, p["title"], p["first_author"], p["year"], registry="crossref", container=s["container"])
    assert isinstance(got, RV.Unresolved) and "boundary match" in got.reason


def test_02z_s006_still_passes():
    s = _src(C02Z, "S006")
    p, rec = s["proposed"], _record(s["registry_record"], s["doi"])
    ok, ratio, shared = TM.title_matches(p["title"], rec["title"])
    assert ok and not TM.at_boundary(ratio, shared)                     # 0.75 on 3: not at the limits
    assert TM.check(p["title"], p["first_author"], p["year"], rec, proposed_container=s["container"])[0]
    got = RV._checked(rec, p["title"], p["first_author"], p["year"], registry="crossref", container=s["container"])
    assert isinstance(got, RV.Found) and got.identifier.value == s["doi"]


BOUND_P = "Inclusive education children disabilities background paper monitoring report global"
BOUND_R = "Inclusive education global development policy"


def test_at_the_boundary_an_equal_year_or_an_equal_container_admits_it():
    ok, ratio, shared = TM.title_matches(BOUND_P, BOUND_R)
    assert ok and TM.at_boundary(ratio, shared)
    rec = {"title": BOUND_R, "authorString": "", "pubYear": "2019", "journalTitle": "The Sage Handbook"}
    assert TM.check(BOUND_P, None, 2019, rec)[0]                                     # year equal
    assert TM.check(BOUND_P, None, 2020, rec, proposed_container="the sage handbook")[0]  # container equal
    assert not TM.check(BOUND_P, None, 2020, rec, proposed_container="UNESCO")[0]        # within one is not equal
    assert not TM.check(BOUND_P, None, None, rec)[0]                                 # nothing to compare: refused
    nested = {"title": BOUND_R, "pubYear": "2019", "journalInfo": {"journal": {"title": "The Sage Handbook"}}}
    assert TM.check(BOUND_P, None, 2020, nested, proposed_container="The Sage Handbook")[0]


def test_above_the_boundary_and_containment_are_unchanged():
    rec = {"title": "Inclusive education global development policy children", "pubYear": "2010"}
    ok, ratio, shared = TM.title_matches(BOUND_P, rec["title"])
    assert ok and not TM.at_boundary(ratio, shared) and TM.check(BOUND_P, None, 2020, rec)[0] is False  # year rule
    assert TM.check(BOUND_P, None, 2011, rec)[0]
    cont = {"title": "Inclusive education global development", "pubYear": "2010"}
    assert TM.check("Inclusive education global development policy", None, 2011, cont)[0]


def test_the_proposals_container_reaches_resolve_and_stubs_still_work():
    seen = {}

    def real_like(t, a, y, k, container=None):
        seen["container"] = container
        return RV.Unresolved("none")
    p = {"type": "review", "title": "T", "first_author": "A", "year": 2020, "container": "UNESCO", "url": ""}
    O.resolve_proposals([p], real_like)
    assert seen["container"] == "UNESCO"
    O.resolve_proposals([p], lambda t, a, y, k: RV.Unresolved("none"))               # a four-argument stub


def test_verify_is_not_changed():
    src = (ROOT / "backend" / "verify" / "search.py").read_text(encoding="utf-8")
    assert "boundary" not in src.lower()
