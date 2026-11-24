"""Resolve a discover proposal through Europe PMC, with WHU's own lookup (find_access.epmc, titles_agree).
WHU's modules do not import the shared verify package (backend/tests/verify/test_units.py, design doc §8).

A proposal resolves only when Europe PMC returns a record whose title agrees (find_access.titles_agree), whose
first author's surname matches the proposal's, and whose year is within one of the proposal's. The identifiers
come from that record and nowhere else. Anything else is Unresolved, with the reason.

Fallbacks (advisor's ruling 2 after attempt 24, 2026-11-24): when Europe PMC is still unavailable after the
retries, the title is looked up at PubMed (NCBI E-utilities) and then Crossref, and a record from either is held
to the same title, author and year checks. Every result names the registries asked and which answered
(`answered`); the Europe PMC outage is marked covered (registries.covered) only when a fallback answered. With no
registry answering, the outage stays and the run stops "registry unavailable; run again later".
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
    answered: list = field(default_factory=list)


def _surname(name: str | None) -> str:
    parts = [p for p in (name or "").replace(",", " ").split() if len(p) > 1 or p.isalpha()]
    return parts[0].lower() if parts else ""


def search(title: str, first_author: str | None = None, year: int | None = None, kind: str | None = None,
           lookup=None, registries=None):
    """LOOKUP (tests; find_access.epmc's shape, a record or None) keeps the Europe-PMC-only path. Otherwise
    REGISTRIES (default registries.py) gives Europe PMC, then on an outage PubMed and Crossref."""
    if lookup is not None:
        rec = lookup(title, "TITLE")
        if rec is None:
            return Unresolved("Europe PMC returned no record for the title (or did not answer)", "NOT_FOUND")
        return _checked(rec, title, first_author, year)
    RG = registries or _registries()
    first = RG.epmc_title(title)
    if first.answered:
        if first.record is None:
            return Unresolved("Europe PMC returned no record for the title", "NOT_FOUND", [first.row("title")])
        got = _checked(first.record, title, first_author, year)
        _answered(got, [first.row("title")])
        return got
    return _fallback(RG, first, "title", [lambda: RG.pubmed_title(title),
                                          lambda: RG.crossref_title(title, _surname_of(first_author))],
                     title, first_author, year)


def search_pmcid(pmcid: str, title: str, first_author: str | None = None, year: int | None = None, lookup=None,
                 registries=None):
    """An article hosted on PMC (ruling (c), 2026-11-07): confirmed as an article through Europe PMC by its PMCID,
    then held to the same title, author and year checks as a title search. On a Europe PMC outage, PubMed by the
    PMCID."""
    if lookup is not None:
        rec = lookup(pmcid, "PMCID")
        if rec is None:
            return Unresolved("Europe PMC returned no record for %s (or did not answer)" % pmcid, "NOT_FOUND")
        got = _checked(rec, title, first_author, year, pmcid=pmcid)
    else:
        RG = registries or _registries()
        first = RG.epmc_id("PMCID", pmcid)
        if first.answered:
            if first.record is None:
                return Unresolved("Europe PMC returned no record for %s" % pmcid, "NOT_FOUND",
                                  [first.row(pmcid)])
            got = _checked(first.record, title, first_author, year, pmcid=pmcid)
            _answered(got, [first.row(pmcid)])
        else:
            got = _fallback(RG, first, pmcid, [lambda: RG.pubmed_pmcid(pmcid)], title, first_author, year,
                            pmcid=pmcid)
    if isinstance(got, Found):
        got.extra["pmcid"] = got.extra.get("pmcid") or pmcid
    return got


def _registries():
    import registries as RG
    return RG


def _surname_of(name):
    return _surname(name) or None


def _answered(got, rows: list) -> None:
    if isinstance(got, Found):
        got.extra["answered"] = rows
    else:
        got.answered = rows


def _fallback(RG, first, asked: str, others, title, first_author, year, pmcid=None):
    """Europe PMC (FIRST) did not answer: each fallback in turn; the first record that passes the checks is the
    source; a later fallback is asked only if no earlier one gave it, and every one asked is recorded. The Europe
    PMC outage is covered only if a fallback answered."""
    rows = [first.row(asked)]
    answered, reasons, down = [], [], [first]
    for ask in others:
        ans = ask()
        rows.append(ans.row(asked))
        if not ans.answered:
            down.append(ans)
            continue
        answered.append(ans.registry)
        for rec in ans.records or ([ans.record] if ans.record else []):
            got = _checked(rec, title, first_author, year, pmcid=pmcid, registry=rec.get("registry") or
                           ans.registry.lower())
            if isinstance(got, Found):
                for d in down:
                    RG.covered(d, answered)
                _answered(got, rows)
                return got
            reasons.append("%s: %s" % (ans.registry, got.reason))
    if not answered:
        return Unresolved("no registry answered (Europe PMC, then %s)" % ", ".join(r["registry"] for r in rows[1:]),
                          "REGISTRY_UNAVAILABLE", rows)
    for d in down:
        RG.covered(d, answered)
    why = "Europe PMC did not answer; %s returned no record that agrees%s" % (
        " and ".join(answered), (": " + "; ".join(reasons[:3])) if reasons else "")
    return Unresolved(why, "NOT_FOUND", rows)


def _checked(rec: dict, title: str, first_author, year, pmcid: str | None = None, registry: str = "europepmc"):
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
    import source_entries as SE
    extra["record"] = SE.record_from_epmc(rec) if registry == "europepmc" else SE.record_from_fallback(rec, registry)
    return Found(ident, rec.get("title") or title, registry, extra)
