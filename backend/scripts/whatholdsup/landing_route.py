"""A landing page's own PDF link (advisor's rulings on the S006 landing-page route, 2026-11-25/26).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): S006 (Kuper et al. 2018, the DFID rapid evidence
assessment) was recorded at its gov.uk Research for Development Outputs page. acquire fetched it, source_store
classed it a landing page ("a page ABOUT the document, not the document"), and nothing else was tried, although the
page links the report's PDF. Ruled: when source_store classes a fetched page as a landing page --

  * THE LINK. The page's `citation_pdf_url` meta if present; otherwise the PDF links whose filename or link text
    passes the title rule (title_match.title_matches) against the source's title. In either case only a link whose
    host is on the page's own REGISTRABLE DOMAIN, read strictly by the Public Suffix List (ICANN and private
    sections both: gov.uk and service.gov.uk are suffixes, so www.gov.uk and assets.publishing.service.gov.uk are
    two registrable domains). Exactly one candidate: taken. More than one: taken only if EXACTLY ONE has link text
    containing the whole source title (both title_match.normalise()d); otherwise refused. None: refused. No other
    tie-break.
  * REDIRECTS. Followed one hop at a time and recorded (the full chain and the final URL). A hop to another
    registrable domain is followed only if the landing page itself links one or more PDFs on that exact host; any
    other cross-domain redirect is refused. At most MAX_HOPS hops.
  * ROBOTS AND TDM before each request for the document (so for the final host before the document is fetched):
    robots.txt must allow it and /.well-known/tdmrep.json must reserve nothing (open_copy.robots / tdm_site). Never
    past a wall (401/403/429 ends the route); the honest user agent (tls.USER_AGENT), nothing retried with other
    headers.
  * IDENTITY. The fetched PDF must pass the normal held check (source_store.held_check), as any copy.
  * LICENCE. The site's statement counts only after the PDF's own text has been read. "All rights reserved", or a
    licence statement naming anything but an Open Government Licence or a Creative Commons licence: refused. An
    OGL / CC licence stated in the document: held, recorded "site licence <name>, document states <name>". The
    document silent: held only if the site states a licence, recorded "site licence <name>, document silent". The
    site silent and the document silent: refused (no licence stated anywhere).

The Public Suffix List is read from backend/data/whatholdsup/public_suffix_list.dat (publicsuffix.org, MPL 2.0; its
VERSION line is recorded in every route record), never fetched during a run.
"""
from __future__ import annotations

import html as _html
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import open_copy as OC
import title_match as TM
import tls

ROUTE = "landing page PDF link"
PSL = Path(__file__).resolve().parents[2] / "data" / "whatholdsup" / "public_suffix_list.dat"
MAX_HOPS = 5
REDIRECTS = (301, 302, 303, 307, 308)

_rules = None


def _load():
    global _rules
    if _rules is None:
        normal, wild, exc, version = set(), set(), set(), None
        for line in PSL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("// VERSION:"):
                version = line.split(":", 1)[1].strip()
            if not line or line.startswith("//"):
                continue
            rule = line.split()[0].lower()
            if not rule.isascii():                       # the list's IDN rules, matched against punycode hosts
                try:
                    rule = ".".join(("!" if i == 0 and lab.startswith("!") else "") +
                                    lab.lstrip("!").encode("idna").decode("ascii") if lab not in ("*",) else lab
                                    for i, lab in enumerate(rule.split(".")))
                except UnicodeError:
                    continue
            if rule.startswith("!"):
                exc.add(rule[1:])
            elif rule.startswith("*."):
                wild.add(rule[2:])
            else:
                normal.add(rule)
        _rules = (normal, wild, exc, version)
    return _rules


def psl_version() -> str | None:
    return _load()[3]


