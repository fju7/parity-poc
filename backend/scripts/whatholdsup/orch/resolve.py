"""Resolve a discover proposal through Europe PMC, with WHU's own lookup (find_access.epmc, titles_agree).
WHU's modules do not import the shared verify package (backend/tests/verify/test_units.py, design doc §8).

A proposal resolves only when Europe PMC returns a record whose title agrees (find_access.titles_agree), whose
first author's surname matches the proposal's, and whose year is within one of the proposal's. The identifiers
come from that record and nowhere else. Anything else is Unresolved, with the reason.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


@dataclass
class Ident:
    kind: str
    value: str


@dataclass
class Found:
    identifier: Ident
    heading: str
    registry: str = "europepmc"
    extra: dict = field(default_factory=dict)


@dataclass
class Unresolved:
    reason: str
    status: str = "NOT_FOUND"


def _surname(name: str | None) -> str:
    parts = [p for p in (name or "").replace(",", " ").split() if len(p) > 1 or p.isalpha()]
    return parts[0].lower() if parts else ""


def search(title: str, first_author: str | None = None, year: int | None = None, kind: str | None = None,
           lookup=None):
    import find_access as FA
    lookup = lookup or FA.epmc
    rec = lookup(title, "TITLE")
    if rec is None:
        return Unresolved("Europe PMC returned no record for the title (or did not answer)", "NOT_FOUND")
    return _checked(rec, title, first_author, year)


def search_pmcid(pmcid: str, title: str, first_author: str | None = None, year: int | None = None, lookup=None):
    """An article hosted on PMC (ruling (c), 2026-11-07): confirmed as an article through Europe PMC by its PMCID,
    then held to the same title, author and year checks as a title search."""
    import find_access as FA
    lookup = lookup or FA.epmc
    rec = lookup(pmcid, "PMCID")
    if rec is None:
        return Unresolved("Europe PMC returned no record for %s (or did not answer)" % pmcid, "NOT_FOUND")
    got = _checked(rec, title, first_author, year, pmcid=pmcid)
    if isinstance(got, Found):
        got.extra["pmcid"] = got.extra.get("pmcid") or pmcid
    return got


def _checked(rec: dict, title: str, first_author, year, pmcid: str | None = None):
    import find_access as FA
    ok, why = FA.titles_agree(title, rec.get("title") or "")
    if not ok:
        return Unresolved("title does not agree: %s" % why)
    sn = _surname(first_author)
    authors = (rec.get("authorString") or "").lower()
    if sn and sn not in authors:
        return Unresolved("first author %r not in the record's authors" % first_author)
    try:
        ry = int(rec.get("pubYear") or 0)
    except ValueError:
        ry = 0
    if year and ry and abs(ry - int(year)) > 1:
        return Unresolved("year %s does not match the record's %s" % (year, ry))
    if rec.get("doi"):
        ident = Ident("doi", rec["doi"])
    elif rec.get("pmid"):
        ident = Ident("pmid", rec["pmid"])
    elif pmcid and rec.get("pmcid") == pmcid:
        ident = Ident("pmcid", pmcid)
    else:
        return Unresolved("the record carries no DOI or PMID")
    extra = {k: rec.get(k) for k in ("pmcid", "pmid", "license") if rec.get(k)}
    return Found(ident, rec.get("title") or title, "europepmc", extra)
