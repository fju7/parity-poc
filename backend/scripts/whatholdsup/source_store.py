#!/usr/bin/env python3
"""The library: every source document we have ever held, kept and re-readable.

WHY THIS EXISTS
---------------
On 2026-09-01 the operator asked why we do not check every sentence against the
source. The ledger answered:

    24 sources
     3 opened by a person
     8 resting on nothing but "whatever the search tool returned for this URL"

We had never acquired the sources. Each role did its own retrieval, took a
fragment, used it and threw it away; the next role searched again. The same
paper had been "read" fifteen times and opened zero times.

A fragment cannot be re-examined, cannot be diffed against next year's version,
and cannot tell you what it did NOT contain -- which is exactly how the Shaaban
paper's own "29 blocks with block size of four" was deleted from the page as if
we had invented it.

A LIBRARY, NOT A PILE
---------------------
Documents are content-addressed: one copy per distinct set of bytes, ever, under
its own sha256. Two things follow, and both are the operator's reasons rather
than mine.

  A DOCUMENT CITED BY THREE ISSUES IS STORED ONCE and each issue points at it.
  The library is the corpus; an issue's manifest is an index into it.

  A DOCUMENT THAT CHANGES IS NOT OVERWRITTEN. A corrected paper, a new guideline
  version, a registry record updated after we published -- each is new bytes,
  so a new hash, and BOTH ARE KEPT. When a correction request or a changelog
  event arrives about a sentence, the question "what did this say when we read
  it" has an answer, and "what changed since" is a diff rather than an argument.

IDENTITY IS CONFIRMED, NOT ASSUMED
----------------------------------
The first version of this module rejected documents by a blocklist of wall
phrases -- "captcha", "subscribe to continue". Within the hour it stored two
PubMed cookie-consent pages as full text, because "cookies required" was not on
the list. A blocklist can only refuse what somebody has already been caught by.

So the test is now positive, which is the same correction this project has made
three times in other places: the bytes must contain something that IDENTIFIES
the document -- a distinctive run of its title, its DOI, its PMID, its NCT
number. A page that cannot show it is the document is not stored as one, whether
or not it looks like a wall.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "backend" / "data" / "whatholdsup" / "library"
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

EXT = {"application/pdf": ".pdf", "text/html": ".html", "application/json": ".json",
       "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml"}

STOP = {"the", "a", "an", "of", "and", "or", "in", "for", "with", "on", "to", "as",
        "at", "by", "from", "is", "are", "was", "were", "not", "no", "vs", "versus"}


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob("WHU-*-%s" % slug))
    if not hits:
        raise SystemExit("no case directory for %r" % slug)
    return hits[0]


# ---------------------------------------------------------------------------
# the library
# ---------------------------------------------------------------------------

def docs_dir() -> Path:
    return LIB / "docs"


def index_path() -> Path:
    return LIB / "index.json"


def issue_index_path(slug: str) -> Path:
    return LIB / "issues" / ("%s.json" % slug)


def _load(p: Path, default: dict) -> dict:
    if not p.exists():
        return dict(default)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)


def load_index() -> dict:
    return _load(index_path(), {
        "what_this_is": (
            "Every source document this publication has ever held, one entry per "
            "distinct set of bytes. Content-addressed, so a document cited by several "
            "issues is stored once, and a document that changes is kept ALONGSIDE the "
            "version we read rather than replacing it. That is what makes 'what did "
            "this say when we wrote the sentence' answerable when a correction request "
            "arrives."),
        "docs": {}})


def load_issue_index(slug: str) -> dict:
    return _load(issue_index_path(slug), {
        "what_this_is": ("Which document in the library each of this issue's sources "
                         "points at. The library holds the bytes; this says what we "
                         "were reading when we wrote the page."),
        "issue": slug, "sources": {}})


def save_index(ix: dict) -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    index_path().write_text(json.dumps(ix, indent=2, ensure_ascii=False), encoding="utf-8")


def save_issue_index(slug: str, ix: dict) -> None:
    issue_index_path(slug).parent.mkdir(parents=True, exist_ok=True)
    issue_index_path(slug).write_text(json.dumps(ix, indent=2, ensure_ascii=False),
                                      encoding="utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def doc_path(digest: str, ext: str) -> Path:
    return docs_dir() / digest[:2] / (digest + ext)


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

def identifying_tokens(src: dict) -> list[str]:
    """Strings that would appear in the document if these bytes really are it."""
    out = []
    for m in re.finditer(r"NCT\d{8}", json.dumps(src), re.I):
        out.append(m.group(0))
    for m in re.finditer(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", src.get("url", "") + " "
                         + src.get("title", "")):
        out.append(m.group(0).rstrip(".,)"))
    for m in re.finditer(r"PMID[: ]*(\d{6,9})|PMC(\d{6,9})", json.dumps(src)):
        out.append(m.group(0))
    title = src.get("title", "")
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9'-]{3,}", title)
             if w.lower() not in STOP]
    out.extend(words[:12])
    seen, uniq = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    return uniq


def pdftotext_path() -> str | None:
    """Find pdftotext, including where PATH will not.

    launchd starts jobs with a minimal PATH that does not include
    /opt/homebrew/bin, so shutil.which() returns nothing on a Mac where poppler
    is installed and working. The acquisition job would then report "pdftotext
    is not installed", refuse every PDF it fetched, and be believed -- a tool
    reporting an absence it was not in a position to observe, which is the error
    this repository has now recorded five times.
    """
    import shutil as _sh
    found = _sh.which("pdftotext")
    if found:
        return found
    for p in ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext",
              "/usr/bin/pdftotext", "/opt/local/bin/pdftotext"):
        if Path(p).exists():
            return p
    return None


def text_of(data: bytes, content_type: str = "") -> tuple[str, str]:
    """The document's readable text, for the identity test.

    A PDF's text is compressed, so decoding its bytes as latin-1 finds almost
    nothing -- which is how the first version of this test REFUSED two genuine
    FDA prescribing-information PDFs, reporting 1 of 4 title words. Refusing a
    real document is the safer error and it is still an error: it would have
    sent a person to hunt for a file we already had.

    pdftotext is used where present, and where it is not the caller is told the
    difference rather than being handed a confident-looking failure.
    """
    if data[:5] != b"%PDF-":
        return data.decode("utf-8", "replace"), "text"
    import subprocess
    import tempfile
    exe = pdftotext_path()
    if exe:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(data); tmp = fh.name
        try:
            out = subprocess.run([exe, "-q", "-l", "8", tmp, "-"], capture_output=True,
                                 timeout=60)
            if out.returncode == 0 and len(out.stdout) > 200:
                return out.stdout.decode("utf-8", "replace"), "pdftotext"
        except Exception:
            pass
        finally:
            try:
                Path(tmp).unlink()
            except Exception:
                pass
    # Nothing came out. The raw bytes are returned so a title in an uncompressed
    # stream can still match, but the CALLER IS TOLD the text was never
    # extracted -- so it can say "nobody here can read this" instead of "this is
    # the wrong document". Those are different statements and only one is true.
    return data.decode("latin-1", "replace"), "unextracted"


def identifies(data: bytes, src: dict, content_type: str = "") -> tuple[bool, str]:
    """Do these bytes show they ARE this document?

    Positive test, deliberately. The blocklist version of this stored two PubMed
    cookie-consent pages as full text within an hour of being written, because
    "cookies required" was not a phrase anyone had been caught by yet. A
    blocklist can only refuse what has already gone wrong once.
    """
    if len(data) < 2000:
        return False, "only %d bytes" % len(data)
    raw, how = text_of(data, content_type)
    hay = raw.lower()
    toks = identifying_tokens(src)
    hard = [t for t in toks if re.match(r"(NCT\d{8}|10\.\d{4,9}/|PMID|PMC\d)", t, re.I)]
    for t in hard:
        if t.lower() in hay:
            return True, "contains its identifier %s" % t
    words = [t for t in toks if t not in hard]
    hits = [w for w in words if w.lower() in hay]
    if len(words) >= 3 and len(hits) >= max(3, (len(words) + 1) // 2):
        return True, "contains %d of %d distinctive title words" % (len(hits), len(words))
    if how == "unextracted":
        # No text came out. That is not "this is the wrong document", it is
        # "nobody here can read this document", and saying the first when you
        # mean the second is the error this whole apparatus exists to stop.
        return False, ("no text could be extracted from this PDF (pdftotext %s), so "
                       "identity could not be checked either way — look at it yourself "
                       "and use --force if it is right"
                       % ("at %s failed on it" % pdftotext_path() if pdftotext_path()
                          else "was not found on this machine"))
    return False, ("nothing in these bytes identifies them as this document "
                   "(%d of %d title words, no DOI/PMID/NCT match)"
                   % (len(hits), len(words)))


# ---------------------------------------------------------------------------
# putting things in
# ---------------------------------------------------------------------------

def put(slug: str, sid: str, data: bytes, *, url: str, via: str,
        content_type: str = "", title: str = "", note: str = "") -> dict:
    digest = sha(data)
    ext = EXT.get((content_type or "").split(";")[0].strip()) or (
        ".pdf" if data[:5] == b"%PDF-" else
        ".json" if data[:1] in (b"{", b"[") else
        ".html" if b"<html" in data[:2000].lower() else ".bin")
    p = doc_path(digest, ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(data)

    ix = load_index()
    row = ix.setdefault("docs", {}).setdefault(digest, {
        "file": str(p.relative_to(LIB)), "bytes": len(data),
        "content_type": content_type, "first_held": date.today().isoformat(),
        "urls": [], "titles": [], "used_by": [], "note": note})
    if url and url not in row["urls"]:
        row["urls"].append(url)
    if title and title not in row["titles"]:
        row["titles"].append(title)
    tag = "%s:%s" % (slug, sid)
    if tag not in row["used_by"]:
        row["used_by"].append(tag)
    save_index(ix)

    iix = load_issue_index(slug)
    prior = (iix.get("sources") or {}).get(sid) or {}
    versions = list(prior.get("superseded") or [])
    alsos = list(prior.get("also_held") or [])
    if prior.get("sha256") and prior["sha256"] != digest:
        # SUPERSEDED AND ALSO_HELD ARE DIFFERENT THINGS, and conflating them
        # destroys the reason for keeping old bytes at all.
        #
        # The Shaaban paper arrived twice on 2026-09-01: as Europe PMC full-text
        # XML from acquisition, and as the published PDF the operator supplied.
        # The first version of this recorded the XML as "superseded" by the PDF.
        # They are the same paper in two representations. A later diff of one
        # against the other would report that everything changed, which would
        # make the version history worse than useless -- it would make it
        # misleading, on precisely the question it exists to answer.
        #
        # SUPERSEDED means the document itself changed: same representation,
        # different bytes -- a corrected paper, a new guideline version, a
        # registry record updated after we published. That is a real diff and a
        # real changelog event.
        #
        # ALSO_HELD means another form of the same thing.
        prior_ext = Path(prior.get("file", "")).suffix
        entry = {"sha256": prior["sha256"], "file": prior.get("file"),
                 "held": prior.get("held"), "url": prior.get("url"),
                 "recorded": date.today().isoformat()}
        if prior_ext and prior_ext != ext:
            alsos.append(entry)
        else:
            entry["replaced"] = date.today().isoformat()
            versions.append(entry)
    iix.setdefault("sources", {})[sid] = {
        "sha256": digest, "file": row["file"], "bytes": len(data), "url": url,
        "held": date.today().isoformat(), "via": via, "note": note,
        "superseded": versions, "also_held": alsos}
    save_issue_index(slug, iix)
    return {"sha256": digest, "file": row["file"], "bytes": len(data),
            "retrieved": date.today().isoformat(), "url": url}


def put_file(slug: str, sid: str, path: Path, *, url: str, via: str,
             title: str = "", note: str = "") -> dict:
    ct, _ = mimetypes.guess_type(str(path))
    return put(slug, sid, Path(path).read_bytes(), url=url, via=via,
               content_type=ct or "", title=title, note=note)


def held(slug: str) -> dict:
    return load_issue_index(slug).get("sources") or {}


def verify(slug: str) -> tuple[list[str], list[str]]:
    intact, broken = [], []
    for sid, row in sorted(held(slug).items()):
        f = LIB / row.get("file", "")
        if not f.exists():
            broken.append("%s: %s is not in the library" % (sid, row.get("file")))
        elif sha(f.read_bytes()) != row.get("sha256"):
            broken.append("%s: %s does not match its recorded hash" % (sid, row.get("file")))
        else:
            intact.append(sid)
    return intact, broken


def sources(slug: str) -> list[dict]:
    raw = json.loads((case_dir(slug) / "sources.json").read_text(encoding="utf-8"))
    return raw.get("sources", raw) if isinstance(raw, dict) else raw


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    try:
        srcs = sources(slug)
    except Exception as exc:
        return [("source library", WARN, "could not read sources.json: %s" % exc)]
    intact, broken = verify(slug)
    h = set(intact)
    rows = []
    lying = [s["id"] for s in srcs
             if ((s.get("access") or {}).get("state") == "full_text_held" and s["id"] not in h)]
    rows.append(("library matches the ledger", OK if not lying else BAD,
                 "every source claiming a held full text has one in the library"
                 if not lying else
                 "%d source(s) claim full_text_held with nothing in the library: %s — a "
                 "field asserting a read that did not happen"
                 % (len(lying), ", ".join(lying))))
    rows.append(("held documents intact", OK if not broken else BAD,
                 "%d document(s) in the library, every hash matches" % len(intact)
                 if not broken else
                 "%d held document(s) missing or altered: %s"
                 % (len(broken), " || ".join(broken[:3]))))
    unheld = [s["id"] for s in srcs if s["id"] not in h]
    rows.append(("sources we hold", OK if not unheld else WARN,
                 "all %d source documents are in the library" % len(srcs) if not unheld else
                 "%d of %d held — not held: %s" % (len(h), len(srcs), ", ".join(unheld[:8]))))
    frag = [s["id"] for s in srcs if (s.get("access") or {}).get("state") == "fragment_only"]
    if frag:
        rows.append(("sources that are only a fragment", WARN,
                     "%d source(s) rest on what a retrieval returned and nobody holds: %s"
                     % (len(frag), ", ".join(frag))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="put a document you already have into the library")
    a.add_argument("sid"); a.add_argument("path")
    a.add_argument("--url", required=True)
    a.add_argument("--via", required=True, help="how it was obtained, and by whom")
    a.add_argument("--note", default="")
    a.add_argument("--force", action="store_true",
                   help="store even if the bytes do not identify themselves")
    sub.add_parser("status")
    sub.add_parser("library", help="everything the library holds, across issues")
    args = ap.parse_args()

    if args.cmd == "add":
        src = next((s for s in sources(args.slug) if s.get("id") == args.sid), {})
        data = Path(args.path).read_bytes()
        ok, why = identifies(data, src)
        if not ok and not args.force:
            print("\n  REFUSED: %s\n  Use --force only if you have looked at the file "
                  "yourself.\n" % why)
            return 2
        row = put_file(args.slug, args.sid, Path(args.path), url=args.url, via=args.via,
                       title=src.get("title", ""), note=args.note)
        print("\n  held %s -> %s  (%d bytes, sha %s)\n  %s\n"
              % (args.sid, row["file"], row["bytes"], row["sha256"][:16],
                 why if ok else "stored with --force, identity NOT confirmed"))
        return 0

    if args.cmd == "library":
        ix = load_index()
        print("\n  %d document(s) in the library\n" % len(ix.get("docs", {})))
        for dg, r in sorted(ix.get("docs", {}).items(), key=lambda x: -x[1]["bytes"]):
            print("  %s  %9d B  %-28s %s" % (dg[:12], r["bytes"],
                                             ", ".join(r["used_by"])[:28],
                                             (r["titles"] or [""])[0][:44]))
        print()
        return 0

    print()
    for name, state, detail in preflight_rows(args.slug):
        print("  %-8s %-32s %s" % (state, name, detail))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