def public_suffix(host: str) -> str:
    """The public suffix of HOST by the PSL algorithm (exception rules win; else the longest matching rule; else the
    implicit "*" rule, the last label)."""
    normal, wild, exc, _v = _load()
    labels = (host or "").lower().rstrip(".").split(".")
    for i in range(len(labels)):
        cand = ".".join(labels[i:])
        if cand in exc:
            return ".".join(labels[i + 1:])
    best = labels[-1:]
    for i in range(len(labels)):
        cand = ".".join(labels[i:])
        rest = ".".join(labels[i + 1:])
        if (cand in normal or (i + 1 < len(labels) and rest in wild)) and len(labels) - i > len(best):
            best = labels[i:]
    return ".".join(best)


def registrable(host: str) -> str | None:
    """The registrable domain (the public suffix plus one label), or None if HOST is itself a public suffix. An IP
    address is its own registrable domain."""
    host = (host or "").lower().rstrip(".")
    if not host:
        return None
    if re.fullmatch(r"[\d.]+|\[?[0-9a-f:]+\]?", host):
        return host
    suf = public_suffix(host)
    if host == suf:
        return None
    lead = host[: -len(suf) - 1].split(".")[-1]
    return "%s.%s" % (lead, suf)


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url or "").hostname or "").lower()


# ---- the page ---------------------------------------------------------------------------------------------------

class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.meta_pdf, self.licence_links = [], [], []
        self._a = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("name", "").lower() == "citation_pdf_url" and a.get("content"):
            self.meta_pdf.append(a["content"].strip())
        if tag == "a" and a.get("href"):
            self._a = {"href": a["href"].strip(), "type": a.get("type", ""), "rel": a.get("rel", ""), "text": []}

    def handle_data(self, data):
        if self._a is not None:
            self._a["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._a is not None:
            self._a["text"] = re.sub(r"\s+", " ", "".join(self._a["text"])).strip()
            self.links.append(self._a)
            if "license" in self._a["rel"].lower().split():
                self.licence_links.append(self._a)
            self._a = None


def _is_pdf(link: dict, url: str) -> bool:
    return urllib.parse.urlsplit(url).path.lower().endswith(".pdf") or "pdf" in (link.get("type") or "").lower()


def _filename_words(url: str) -> str:
    name = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
    return re.sub(r"[_\-.+]+", " ", re.sub(r"\.pdf$", "", name, flags=re.I)).strip()


def parse(page: bytes, page_url: str) -> dict:
    p = _Page()
    p.feed((page or b"").decode("utf-8", "replace"))
    pdfs = []
    for l in p.links:
        u = urllib.parse.urljoin(page_url, _html.unescape(l["href"]))
        if urllib.parse.urlsplit(u).scheme in ("http", "https") and _is_pdf(l, u):
            pdfs.append({"url": u, "text": l["text"], "host": _host(u)})
    meta = [urllib.parse.urljoin(page_url, m) for m in p.meta_pdf]
    return {"pdf_links": pdfs, "citation_pdf_url": meta, "licence_links": p.licence_links,
            "text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", (page or b"").decode("utf-8", "replace")))}


def choose(parsed: dict, page_url: str, title: str) -> tuple[dict | None, dict]:
    """(the chosen link or None, the record of what was considered and why)."""
    home = registrable(_host(page_url))
    rec = {"page": page_url, "page_domain": home, "psl_version": psl_version(), "candidates": []}
    if parsed["citation_pdf_url"]:
        rec["from"] = "citation_pdf_url meta"
        for u in dict.fromkeys(parsed["citation_pdf_url"]):
            same = registrable(_host(u)) == home
            rec["candidates"].append({"url": u, "host": _host(u), "same_domain": same, "passes": same,
                                      "why": "citation_pdf_url" if same else "another registrable domain"})
    else:
        rec["from"] = "PDF links passing the title rule"
        seen = set()
        for l in parsed["pdf_links"]:
            if l["url"] in seen:
                continue
            seen.add(l["url"])
            same = registrable(l["host"]) == home
            t_ok, t_r, _s = TM.title_matches(title, l["text"]) if l["text"] else (False, 0.0, set())
            f_ok, f_r, _s = TM.title_matches(title, _filename_words(l["url"]))
            rec["candidates"].append({"url": l["url"], "host": l["host"], "text": l["text"][:200],
                                      "same_domain": same, "text_ratio": round(t_r, 3), "filename_ratio": round(f_r, 3),
                                      "passes": same and (t_ok or f_ok)})
    passing = [c for c in rec["candidates"] if c["passes"]]
    if not passing:
        rec["outcome"] = "refused: no %s on the page's registrable domain (%s)" % (
            "citation_pdf_url" if rec["from"].startswith("citation") else "PDF link passing the title rule", home)
        return None, rec
    if len(passing) == 1:
        rec["chosen_by"] = "the only candidate"
        return passing[0], rec
    whole = TM.normalise(title)
    full = [c for c in passing if whole and whole in TM.normalise(c.get("text") or "")]
    if len(full) == 1:
        rec["chosen_by"] = "tie-break: the only one of %d candidates whose link text contains the whole title" % len(
            passing)
        return full[0], rec
    rec["outcome"] = ("refused: %d candidates pass the title rule and %d have link text containing the whole title "
                      "(exactly one is required)" % (len(passing), len(full)))
    return None, rec


