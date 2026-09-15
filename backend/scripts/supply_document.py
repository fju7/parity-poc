"""Offer a hand-fetched file as the document for an identifier (verify/supplied.py).

    python scripts/supply_document.py FILE --id <DOI, PMID, PMCID or NCT> \\
        --url <the address it was fetched from> --by "Fred Ugast"

The operator supplies the DOCUMENT, never the conclusion: the file is admitted
only if the registry names the identifier and the file carries the registry's
title; it then binds at publish exactly as a machine fetch would. Exit 1 on any
refusal. An admission is a post-freeze change: add its row to
docs/signal-corpus-freeze.md (hash, URL, who, which claims moved) and re-run
publish_topic.py for the topic.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--id", required=True, help="DOI / PMID / PMCID / NCT the file is offered for")
    ap.add_argument("--url", required=True, help="the URL the file was fetched from")
    ap.add_argument("--by", required=True, help="who fetched it")
    ap.add_argument("--check", action="store_true", help="run every check, store nothing")
    a = ap.parse_args()
    from verify.supplied import supply
    r = supply(a.file, a.url, a.by, a.id, store=not a.check)
    print(f"{r.status}  sha256={r.sha256}")
    print(" ", r.reason)
    if r.resolution is not None:
        print("  registry:", r.resolution.registry, "|", (r.resolution.heading or "")[:120])
    if r.heading is not None:
        print("  HEADING:", "ok" if r.heading.ok else "REFUSED", "|", (r.heading.evidence or r.heading.reason)[:160])
    if r.record:
        print(json.dumps({k: r.record[k] for k in ("identifier", "supplied_by", "source_url", "retrieved_at", "text_layer", "status") if k in r.record}, indent=1))
    if r.admitted and not a.check:
        print("  stored:", r.record.get("path"), "-- now: freeze-register row, then publish_topic.py <slug>")
    return 0 if r.admitted else 1


if __name__ == "__main__":
    sys.exit(main())
