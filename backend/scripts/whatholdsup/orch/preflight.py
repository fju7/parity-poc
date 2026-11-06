"""The orchestrator's preflight rows (docs/whu-orchestrator.md §2.5, §3), for orchestrated issues only
(issue.json "orchestrated": true). An issue the orchestrator did not run gets neither row, so the lean test's
pages are judged exactly as before.

  "records match the orchestrator's chain": every record's current hash equals the last hash the chain wrote,
      and no frozen field moved (orch/chain.py).
  "overstatement check complete": every bound sentence on the page has a verdict for its current text and
      passage, and none judged "yes" is still on the page (orch/overstatement.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

OK, BAD = "ok", "BLOCKED"
CHAIN_ROW = "records match the orchestrator's chain"
# Files the preflight itself appends to while it runs (its own logs); they cannot have a chain hash yet.
PREFLIGHT_WRITES = ("rulings/applied_check.jsonl",)


def orchestrated(slug: str) -> bool:
    import source_store as store
    try:
        return json.loads((store.case_dir(slug) / "issue.json").read_text(encoding="utf-8")).get("orchestrated") is True
    except (Exception, SystemExit):
        return False


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    if not orchestrated(slug):
        return []
    import source_store as store
    import bindings as B
    import ruling as R
    import audit_stage as A
    from orch import chain as CH
    from orch import overstatement as O
    case = store.case_dir(slug)
    bad = [b for b in CH.check(case, slug) if not any(b.endswith(" " + p) for p in PREFLIGHT_WRITES)]
    rows = [(CHAIN_ROW, BAD, "%d record(s) differ from the chain: %s" % (len(bad), "; ".join(bad[:4])))
            if bad else (CHAIN_ROW, OK, "every record matches the hash the chain last wrote")]
    rows.append(O.preflight_row(case, B.page_sentences(slug), B.load(slug).get("bindings") or {},
                                R.held_texts(slug), A.locate))
    return rows