# ---- the fetch --------------------------------------------------------------------------------------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def step(url: str, timeout: int = 45) -> tuple[int, str | None, bytes, str]:
    """One request, redirects NOT followed: (status, Location or None, body, content type). Raises HTTPError for a
    4xx/5xx, as urllib does."""
    op = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=tls.context()))
    req = urllib.request.Request(url, headers={"User-Agent": tls.USER_AGENT,
                                               "Accept": "application/pdf,*/*;q=0.8"})
    try:
        r = op.open(req, timeout=timeout)
        return r.status, r.headers.get("Location"), r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        if e.code in REDIRECTS:
            return e.code, e.headers.get("Location"), b"", e.headers.get("Content-Type", "")
        raise


# ---- the licence ------------------------------------------------------------------------------------------------

OGL = re.compile(r"\bOpen Government Licen[cs]e(?:\s+(?:for public sector information\s+)?v(?:ersion)?\s*\.?\s*(\d(?:\.\d)?))?",
                 re.I)
CC = re.compile(r"\b(?:Creative Commons(?: Attribution[A-Za-z\- ]*?)?(?:\s+(\d\.\d))?(?: International)?(?: Licen[cs]e)?"
                r"|CC[ \-](?:BY|0)(?:[ \-](?:NC|ND|SA)){0,2}(?:[ \-]?(\d\.\d))?)", re.I)
RESERVED = re.compile(r"\ball rights reserved\b", re.I)
LICENCE_STATEMENT = re.compile(r"\b(?:licen[cs]ed under|under the [\w .\-]{0,60}?licen[cs]e|licen[cs]e:)", re.I)


def _name(m) -> str:
    s = re.sub(r"\s+", " ", m.group(0)).strip()
    return s


def licence_names(text: str) -> list[str]:
    return [_name(m) for m in OGL.finditer(text or "")] + [_name(m) for m in CC.finditer(text or "")]


def site_licence(parsed: dict) -> str | None:
    """The site's licence: an <a rel="license"> naming an OGL / CC licence, else the page text naming one."""
    for l in parsed["licence_links"]:
        names = licence_names(l["text"])
        if names:
            return names[0]
    names = licence_names(parsed["text"])
    return names[0] if names else None


def document_licence(text: str) -> tuple[str, str | None]:
    """("reserved" | "other" | "states" | "silent", the words)."""
    m = RESERVED.search(text or "")
    if m:
        return "reserved", re.sub(r"\s+", " ", text[max(0, m.start() - 80): m.end() + 20]).strip()
    names = licence_names(text)
    if names:
        return "states", names[0]
    m = LICENCE_STATEMENT.search(text or "")
    if m:
        return "other", re.sub(r"\s+", " ", text[max(0, m.start() - 40): m.end() + 80]).strip()
    return "silent", None


