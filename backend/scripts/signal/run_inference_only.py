#!/usr/bin/env python3
"""Run ONE role — INFERENCE — against a draft, and nothing else.

Why this exists. On 2026-09-03 the inference role hit the model's output
ceiling on issue one and blocked the run. Diagnosing it through the full gate
costs $6.59 and twenty-five minutes, because the other five phases re-run to
reach it. This reaches the failing role directly for the price of that one
call, so the question "did it repeat itself or did it find two hundred things"
can be answered without buying the answer to twenty questions nobody asked.

It writes nothing to the gate report and settles nothing. A run of this is a
diagnostic, not a check: the gate is still the only thing that can clear a page.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factcheck_draft as fd


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_inference_only.py <issue-slug> <draft-path>")
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
    print(f"Issue: {slug}   Model: {fd.SIGNAL_MODEL}   Cap: {fd.MAX_OUTPUT_TOKENS:,}\n")

    out = fd.inference(draft)
    if out is None:
        print("\nThe role returned nothing. If it was cut off, the text is saved "
              "under data/signal/truncated/ — read that before changing anything.")
        return 2
    print(json.dumps(out, indent=2)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
