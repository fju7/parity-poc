#!/usr/bin/env python3
"""Re-derive a finished run's page and preflight from its records by code only (advisor's ruling 3 on P222).

    orch/run_env.py <slug> -- python orch/rederive.py <slug> --label TEXT [--premise-page]

Re-renders the page's generated blocks (question, limits, readers' list) from the records exactly as the
orchestrator's _rerender does, re-binds the readers'-list lines, then runs `publish.py check <slug>`. With
--premise-page it instead builds the premise page (premise_page.py) from the records and runs the check on that.
No model call is possible: the check runs with every model key removed from its environment, and the spend
ledger's line count is compared before and after (a change stops the script, exit 1). The result is appended to
the run record (orchestrator/run_paid.json, "rederived") with LABEL, the page hashes before and after, the outcome
and every STOP row.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
LEDGER = ROOT / "backend" / "data" / "spend" / "ledger.jsonl"
KEYS = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def _lines(p: Path) -> int:
    return sum(1 for _ in p.open(encoding="utf-8")) if p.exists() else 0


def check(slug: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in KEYS and not k.startswith("WHU_ORCH_")}
    env["WHU_LEAN"] = "1"
    r = subprocess.run([sys.executable, str(HERE / "publish.py"), "check", slug], cwd=str(ROOT), env=env,
                       capture_output=True, text=True)
    stops = [" ".join(ln.split()) for ln in r.stdout.splitlines() if ln.lstrip().startswith("STOP")]
    return {"exit": r.returncode, "outcome": "Ready." if r.stdout.strip().endswith("Ready.") else "Not Ready",
            "stops": stops, "tail": r.stdout[-4000:]}


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or "--label" not in a:
        print(__doc__)
        return 2
    slug, label = a[0], a[a.index("--label") + 1]
    premise = "--premise-page" in a
    import orchestrator as O
    ctx = O.Ctx(slug, "rederive")
    before = {"page": _sha(ctx.page), "page_json": _sha(ctx.page_json)}
    n0 = _lines(LEDGER)
    if premise:
        # Built in place from a backup and put back after the check: the case keeps its full page, and the premise
        # page, its page.json and its record are kept under draft/premise_page/ (never as the case's page).
        import shutil
        import tempfile
        import premise_page as PP
        keep = Path(tempfile.mkdtemp(prefix="whu-premise-"))
        shutil.copytree(ctx.case, keep / "case")
        try:
            built = PP.build(ctx)
            got = check(slug)
            out = keep / "premise_page"
            out.mkdir()
            for f in (ctx.page, ctx.page_json, ctx.case / PP.RECORD):
                shutil.copy2(f, out / f.name)
        finally:
            shutil.rmtree(ctx.case)
            shutil.copytree(keep / "case", ctx.case)
        dest = ctx.case / "draft" / "premise_page"
        dest.mkdir(exist_ok=True)
        for f in (keep / "premise_page").iterdir():
            shutil.copy2(f, dest / f.name)
        built["page_sha256"] = _sha(dest / ctx.page.name)
        shutil.rmtree(keep)
    else:
        from orch.page import Page
        O._rerender(ctx, Page.load(ctx.page_json))
        built = None
        got = check(slug)
    if _lines(LEDGER) != n0:
        print("rederive: the spend ledger changed during a code-only re-derivation", file=sys.stderr)
        return 1
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "label": label,
           "kind": "premise page" if premise else "page", "model_calls": 0,
           "page_before": before, "page_after": {"page": _sha(ctx.page), "page_json": _sha(ctx.page_json)},
           "outcome": got["outcome"], "stops": got["stops"]}
    if built:
        rec["premise_page"] = built
    rp = ctx.case / "orchestrator" / "run_paid.json"
    doc = json.loads(rp.read_text(encoding="utf-8"))
    doc.setdefault("rederived", []).append(rec)
    rp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("label", "kind", "outcome", "stops")}, indent=1, ensure_ascii=False))
    print(got["tail"][-2500:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