def licence_decision(site: str | None, doc_text: str) -> tuple[bool, dict]:
    kind, words = document_licence(doc_text)
    rec = {"site": site, "document": kind, "document_words": words}
    if kind == "reserved":
        return False, dict(rec, line="refused: the document says all rights reserved (%s)" % words)
    if kind == "other":
        return False, dict(rec, line="refused: the document states a licence that is not OGL or CC (%s)" % words)
    if kind == "states":
        return True, dict(rec, line="site licence %s, document states %s" % (site or "none stated", words))
    if site:
        return True, dict(rec, line="site licence %s, document silent" % site)
    return False, dict(rec, line="refused: neither the site nor the document states a licence")


# ---- the route --------------------------------------------------------------------------------------------------

def find(page: bytes, page_url: str, src: dict, held_check, fetch, stepper=None, text_of=None) -> dict:
    """Try the landing page's own PDF link. FETCH(url) -> (bytes, ct, final), raising urllib errors (robots.txt and
    tdmrep.json); STEPPER(url) -> (status, location, body, ct), one hop; HELD_CHECK(bytes, ct) -> (ok, check);
    TEXT_OF(bytes, ct) -> the document's text. Returns {"record": ...} and, when held, "data", "ct", "final",
    "check", "licence"."""
    stepper = stepper or step
    if text_of is None:
        import source_store as store
        text_of = lambda d, c: store.text_of(d, c, pages=0)[0]          # noqa: E731
    parsed = parse(page, page_url)
    chosen, rec = choose(parsed, page_url, src.get("title") or "")
    rec["route"] = ROUTE
    if chosen is None:
        return {"record": rec}
    rec["chosen"] = chosen["url"]
    home = registrable(_host(page_url))
    pdf_hosts = {l["host"] for l in parsed["pdf_links"]}
    chain, url = [], chosen["url"]
    rec["chain"] = chain
    for _hop in range(MAX_HOPS + 1):
        h = _host(url)
        hop = {"url": url, "host": h}
        chain.append(hop)
        if registrable(h) != home and h not in pdf_hosts:
            rec["outcome"] = ("refused: a redirect to %s, another registrable domain on which the landing page links "
                              "no PDF" % h)
            return {"record": rec}
        ok, why = OC.robots(url, fetch)
        hop["robots"] = why
        if not ok:
            rec["outcome"] = "refused: %s" % why
            return {"record": rec}
        reserved, why = OC.tdm_site(url, fetch)
        hop["tdm"] = why
        if reserved:
            rec["outcome"] = "refused: %s" % why
            return {"record": rec}
        try:
            status, loc, body, ct = stepper(url)
        except urllib.error.HTTPError as e:
            hop["status"] = e.code
            rec["outcome"] = ("refused: HTTP %d: a wall, not passed" % e.code) if e.code in OC.WALL_CODES else \
                "refused: HTTP %d" % e.code
            return {"record": rec}
        except (urllib.error.URLError, OSError, ssl.SSLError) as e:
            hop["status"] = type(e).__name__
            rec["outcome"] = "refused: %s" % type(e).__name__
            return {"record": rec}
        hop["status"] = status
        if status in REDIRECTS:
            if not loc:
                rec["outcome"] = "refused: HTTP %d with no Location" % status
                return {"record": rec}
            hop["location"] = loc
            url = urllib.parse.urljoin(url, loc)
            continue
        break
    else:
        rec["outcome"] = "refused: more than %d redirects" % MAX_HOPS
        return {"record": rec}
    rec["final_url"] = url
    if OC.tdm_page(body):
        rec["outcome"] = "refused: the document reserves text and data mining (tdm-reservation)"
        return {"record": rec}
    held, check = held_check(body, ct)
    if not held:
        rec["outcome"] = "refused: not the document: %s" % check.get("why")
        return {"record": rec}
    ok, lic = licence_decision(site_licence(parsed), text_of(body, ct))
    rec["licence"] = lic
    if not ok:
        rec["outcome"] = lic["line"]
        return {"record": rec}
    rec["outcome"] = "held from the landing page's PDF link (%s)" % lic["line"]
    return {"record": rec, "data": body, "ct": ct, "final": url, "check": check, "licence": lic}
