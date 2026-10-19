#!/usr/bin/env python3
"""Fetch each cited source once and save it as the snapshot both judges see.

Protocol, "Same evidence for both": every cited source is retrieved once by
script and saved with its sha256 and how much of it was readable (full text or
abstract only). Both judges are then given the same text, so one judge reaching
a paywall and the other not cannot create a disagreement.

Usage:
    snapshot.py ITEMS.json OUT_DIR

ITEMS.json is a list of {"item": id, "url": ...}. For each item this writes
OUT_DIR/<item>.raw (the bytes as served), OUT_DIR/<item>.txt (the text the
judges read) and one row in OUT_DIR/manifest.json. Free: no model calls.

READABLE EXTENT. The substance test is WHU's own (source_store.substance): a
full text carries a reference list and a discussion or introduction; an
abstract page has the abstract and neither. A source that is not an article (a
news item, a guideline page, a government recommendation) is its own whole
document, and is "full text" when it yields readable prose. Anything that
yields under MIN_CHARS of text, or a bot wall, is "unreachable": the item is
dropped from the test and counted, never judged on nothing.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
import source_store  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
MIN_CHARS = 800
WALLS = ("just a moment...", "enable javascript and cookies", "access denied",
         "are you a robot", "captcha", "request unsuccessful")
# Hosts whose page is an ARTICLE record: a page there without the paper's body
# is the abstract (or less), never the full document.
ARTICLE_HOSTS = ("nature.com", "jamanetwork.com", "ovid.com", "profiles.wustl.edu",
                 "research.pasteur.fr", "bmj.com", "ncbi.nlm.nih.gov/pmc",
                 "pubmed.ncbi.nlm.nih.gov", "frontiersin.org", "wiley.com",
                 "sciencedirect.com", "springer.com", "researchgate.net",
                 "nutritionconnect.org")
# An abstract is one long paragraph. A record page that carries none is a
# landing page, whatever its length in navigation text.
ABSTRACT_PARA = 400


def html_text(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", t,
               flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</(p|div|li|h\d|tr|section|article)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def extent(url: str, data: bytes, text: str, ctype: str) -> tuple[str, str]:
    low = text[:4000].lower()
    if len(text) < MIN_CHARS:
        return "unreachable", "%d readable characters" % len(text)
    if any(w in low for w in WALLS) and len(text) < 6000:
        return "unreachable", "bot wall or access-denied page"
    kind, why = source_store.substance(data, ctype)
    if kind == "full_text":
        return "full text", why
    if kind == "abstract":
        return "abstract only", why
    if any(h in url for h in ARTICLE_HOSTS):
        longest = max((len(l) for l in text.splitlines()), default=0)
        if longest >= ABSTRACT_PARA:
            return "abstract only", ("article record without the paper's body; longest "
                                     "paragraph %d characters (the abstract): %s" % (longest, why))
        return "unreachable", "article record with neither abstract nor body: " + why
    return "full text", "not an article; the page is the whole document (%d characters)" % len(text)


def source_id(url: str) -> str:
    return "S" + hashlib.sha256(url.encode()).hexdigest()[:12]


def text_of(data: bytes) -> str:
    if data[:5] == b"%PDF-":
        text, how = source_store.text_of(data, "application/pdf", pages=0)
        return text if how == "pdftotext" else ""
    return html_text(data)


def main() -> int:
    """snapshot.py ITEMS.json OUT_DIR [--reuse OLD_DIR]

    One snapshot per SOURCE (keyed by URL), not per item: a sentence citing
    two sources is judged against both, and two sentences citing one source
    read the same bytes. ITEMS.json rows carry "urls" (or a single "url").

    --reuse OLD_DIR takes the bytes already fetched for a URL in an earlier
    round (OLD_DIR/manifest.json) instead of fetching again, so a source is
    retrieved once for the whole prep, as the protocol requires. Extent is
    always re-decided from the stored bytes, never carried over.

    Each row records abstract_only, decided from the stored text by extent():
    True only when the text is an abstract or an article record without the
    paper's body. Unreachable sources are recorded and never judged.
    """
    args = sys.argv[1:]
    reuse = None
    if "--reuse" in args:
        i = args.index("--reuse"); reuse = Path(args[i + 1]); del args[i:i + 2]
    items = json.loads(Path(args[0]).read_text())
    out = Path(args[1]); (out / "sources").mkdir(parents=True, exist_ok=True)
    old: dict[str, Path] = {}
    if reuse:
        for r in json.loads((reuse / "manifest.json").read_text()):
            f = reuse / (r["item"] + ".raw")
            if f.exists():
                old.setdefault(r["url"], f)
    urls = []
    for it in items:
        for u in it.get("urls") or [it["url"]]:
            if u not in urls:
                urls.append(u)
    rows = []
    for url in urls:
        sid = source_id(url)
        row = {"source_id": sid, "url": url}
        try:
            if url in old:
                data = old[url].read_bytes()
                row.update(fetched="reused", reused_from=str(old[url]))
            else:
                row["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en"},
                                 timeout=60, allow_redirects=True)
                row.update(fetched="fetched", status=r.status_code, final_url=r.url,
                           content_type=r.headers.get("content-type", ""))
                if r.status_code >= 400:
                    raise RuntimeError("HTTP %d" % r.status_code)
                data = r.content
            text = text_of(data)
            ext, why = extent(url, data, text, row.get("content_type", ""))
            row.update(raw_sha256=hashlib.sha256(data).hexdigest(), raw_bytes=len(data),
                       text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                       text_chars=len(text), extent=ext, extent_why=why,
                       abstract_only=(ext == "abstract only"))
            (out / "sources" / (sid + ".raw")).write_bytes(data)
            (out / "sources" / (sid + ".txt")).write_text(text, encoding="utf-8")
        except Exception as e:  # unreachable is a finding, not a crash
            row.update(extent="unreachable", extent_why=str(e)[:200], abstract_only=False)
        rows.append(row)
        print("%s %-14s %7s chars  %-8s %s" % (sid, row["extent"], row.get("text_chars", "-"),
                                              row.get("fetched", "-"), url[:70]))
    (out / "sources" / "manifest.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
