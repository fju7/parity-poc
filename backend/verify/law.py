"""The law registry adapter: CFR, Ohio Revised Code, Ohio Administrative Code,
the CMS Internet-Only Manuals, the NCCI Policy Manual.

The easy registry: free, stable URLs, machine-retrievable, no licence. A
section either has a heading or it does not, and its text is what a reader
would find. resolve() returns the registry's own heading; fetch() returns
the text of the CITED UNIT -- the section, or for the manuals the numbered
subsection sliced from the chapter -- because a heading like "Basic
conditions" identifies nothing and the paragraph is what the letter is about.

Other states are one adapter each, added when a curated candidate table
exists for them (design doc §5b: until then the state degrades to a
no-citation letter, by design).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html as _html
import re
import shutil
import subprocess
import tempfile

from . import http
from .types import Document, Exists, Identifier, Provenance, Resolution

_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: E731


# ---------------------------------------------------------------------------
# identify: a citation string -> Identifier, or None when nothing resolvable
# ---------------------------------------------------------------------------
_CFR = re.compile(r"\b(\d{1,2})\s*C\.?\s?F\.?\s?R\.?\s*(?:§+\s*)?(?:Part\s*)?(\d+\.\d+)((?:\([a-z0-9]+\))*)", re.I)
_ORC = re.compile(r"\b(?:Ohio\s+Revised\s+Code|Ohio\s+Rev\.?\s+Code|R\.C\.|O\.R\.C\.)\s*(?:§+\s*)?(\d{4}\.\d+)", re.I)
_OAC = re.compile(r"\b(?:Ohio\s+Administrative\s+Code|Ohio\s+Adm\.?\s+Code|O\.A\.C\.|OAC)\s*(?:§+\s*|[Rr]ule\s*)?(\d{4}(?:-\d+){1,3})", re.I)
_IOM = re.compile(r"\b(?:Pub(?:lication|\.)?\s*)?(100-0\d)\b[^.\n]{0,60}?\b[Cc]hapter\s+(\d+)(?:[^.\n]{0,20}?\b[Ss]ection\s+(\d+(?:\.\d+)*))?")
_NCCI = re.compile(r"\bNCCI\b[^.\n]{0,50}?\b[Cc]hapter\s+([IVX]+|\d+)(?:[^.\n]{0,20}?\b[Ss]ection\s+([A-Z]))?")
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
          "XI": 11, "XII": 12, "XIII": 13}


def identify(text: str, provenance: Provenance = Provenance.TYPED) -> Identifier | None:
    t = text or ""
    m = _CFR.search(t)
    if m:
        return Identifier("cfr", f"{m.group(1)}:{m.group(2)}{m.group(3).lower()}", m.group(0), provenance)
    m = _OAC.search(t)
    if m:
        return Identifier("oac", m.group(1), m.group(0), provenance)
    m = _ORC.search(t)
    if m:
        return Identifier("orc", m.group(1), m.group(0), provenance)
    m = _IOM.search(t)
    if m:
        return Identifier("cms_iom", f"{m.group(1)}:{m.group(2)}:{m.group(3) or ''}".rstrip(":"), m.group(0), provenance)
    m = _NCCI.search(t)
    if m:
        ch = m.group(1); ch = str(_ROMAN.get(ch.upper(), ch))
        return Identifier("ncci", f"{ch}:{m.group(2) or ''}".rstrip(":"), m.group(0), provenance)
    return None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _strip(html: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def _doc(ident: Identifier, text: str, route: str, url: str | None, kind: str = "section",
         content_type: str = "text/plain", text_layer: str = "DECLARED_SOUND") -> Document:
    return Document(ident, hashlib.sha256(text.encode()).hexdigest(), text, content_type, _NOW(), url,
                    route, kind, text_layer)


def _pdftotext(pdf: bytes) -> str | None:
    exe = shutil.which("pdftotext") or next((p for p in ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext",
                                                         "/usr/bin/pdftotext") if shutil.os.path.exists(p)), None)
    if not exe:
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf); path = f.name
    try:
        return subprocess.run([exe, "-layout", path, "-"], capture_output=True, text=True, timeout=120).stdout
    finally:
        shutil.os.unlink(path)


# ---------------------------------------------------------------------------
# CFR via the eCFR versioner API
# ---------------------------------------------------------------------------
def _ecfr_date() -> str:
    # The API serves point-in-time text; the first of the current month is
    # always available and is what we cite. Recorded in the Resolution.
    today = dt.date.today()
    return today.replace(day=1).isoformat()


def _cfr(ident: Identifier) -> tuple[Resolution, Document | None]:
    title, rest = ident.value.split(":", 1)
    section = re.match(r"[\d.]+", rest).group(0)
    paras = re.findall(r"\(([a-z0-9]+)\)", rest)
    date = _ecfr_date()
    url = f"https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title}.xml?section={section}"
    res = Resolution(ident, Exists.UNCHECKED, registry="ecfr", checked_at=_NOW(),
                     canonical=f"https://www.ecfr.gov/current/title-{title}/section-{section}")
    st, body, _ = http.get(url)
    if st == 404:
        res.exists = Exists.NONEXISTENT; return res, None
    if st != 200 or not body:
        return res, None
    xml = body.decode("utf-8", "replace")
    m = re.search(r"<HEAD>\s*§\s*[\d.]+\s*(.*?)</HEAD>", xml, re.S)
    res.exists = Exists.EXISTS
    res.heading = _strip(m.group(1)) if m else None
    res.registry_id = f"{title} CFR {section}"; res.extra = {"as_of": date}
    text = _strip(xml)
    # The cited unit: narrow to the paragraph when the citation names one,
    # e.g. (a)(6). Fall back to the whole section if the paragraph is not found.
    unit = text
    for p in paras:
        m = re.search(r"\(" + re.escape(p) + r"\)\s", unit)
        if not m:
            break
        tail = unit[m.start():]
        nxt = re.search(r"\s\([a-z0-9]+\)\s", tail[4:])
        unit = tail[: (nxt.start() + 4) if nxt else len(tail)]
    res.extra["section_text"] = text
    if paras and unit is not text:
        # A paragraph citation names the paragraph, whose own words are what
        # a reader compares against; "Basic conditions" is the section's
        # heading and identifies nothing about (a)(6).
        res.heading = (res.heading or "") + " || " + unit[:300]
    return res, _doc(ident, unit, "ecfr_api", res.canonical, "section", "application/xml")


# ---------------------------------------------------------------------------
# Ohio Revised Code / Administrative Code via codes.ohio.gov
# ---------------------------------------------------------------------------
def _ohio(ident: Identifier) -> tuple[Resolution, Document | None]:
    if ident.system == "orc":
        url = f"https://codes.ohio.gov/ohio-revised-code/section-{ident.value}"
    else:
        url = f"https://codes.ohio.gov/ohio-administrative-code/rule-{ident.value}"
    res = Resolution(ident, Exists.UNCHECKED, registry="codes.ohio.gov", canonical=url, checked_at=_NOW())
    st, body, _ = http.get(url)
    if st == 404:
        res.exists = Exists.NONEXISTENT; return res, None
    if st != 200 or not body:
        return res, None
    page = body.decode("utf-8", "replace")
    m = re.search(r"<h1>\s*(?:Section|Rule)\s+[\d.\-]+\s*<span[^>]*>\|</span>\s*(.*?)</h1>", page, re.S)
    if not m:
        # A page that loaded but has no section heading is not the section.
        res.exists = Exists.NONEXISTENT if "not found" in page.lower() else Exists.UNCHECKED
        return res, None
    res.exists = Exists.EXISTS
    res.heading = _strip(m.group(1)).rstrip(".")
    # The chapter's own title is part of what the registry says the section
    # is: 3922.01 is "Definitions" under "Chapter 3922 External Review".
    c = re.search(r'href="/ohio-(?:revised|administrative)-code/chapter-[\w.\-]+">\s*(Chapter[^<]+)</a>', page)
    if c:
        res.heading += " || " + _strip(c.group(1))
    res.registry_id = f"{'ORC' if ident.system == 'orc' else 'OAC'} {ident.value}"
    main = page[page.find("<main"):]
    main = main[: main.find("</main>")] if "</main>" in main else main
    return res, _doc(ident, _strip(main), "codes_ohio_gov", url, "section", "text/html")


# ---------------------------------------------------------------------------
# CMS Internet-Only Manual chapters (PDF) and the NCCI Policy Manual (PDF)
# ---------------------------------------------------------------------------
_IOM_FILE = {"100-04": "clm104c{ch:02d}.pdf", "100-02": "bp102c{ch:02d}.pdf", "100-08": "pim83c{ch:02d}.pdf"}


def _pdf_section(text: str, number: str) -> tuple[str | None, str | None]:
    """(heading, body) for a numbered section inside a manual chapter's text."""
    esc = re.escape(number)
    heads = list(re.finditer(r"(?m)^\s*" + esc + r"\s*[-–—]\s*(.+)$", text))
    if not heads:
        return None, None
    heading = " ".join(heads[0].group(1).split())
    # The body is the LAST occurrence (the TOC comes first), up to the next heading of any depth.
    body_start = heads[-1].start()
    nxt = re.search(r"(?m)^\s*\d+(?:\.\d+)*\s*[-–—]\s+\S", text[heads[-1].end():])
    body = text[body_start: heads[-1].end() + (nxt.start() if nxt else len(text))]
    return heading, " ".join(body.split())


