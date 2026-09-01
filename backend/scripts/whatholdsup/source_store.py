#!/usr/bin/env python3
"""The document store: every source we have, kept, hashed, and re-readable.

WHY THIS EXISTS
---------------
On 2026-09-01 the operator asked why we do not check every sentence against the
source. The answer was in the ledger:

    24 sources
     3 opened by a person
     8 resting on nothing but "whatever the search tool returned for this URL"

We had never acquired the sources. Each role did its own retrieval, took a
fragment, used it, and threw it away; the next role searched again. The same
paper had been "read" fifteen times and opened zero times. The page was being
checked against a stream of fragments rather than against a library.

A fragment cannot be re-examined. It cannot be diffed against next year's
version. It cannot tell you what it did NOT contain -- which is precisely how
the Shaaban paper's own "29 blocks with block size of four" came to be deleted
from the page as if it were our own arithmetic, and how our observation about
interval width came to be published under Tanguy's name for four days.

It is also cheaper. One page gate run made 68 web searches; the one before it,
72. About $30 was spent in a week repeatedly half-retrieving the same two dozen
documents. Holding them costs one acquisition and then nothing: a claim check
against a file is a string operation.

WHAT IT IS FOR, BEYOND CHECKING
-------------------------------
A correction request arrives in six months about a sentence sourced to a paper.
Either we still have the document that sentence was written from, or we are
reconstructing our own reasoning from a URL that may now resolve to a different
version, a paywall, or nothing. The store is what makes a correction answerable
rather than re-litigated.

WHAT IT DOES NOT DO
-------------------
It does not fetch. Acquisition runs on the operator's machine, with the
operator's own network and access -- see acquire_sources.py. This module owns
the layout, the hashing and the verification, so that "we hold this document"
is a checkable fact and not a field somebody typed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT / "backend" / "data" / "whatholdsup" / "sources"
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

EXT = {"application/pdf": ".pdf", "text/html": ".html", "application/json": ".json",
       "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml"}


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob("WHU-*-%s" % slug))
    if not hits:
        raise SystemExit("no case directory for %r" % slug)
    return hits[0]


def issue_dir(slug: str) -> Path:
    return STORE / slug


def manifest_path(slug: str) -> Path:
    return issue_dir(slug) / "manifest.json"


def load_manifest(slug: str) -> dict:
    p = manifest_path(slug)
    if not p.exists():
        return {"what_this_is": (
            "Every source document this issue is written from, as retrieved, with the "
            "hash of the bytes we actually read. A sentence on the page can be checked "
            "against the file named here, by anyone, without a network. When a "
            "correction request arrives about a sentence, this is what answers it."),
            "held": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"held": {}}


def save_manifest(slug: str, man: dict) -> None:
    issue_dir(slug).mkdir(parents=True, exist_ok=True)
    manifest_path(slug).write_text(json.dumps(man, indent=2, ensure_ascii=False),
                                   encoding="utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def put(slug: str, sid: str, data: bytes, *, url: str, via: str,
        content_type: str = "", note: str = "") -> dict:
    """Store one document's bytes under a source id. Returns its manifest row."""
    ext = EXT.get((content_type or "").split(";")[0].strip())
    if not ext:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) if content_type else None
    if not ext:
        ext = ".pdf" if data[:5] == b"%PDF-" else ".html" if b"<html" in data[:2000].lower() else ".bin"
    issue_dir(slug).mkdir(parents=True, exist_ok=True)
    name = "%s%s" % (sid, ext)
    (issue_dir(slug) / name).write_bytes(data)
    row = {"file": name, "sha256": sha(data), "bytes": len(data), "url": url,
           "retrieved": date.today().isoformat(), "via": via,
           "content_type": content_type, "note": note}
    man = load_manifest(slug)
    man.setdefault("held", {})[sid] = row
    save_manifest(slug, man)
    return row


def put_file(slug: str, sid: str, path: Path, *, url: str, via: str,
             note: str = "") -> dict:
    ct, _ = mimetypes.guess_type(str(path))
    return put(slug, sid, Path(path).read_bytes(), url=url, via=via,
               content_type=ct or "", note=note)


def held(slug: str) -> dict:
    return load_manifest(slug).get("held") or {}


def verify(slug: str) -> tuple[list[str], list[str]]:
    """(intact, broken). A manifest row whose bytes are gone or changed is worse
    than no row: it says we can check something we cannot."""
    intact, broken = [], []
    for sid, row in sorted(held(slug).items()):
        f = issue_dir(slug) / row.get("file", "")
        if not f.exists():
            broken.append("%s: %s is not in the store" % (sid, row.get("file")))
        elif sha(f.read_bytes()) != row.get("sha256"):
            broken.append("%s: %s does not match its recorded hash" % (sid, row.get("file")))
        else:
            intact.append(sid)
    return intact, broken


def sources(slug: str) -> list[dict]:
    p = case_dir(slug) / "sources.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw.get("sources", raw) if isinstance(raw, dict) else raw


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    """Does the ledger's story match what is on disk?"""
    try:
        srcs = sources(slug)
    except Exception as exc:
        return [("source store", WARN, "could not read sources.json: %s" % exc)]
    intact, broken = verify(slug)
    h = set(intact)
    rows = []

    # A source claiming full_text_held with nothing in the store is the exact
    # failure this whole change is about, one level up: a field asserting a read
    # that did not happen.
    lying = [s["id"] for s in srcs
             if ((s.get("access") or {}).get("state") == "full_text_held"
                 and s["id"] not in h)]
    rows.append(("source store matches the ledger", OK if not lying else BAD,
                 "every source claiming a held full text has one in the store"
                 if not lying else
                 "%d source(s) claim full_text_held and are NOT in the store: %s. "
                 "That is a field asserting a read that did not happen, which is the "
                 "failure the state was created to end."
                 % (len(lying), ", ".join(lying))))

    rows.append(("stored documents intact", OK if not broken else BAD,
                 "%d document(s) held, every hash matches" % len(intact)
                 if not broken else
                 "%d stored document(s) missing or altered: %s"
                 % (len(broken), " || ".join(broken[:3]))))

    n = len(srcs)
    frag = [s["id"] for s in srcs if (s.get("access") or {}).get("state") == "fragment_only"]
    unheld = [s["id"] for s in srcs if s["id"] not in h]
    rows.append(("sources we actually hold", OK if len(h) == n else WARN,
                 "%d of %d source documents are in the store%s"
                 % (len(h), n,
                    "" if len(h) == n else
                    " — not held: %s" % ", ".join(unheld[:8]))))
    if frag:
        rows.append(("sources that are only a fragment", WARN,
                     "%d source(s) rest on what a retrieval returned and nobody holds: "
                     "%s. They license the figures that retrieval returned and no "
                     "characterisation of the document."
                     % (len(frag), ", ".join(frag))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="store a document you already have on disk")
    a.add_argument("sid")
    a.add_argument("path")
    a.add_argument("--url", required=True)
    a.add_argument("--via", required=True, help="how it was obtained, and by whom")
    a.add_argument("--note", default="")
    sub.add_parser("status", help="what is held, what is not")
    args = ap.parse_args()

    if args.cmd == "add":
        row = put_file(args.slug, args.sid, Path(args.path), url=args.url,
                       via=args.via, note=args.note)
        print("\n  stored %s -> %s  (%d bytes, sha %s)\n"
              % (args.sid, row["file"], row["bytes"], row["sha256"][:16]))
        return 0

    print()
    for name, state, detail in preflight_rows(args.slug):
        print("  %-8s %-34s %s" % (state, name, detail))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
