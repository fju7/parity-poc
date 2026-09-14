"""The generic-URL adapter: a document with no registry identifier.

Agency reports, court decisions, guideline pages, payer policies -- on some
subjects that is where the authoritative material lives (an IOM/NAM review,
CDC surveillance, the Omnibus Autism Proceeding), and none of it carries a
DOI, PMID, NCT or law citation. Phase 3 ruling: a prerequisite, not a later
gain.

What it does: fetch the page, HEADING against its <title> element (and the
first <h1>, and the PDF's first line for a PDF), the same abstention rule,
the same four binding kinds downstream. What it does NOT do: resolve. There
is no registry to ask whether this document exists or what it is called; the
page answers for itself. So the Resolution's `registry` is "generic_fetch",
`exists` is EXISTS only in the sense that the URL returned a document, and
the record and the reader can both tell a generic fetch from a registry
resolution. The status check has no adapter for it: a moved or rewritten
page shows up as binding_lost or rerendered on the monthly re-check, never
as retracted -- because no registry can say so.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html as _html
import re
import urllib.parse

from . import http
from .law import _pdftotext, _strip
from .types import Document, Exists, Identifier, Provenance, Resolution

_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: E731
_last_doc: dict[str, Document] = {}

# Text that means "you got a wall, not the document". Positive identity is
# the HEADING bind against the title; this only refuses the obvious shells,
# and the size floor does the rest (source_store.py learned this in WHU).
_WALL = re.compile(r"(enable javascript|access denied|are you a robot|verify you are human|cloudflare|"
                   r"page not found|404 not found|sign in to continue)", re.I)
MIN_TEXT = 1500


def identify(url: str, provenance: Provenance = Provenance.RESOLVED_FROM_HELD) -> Identifier | None:
    u = (url or "").strip()
    if not re.match(r"^https?://", u, re.I):
        return None
    return Identifier("url", u, u, provenance)


def _titles(page: str) -> list[str]:
    out = []
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    if m:
        out.append(_strip(m.group(1)))
    m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S | re.I)
    if m:
        out.append(_strip(m.group(1)))
    for prop in ("og:title", "citation_title", "dc.title", "DC.title"):
        m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) + r'["\'][^>]+content=["\']([^"\']+)', page, re.I)
        if m:
            out.append(_html.unescape(m.group(1)).strip())
    seen, uniq = set(), []
    for t in out:
        if t and t not in seen:
            seen.add(t); uniq.append(t)
    return uniq


def resolve(ident: Identifier) -> Resolution:
    """Fetch the page; the page answers for itself. registry = generic_fetch."""
    res = Resolution(ident, Exists.UNCHECKED, registry="generic_fetch", canonical=ident.value, checked_at=_NOW())
    st, body, headers = http.get(ident.value, timeout=60)
    if st == 404 or st == 410:
        res.exists = Exists.NONEXISTENT; res.extra = {"http": st}; return res
    if st != 200 or not body:
        res.extra = {"http": st, "error": headers.get("error")}; return res
    ctype = (headers.get("content-type") or "").split(";")[0].strip().lower()
    final = headers.get("final_url") or ident.value
    if body.startswith(b"%PDF") or ctype == "application/pdf":
        text = _pdftotext(body)
        if text is None:
            res.exists = Exists.EXISTS; res.heading = None; res.extra = {"http": st, "kind": "pdf", "text_layer": "UNEXTRACTED"}
            _last_doc[ident.value] = Document(ident, hashlib.sha256(body).hexdigest(), "", "application/pdf", _NOW(), final,
                                              "generic_fetch_pdf", "full_text", "UNEXTRACTED")
            return res
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        res.heading = " || ".join(lines[:3]) if lines else None
        res.exists = Exists.EXISTS; res.extra = {"http": st, "kind": "pdf", "final_url": final}
        clean = " ".join(text.split())
        _last_doc[ident.value] = Document(ident, hashlib.sha256(clean.encode()).hexdigest(), clean, "application/pdf",
                                          _NOW(), final, "generic_fetch_pdf", "full_text")
        return res
    page = body.decode("utf-8", "replace")
    titles = _titles(page)
    text = _strip(page)
    if len(text) < MIN_TEXT or _WALL.search(text[:2000]):
        res.exists = Exists.UNCHECKED
        res.extra = {"http": st, "reason": "a shell, a wall or too little text to be the document", "chars": len(text)}
        return res
    res.exists = Exists.EXISTS
    res.heading = " || ".join(titles) if titles else None
    res.extra = {"http": st, "kind": "html", "final_url": final, "titles": titles}
    _last_doc[ident.value] = Document(ident, hashlib.sha256(text.encode()).hexdigest(), text, "text/html", _NOW(), final,
                                      "generic_fetch_html", "full_text")
    return res


def fetch(res: Resolution) -> Document | None:
    if res.exists != Exists.EXISTS:
        return None
    if res.identifier.value not in _last_doc:
        resolve(res.identifier)
    return _last_doc.get(res.identifier.value)