def _iom(ident: Identifier) -> tuple[Resolution, Document | None]:
    pub, ch, *sec = ident.value.split(":")
    sec = sec[0] if sec else ""
    fname = _IOM_FILE.get(pub)
    res = Resolution(ident, Exists.UNCHECKED, registry="cms.gov IOM", checked_at=_NOW())
    if not fname:
        return res, None
    url = "https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/" + fname.format(ch=int(ch))
    res.canonical = url
    st, body, _ = http.get(url, timeout=120)
    if st == 404:
        res.exists = Exists.NONEXISTENT; return res, None
    if st != 200 or not body.startswith(b"%PDF"):
        return res, None
    text = _pdftotext(body)
    if text is None:
        res.exists = Exists.EXISTS; res.heading = None
        return res, _doc(ident, "", "cms_iom_pdf", url, "section", "application/pdf", "UNEXTRACTED")
    if not sec:
        m = re.search(r"(?m)^\s*Chapter\s+" + re.escape(ch) + r"\s*[-–—]\s*(.+)$", text)
        res.exists = Exists.EXISTS; res.heading = " ".join(m.group(1).split()) if m else f"Chapter {ch}"
        res.registry_id = f"IOM {pub} ch.{ch}"
        return res, _doc(ident, " ".join(text.split()), "cms_iom_pdf", url, "section", "application/pdf")
    heading, unit = _pdf_section(text, sec)
    if heading is None:
        res.exists = Exists.NONEXISTENT; res.registry_id = f"IOM {pub} ch.{ch} §{sec}"
        return res, None
    res.exists = Exists.EXISTS; res.heading = heading; res.registry_id = f"IOM {pub} ch.{ch} §{sec}"
    return res, _doc(ident, unit, "cms_iom_pdf", url, "section", "application/pdf")


