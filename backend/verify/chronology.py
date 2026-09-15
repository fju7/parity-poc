"""CHRONOLOGY: a source cannot support a claim about an event that postdates it.

The existence -> ordering mechanism from the design's own taxonomy. Three
GMC claims on the first mmr freeze were "source confirmed" against Wakefield
1998 -- true statements the 1998 paper cannot contain, because the General
Medical Council ruled in 2010. Deterministic, no model:

  literature / generic   a date the claim references AFTER the source's
                         publication date  -> IMPOSSIBLE
  law                    NOT judged today: the registries expose the current
                         version's effective date and a partial version list,
                         not enactment, so "before it existed" cannot be shown

"A date the claim references" is (1) an explicit date in the claim text --
"February 2010", "in 2004", "24 May 2010" -- or (2) a dated event the claim
names, from two places that need no model: the registry's own events for
this source (a paper cannot support a claim about its own retraction; the
retraction date comes from Crossref), and a small curated table of named
events (backend/data/verify/events.json: phrase, date, source, curator).
A claim with no date and no named event, or a source with no date, cannot
be judged and CHRONOLOGY says so; it never refuses on silence.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .types import Binding, Kind, Resolution

EVENTS = Path(__file__).resolve().parents[1] / "data" / "verify" / "events.json"
_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"], 1)}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})
_MONTH_RX = "|".join(sorted(_MONTHS, key=len, reverse=True))
# "6 February 2010", "February 6, 2010", "February 2010", "2010" (not inside a longer number / not a figure like 1,961)
_DATE = re.compile(r"\b(?:(?P<d1>\d{1,2})\s+(?P<m1>" + _MONTH_RX + r")\.?\s+(?P<y1>(?:19|20)\d{2})"
                   r"|(?P<m2>" + _MONTH_RX + r")\.?\s+(?:(?P<d2>\d{1,2}),?\s+)?(?P<y2>(?:19|20)\d{2})"
                   r"|(?<!\d)(?<!\d,)(?<!\d\.)(?P<y3>(?:19|20)\d{2})(?!\d|,\d|\.\d))\b", re.I)


def claim_dates(text: str) -> list[tuple[dt.date, str]]:
    """(date, precision) for every explicit date in the text; precision 'day' | 'month' | 'year'."""
    out = []
    for m in _DATE.finditer(text or ""):
        if m.group("y1"):
            out.append((dt.date(int(m.group("y1")), _MONTHS[m.group("m1").lower()], int(m.group("d1"))), "day"))
        elif m.group("y2"):
            mo = _MONTHS[m.group("m2").lower()]
            out.append((dt.date(int(m.group("y2")), mo, int(m.group("d2") or 1)), "day" if m.group("d2") else "month"))
        else:
            out.append((dt.date(int(m.group("y3")), 1, 1), "year"))
    return out


def _events() -> list[dict]:
    try:
        return json.loads(EVENTS.read_text())["events"]
    except Exception:
        return []


def named_events(text: str, registry_events: list[dict] | None = None) -> list[tuple[dt.date, str, str]]:
    """(date, precision, label) for every dated event the claim names."""
    t = (text or "").lower()
    out = []
    for e in _events():
        if any(p.lower() in t for p in e["phrases"]):
            out.append((dt.date.fromisoformat(e["date"]), e.get("precision", "day"), e["label"]))
    # the registry's own events for THIS source: a paper cannot support a claim about its own retraction
    # A claim that names this source's own retraction, correction or concern
    # references the registry's date for it -- Crossref update-to / Europe PMC
    # -- never a typed one. "Ten of the thirteen co-authors withdrew" is the
    # 2004 partial retraction, which Crossref records as a correction.
    if registry_events and re.search(r"\bretract|withdrawn by the journal|expression of concern|erratum|correction to|"
                                     r"co-authors\b.{0,40}\bwithdrew|withdrew their names|retraction of an interpretation", t):
        for ev in registry_events:
            if ev.get("type") in ("retraction", "correction", "expression_of_concern", "erratum") and ev.get("date"):
                parts = [int(x) for x in re.findall(r"\d+", str(ev["date"]))]
                if parts:
                    y, mo, d = (parts + [1, 1])[:3]
                    out.append((dt.date(y, mo, d), "day" if len(parts) == 3 else "month" if len(parts) == 2 else "year",
                                f"registry {ev['type']} of this source"))
    return out


def _source_date(res: Resolution) -> tuple[dt.date, str] | None:
    ex = res.extra or {}
    parts = ex.get("published")
    if parts and parts[0]:
        y, mo, d = (list(parts) + [1, 1])[:3]
        return dt.date(int(y), int(mo or 1), int(d or 1)), "day" if len(parts) >= 3 else "month" if len(parts) == 2 else "year"
    if ex.get("year"):
        return dt.date(int(ex["year"]), 1, 1), "year"
    # LAW IS NOT JUDGED. codes.ohio.gov's "Effective:" is the date of the
    # CURRENT version (3901.381 shows 2019; it was enacted in 2002) and its
    # version list starts where the site's archive does (2010), not at
    # enactment. A claim dated before that is not thereby impossible, and a
    # check that cannot tell must say so rather than refuse. Until a registry
    # exposes enactment, law CHRONOLOGY returns cannot-be-judged.
    st = (ex.get("status") or {})
    sd = (st.get("startDateStruct") or {}).get("date") if isinstance(st, dict) else None
    if sd:
        parts = [int(x) for x in sd.split("-")]
        return dt.date(*(parts + [1, 1])[:3]), "day" if len(parts) == 3 else "month"
    return None


def _after(a: tuple[dt.date, str], b: tuple[dt.date, str]) -> bool:
    """Is date a strictly after date b at the coarser of the two precisions?"""
    order = {"year": 0, "month": 1, "day": 2}
    p = min(order[a[1]], order[b[1]])
    if p == 0:
        return a[0].year > b[0].year
    if p == 1:
        return (a[0].year, a[0].month) > (b[0].year, b[0].month)
    return a[0] > b[0]


def bind_chronology(assertion: str, res: Resolution, registry_events: list[dict] | None = None) -> Binding:
    refs = [(d, p, f"explicit date {d.isoformat()[:{'year': 4, 'month': 7, 'day': 10}[p]]}") for d, p in claim_dates(assertion)]
    refs += [(d, p, label) for d, p, label in named_events(assertion, registry_events)]
    if not refs:
        return Binding(Kind.CHRONOLOGY, True, evidence="no date or dated event in the claim; cannot be judged")
    src = _source_date(res)
    if src is None:
        return Binding(Kind.CHRONOLOGY, True, evidence="source has no date; cannot be judged")
    law = res.identifier.registry == "law"
    for d, p, label in refs:
        if law and _after(src, (d, p)):
            return Binding(Kind.CHRONOLOGY, False, evidence=label,
                           reason=f"IMPOSSIBLE: the claim references {label}, before the provision's effective date {src[0].isoformat()}")
        if not law and _after((d, p), src):
            return Binding(Kind.CHRONOLOGY, False, evidence=label,
                           reason=f"IMPOSSIBLE: the claim references {label}, after the source's publication ({src[0].year})")
    return Binding(Kind.CHRONOLOGY, True, evidence=f"source {src[0].isoformat()[:4]}; " + "; ".join(r[2] for r in refs))
