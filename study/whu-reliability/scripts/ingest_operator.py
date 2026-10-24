#!/usr/bin/env python3
"""Ingest the sources the advisor fetched by hand (route d, scoring prep round 3).

    ingest_operator.py [--incoming DIR]

Route (d) of retrieve_sources.py: the Claude desktop app's built-in browser,
for free pages only, used by the advisor on every source operator_fetch.json
marked free_to_read_but_blocks_automation, whichever system cited it. The
advisor's files and log are in PRIVATE/m1/operator_incoming/: one file per
source, named <source_id>.<ext>, and fetch_log.json (one entry per source: id,
outcome, version_held, bytes, sha256, method, and the addresses tried).

For each entry with outcome "held", the file must exist, be the size the log
says and have the sha256 the log says; any mismatch stops the run with exit 2
and nothing is written. The text both judges read is then decided exactly as
for a script fetch (snapshot.text_of, snapshot.extent): a file the extent rule
calls unreachable is not held. The row keeps its source_id (keyed by the cited
address) and gains a retrieval record with route "d", the version held and
the hash, with the earlier passes kept. An entry with any other outcome stays
unreachable and its outcome is recorded. Free: no model is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import snapshot as SN  # noqa: E402

RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "m1"
CTYPE = {".pdf": "application/pdf", ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def version_kind(note: str | None) -> str | None:
    """The log's version note as one of the words the manifest uses (the note,
    which can name the copy's address, stays in the private manifest only)."""
    n = (note or "").lower()
    for start, kind in (("published", "publishedVersion"), ("accepted", "acceptedVersion"),
                        ("preprint", "submittedVersion"), ("web page", "web page as rendered")):
        if n.startswith(start):
            return kind
    return "unknown" if note else None


def check(entries: list[dict], incoming: Path) -> list[str]:
    bad = []
    for e in entries:
        if e.get("outcome") != "held":
            continue
        files = sorted(incoming.glob(e["id"] + ".*"))
        if len(files) != 1:
            bad.append("%s: %d file(s) in %s" % (e["id"], len(files), incoming))
            continue
        data = files[0].read_bytes()
        if len(data) != e.get("bytes") or hashlib.sha256(data).hexdigest() != e.get("sha256"):
            bad.append("%s: file is %d bytes, sha256 %s; the log says %s bytes, %s"
                       % (e["id"], len(data), hashlib.sha256(data).hexdigest()[:12], e.get("bytes"),
                          (e.get("sha256") or "")[:12]))
    return bad


def ingest(row: dict, e: dict, incoming: Path) -> dict:
    rec = {"at": now(), "route": None, "version": None, "retrieved_from": None,
           "tried": [{"route": "d", "by": "the advisor, in the desktop app's built-in browser",
                      "result": e.get("outcome"), "addresses_tried": e.get("url_tried"),
                      "method": e.get("method")}]}
    if e.get("outcome") == "held":
        f = next(incoming.glob(e["id"] + ".*"))
        data = f.read_bytes()
        ctype = CTYPE.get(f.suffix.lower(), "")
        text = SN.text_of(data)
        ext, why = SN.extent(row["url"], data, text, ctype)
        rec["tried"][0].update(result=ext, why=why, sha256=e["sha256"], bytes=e["bytes"])
        if ext != "unreachable":
            (RUN / "sources" / (row["source_id"] + ".raw")).write_bytes(data)
            (RUN / "sources" / (row["source_id"] + ".txt")).write_text(text, encoding="utf-8")
            rec.update(route="d", version=version_kind(e.get("version_held")), version_note=e.get("version_held"),
                       retrieved_from="operator_incoming/" + f.name)
            row.update(fetched="operator", content_type=ctype, final_url=None,
                       raw_sha256=e["sha256"], raw_bytes=len(data),
                       text_sha256=hashlib.sha256(text.encode()).hexdigest(), text_chars=len(text),
                       extent=ext, extent_why=why, abstract_only=(ext == "abstract only"))
    if row.get("retrieval"):
        rec["earlier_passes"] = row["retrieval"].pop("earlier_passes", []) + [row["retrieval"]]
    row["retrieval"] = rec
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--incoming", default=str(RUN / "operator_incoming"))
    a = ap.parse_args()
    incoming = Path(a.incoming)
    entries = json.loads((incoming / "fetch_log.json").read_text())["entries"]
    mf = RUN / "sources" / "manifest.json"
    rows = json.loads(mf.read_text())
    by = {r["source_id"]: i for i, r in enumerate(rows)}
    bad = check(entries, incoming)
    bad += ["%s: not in the manifest" % e["id"] for e in entries if e["id"] not in by]
    bad += ["%s: already held (extent %s)" % (e["id"], rows[by[e["id"]]]["extent"])
            for e in entries if e["id"] in by and rows[by[e["id"]]]["extent"] != "unreachable"]
    if bad:
        print("STOP: %d problem(s); nothing written" % len(bad))
        for b in bad:
            print("  " + b)
        return 2
    for e in entries:
        i = by[e["id"]]
        rows[i] = ingest(rows[i], e, incoming)
        r = rows[i]
        print("%s  %-13s route %-2s %s" % (r["source_id"], r["extent"], r["retrieval"]["route"] or "-",
                                          "" if r["retrieval"]["route"] else "(%s)" % e.get("outcome")))
    mf.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