def _ncci(ident: Identifier) -> tuple[Resolution, Document | None]:
    ch, *sec = ident.value.split(":")
    sec = sec[0] if sec else ""
    res = Resolution(ident, Exists.UNCHECKED, registry="cms.gov NCCI", checked_at=_NOW())
    year = dt.date.today().year
    for y in (year, year - 1):
        url = f"https://www.cms.gov/files/document/{int(ch):02d}-chapter{int(ch)}-ncci-medicare-policy-manual-{y}-final.pdf"
        st, body, _ = http.get(url, timeout=120)
        if st == 200 and body.startswith(b"%PDF"):
            break
    else:
        res.exists = Exists.NONEXISTENT if st == 404 else Exists.UNCHECKED
        return res, None
    res.canonical = url; res.extra = {"year": y}
    text = _pdftotext(body)
    if text is None:
        res.exists = Exists.EXISTS
        return res, _doc(ident, "", "ncci_pdf", url, "section", "application/pdf", "UNEXTRACTED")
    if not sec:
        res.exists = Exists.EXISTS; res.heading = f"NCCI Policy Manual Chapter {ch}"
        return res, _doc(ident, " ".join(text.split()), "ncci_pdf", url, "section", "application/pdf")
    heads = list(re.finditer(r"(?m)^\s*" + re.escape(sec) + r"\.\s+([A-Z][^\n]{3,80}?)\s*(?:\.{3,}.*)?$", text))
    if not heads:
        res.exists = Exists.NONEXISTENT; return res, None
    res.exists = Exists.EXISTS; res.heading = " ".join(heads[0].group(1).split())
    res.registry_id = f"NCCI ch.{ch} §{sec}"
    last = heads[-1]
    nxt = re.search(r"(?m)^\s*[A-Z]\.\s+[A-Z][^\n]{3,80}$", text[last.end():])
    unit = text[last.start(): last.end() + (nxt.start() if nxt else len(text))]
    return res, _doc(ident, " ".join(unit.split()), "ncci_pdf", url, "section", "application/pdf")


# ---------------------------------------------------------------------------
# the interface
# ---------------------------------------------------------------------------
_ADAPTERS = {"cfr": _cfr, "orc": _ohio, "oac": _ohio, "cms_iom": _iom, "ncci": _ncci}
_last_doc: dict[str, Document] = {}


def resolve(ident: Identifier) -> Resolution:
    fn = _ADAPTERS.get(ident.system)
    if not fn:
        return Resolution(ident, Exists.UNCHECKED, checked_at=_NOW())
    res, doc = fn(ident)
    if doc is not None:
        _last_doc[ident.system + ":" + ident.value] = doc
    return res


def fetch(res: Resolution) -> Document | None:
    """Law registries hand back the text with the resolution; fetch returns it."""
    if res.exists != Exists.EXISTS:
        return None
    key = res.identifier.system + ":" + res.identifier.value
    if key not in _last_doc:
        resolve(res.identifier)
    return _last_doc.get(key)
