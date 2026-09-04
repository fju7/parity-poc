#!/usr/bin/env python3
"""Run ONE role — EXTRACT — against a draft, and print what it actually returns.

Why this exists. On 2026-09-04 the gate blocked at step one: extraction produced
7,507 output tokens, parsed clean as JSON, and yielded no claims. The run cost
$0.15 and the answer went on the floor, so nobody could say WHAT it returned —
an empty array, an object under a key nobody expected, a list of strings.

Reaching it through the full gate costs the whole run. This reaches the one role
for the price of its own call, prints the shape before anything interprets it,
and writes the raw text to disk either way.

It settles nothing. A run of this is a diagnostic, not a check.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factcheck_draft as fd


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_extract_only.py <issue-slug> <draft-path>")
        return 2
    slug, draft_path = sys.argv[1], Path(sys.argv[2])
    if not draft_path.exists():
        print(f"[ERROR] no such draft: {draft_path}")
        return 2

    fd.enter_issue(slug)
    draft = fd.read_draft(draft_path)
    if not draft:
        return 2
    print(f"Draft: {draft_path.name} ({len(draft):,} chars of prose)")
    print(f"Model: {fd.SIGNAL_MODEL}   Cap: {fd.MAX_OUTPUT_TOKENS:,}\n")

    out = fd.call(fd.EXTRACT_SYSTEM,
                  f"Draft follows.\n\n---\n{draft}\n---",
                  search=False, label="extract-diagnostic",
                  max_tokens=fd.read_budget(draft))

    print("\n--- what came back ---")
    print("type:", type(out).__name__)
    if isinstance(out, dict):
        print("keys:", sorted(out)[:20])
        for k, v in list(out.items())[:6]:
            print(f"  {k}: {type(v).__name__}"
                  + (f", {len(v)} item(s)" if isinstance(v, (list, dict)) else ""))
    elif isinstance(out, list):
        print("length:", len(out))
        if out:
            print("first element type:", type(out[0]).__name__)
            print(json.dumps(out[0], indent=1)[:700])
    elif out is None:
        print("call() returned None — see the error above it")
    where = fd._dump_truncated("extract-diagnostic", json.dumps(out)[:400000]
                               if out is not None else "", None)
    if where:
        print("\nwritten to", where)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
