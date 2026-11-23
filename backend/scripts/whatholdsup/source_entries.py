"""Source-list entries, built from each source's own registry record (advisor's ruling 3 after orchestrator trial 1
attempt 18, 2026-11-23).

Attempt 18's page listed "Saran. Evidence and gap map ... countries.. Campbell Systematic Reviews. 2020.": the
author was the discover model's surname alone (Europe PMC's record gives "Saran A, White H, Kuper H."), and the
registry's title ends in a full stop the renderer then doubled. (The "2018" the audit reader quoted was the
previous entry's year, Kuper's 2018 assessment: the reader joined three adjacent audit units; no record was mixed.)

An entry is now: authors with initials (the first three, then "et al."), the title, the container and ONE
publication year -- all from the record the registry returned for that source (src["registry_record"]), never a
correction's or another version's. A source with no registry record (an agency's own site) keeps its proposal's
fields. `problems` fails an entry on doubled punctuation, more than one year outside the title, or a missing author
initial where the registry gives one; it runs as a standing orchestrator check and as a lean preflight row.
"""
from __future__ import annotations

import html as H
import json
import re
from pathlib import Path

ROW = "source-list entries match their registry records"
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
DOUBLED = re.compile(r"(?<!\.)\.\.(?!\.)|,,|;;|::|\.\s+\.|,\s*\.|[?!]\.")
AUTHOR_WITH_INITIALS = re.compile(r"^[^\W\d][\w'’ -]*\s+[A-Z]{1,4}\.?$")
ENTRY = re.compile(r'<div class="src"><span class="tag">\[(\d+)\]</span>\s*(.*?)</div>', re.S)


def record_from_epmc(rec: dict) -> dict:
    """The fields an entry is built from, as Europe PMC's core record gives them."""
    authors = [a.strip() for a in (rec.get("authorString") or "").rstrip(".").split(",") if a.strip()]
    year = rec.get("pubYear")
    container = ((rec.get("journalInfo") or {}).get("journal") or {}).get("title") or rec.get("journalTitle")
    return {"registry": "europepmc", "authors": authors,
            "year": int(year) if str(year or "").isdigit() else None,
            "title": rec.get("title") or None, "container": container or None}


def _clean(s: str | None) -> str:
    return re.sub(r"[\s.]+$", "", " ".join((s or "").split()))


def _authors(names: list[str]) -> str:
    names = [_clean(n) for n in names if _clean(n)]
    if not names:
        return ""
    return ", ".join(names[:3]) + (", et al" if len(names) > 3 else "")


def entry_text(src: dict) -> str:
    rec = src.get("registry_record")
    if rec:
        parts = (_authors(rec.get("authors") or []), _clean(rec.get("title") or src.get("title")),
                 _clean(rec.get("container")), str(rec["year"]) if rec.get("year") else None)
    else:
        parts = (_clean(src.get("authors")), _clean(src.get("title")), _clean(src.get("container")),
                 str(src["year"]) if src.get("year") else None)
    out = ""
    for p in (p for p in parts if p):
        out += (p if not out else (" " if out[-1] in "?!" else ". ") + p)
    return out + ("" if out[-1:] in ("?", "!") else ".")


def entry_html(n: int, src: dict) -> str:
    text = entry_text(src)
    link = src.get("url") or ("https://doi.org/%s" % src["doi"] if src.get("doi") else "")
    inner = '<a href="%s">%s</a>' % (H.escape(link), H.escape(text)) if link else H.escape(text)
    return '<div class="src"><span class="tag">[%d]</span> %s</div>' % (n, inner)


def problems(src: dict, text: str) -> list[str]:
    out = []
    title = _clean((src.get("registry_record") or {}).get("title") or src.get("title"))
    if DOUBLED.search(text):
        out.append("doubled punctuation")
    outside = text.replace(title, " ") if title else text
    years = YEAR.findall(outside)
    if len(years) > 1:
        out.append("more than one year (%s)" % ", ".join(years))
    rec_authors = (src.get("registry_record") or {}).get("authors") or []
    if rec_authors and AUTHOR_WITH_INITIALS.match(_clean(rec_authors[0])):
        first = text.split(",")[0].split(". ")[0]
        if not AUTHOR_WITH_INITIALS.match(_clean(first)):
            out.append("first author without the initials the registry gives (%r)" % rec_authors[0])
    return out


def page_problems(sources: list[dict], page_html: str) -> list[str]:
    """Every source-list entry on the page, checked against its source (by the entry's [n])."""
    out = []
    for m in ENTRY.finditer(page_html or ""):
        n = int(m.group(1))
        text = " ".join(H.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split())
        if not 1 <= n <= len(sources):
            out.append("[%d]: no source %d" % (n, n))
            continue
        out += ["[%d] %s" % (n, p) for p in problems(sources[n - 1], text)]
    return out


def preflight_rows(slug: str, page: Path, ok: str, bad: str) -> list[tuple[str, str, str]]:
    """The lean preflight row (publish.preflight passes the issue's page and its OK / BAD)."""
    import source_store as store
    sources = json.loads((store.case_dir(slug) / "sources.json").read_text(encoding="utf-8")).get("sources") or []
    if not Path(page).exists():
        return [(ROW, bad, "no page at %s" % page)]
    found = page_problems(sources, Path(page).read_text(encoding="utf-8"))
    return [(ROW, bad if found else ok, "; ".join(found[:6]) if found else "every entry from its registry record")]
