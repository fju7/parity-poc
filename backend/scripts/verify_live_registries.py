"""Run both golden sets against the LIVE registries and diff against the recording.

WHY
---
tests/verify replays 90 registry responses recorded on 2026-09-14. Fixtures
freeze; the eCFR revises, Ohio amends, CMS reissues its manuals every year,
Europe PMC adds full texts. A test that passes against a recording says the
code still agrees with September 2026, not that the world does. This runs
the same golden sets with the cache bypassed and reports every divergence
between live and recorded: a section whose heading changed, a document whose
text changed, an identifier that stopped resolving, a binding outcome that
flipped. Any divergence is a non-zero exit -- the run IS the report, and the
workflow that schedules it (.github/workflows/verify-gates.yml) is how the
operator hears.

Usage:
    python scripts/verify_live_registries.py            # both registries
    python scripts/verify_live_registries.py --only law
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
FIXTURES = BACKEND / "tests" / "verify" / "fixtures" / "http"

from verify import http  # noqa: E402
from verify import law, literature  # noqa: E402
from verify.bind import bind_all  # noqa: E402
from verify.types import Context  # noqa: E402

LIT = json.loads((BACKEND / "tests" / "verify" / "golden_literature.json").read_text())
LAW = json.loads((BACKEND / "tests" / "verify" / "golden_law.json").read_text())


def _entries(only: str | None):
    if only in (None, "literature"):
        for grp in ("known_good", "known_bad"):
            for e in LIT[grp]:
                yield ("literature", grp, e["id"], e["id"].split(":", 1)[1], e["assertion"] or e["ours"], e["ours"], Context())
    if only in (None, "law"):
        for grp in ("negatives", "positives", "context_negatives"):
            for e in LAW[grp]:
                yield ("law", grp, e["cite"], e["cite"], e["assertion"], e["characterisation"], Context(**e["context"]))


def _run(registry, raw, assertion, characterisation, ctx):
    mod = literature if registry == "literature" else law
    ident = mod.identify(raw)
    if ident is None:
        return {"exists": "NO_IDENTIFIER", "heading": None, "sha": None, "ok": False, "kinds": {}}
    res = mod.resolve(ident)
    doc = mod.fetch(res)
    ok, bs = bind_all(assertion, res, doc, ctx, characterisation=characterisation)
    return {"exists": res.exists.value, "heading": res.heading, "sha": doc.sha256 if doc else None,
            "chars": len(doc.text) if doc else 0, "ok": ok,
            "kinds": {b.kind.value: ("abstain" if b.abstained else b.ok) for b in bs}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["literature", "law"])
    a = ap.parse_args()
    diverged = 0
    rows = []
    for registry, grp, label, raw, assertion, char, ctx in _entries(a.only):
        http.CACHE_DIR = FIXTURES
        rec = _run(registry, raw, assertion, char, ctx)
        http.CACHE_DIR = None
        live = _run(registry, raw, assertion, char, ctx)
        diffs = []
        if live["exists"] != rec["exists"]:
            diffs.append(f"exists {rec['exists']} -> {live['exists']}")
        if (live["heading"] or "") != (rec["heading"] or ""):
            diffs.append(f"heading changed: {str(rec['heading'])[:50]!r} -> {str(live['heading'])[:50]!r}")
        if live["sha"] != rec["sha"]:
            diffs.append(f"document changed ({rec.get('chars')} -> {live.get('chars')} chars)")
        if live["kinds"] != rec["kinds"] or live["ok"] != rec["ok"]:
            diffs.append(f"binding changed: {rec['kinds']} -> {live['kinds']}")
        status = "same" if not diffs else "DIVERGED"
        diverged += bool(diffs)
        rows.append((registry, grp, label, status, "; ".join(diffs)))
    w = max(len(r[2]) for r in rows)
    for r in rows:
        print(f"{r[0]:10} {r[1]:17} {r[2]:{w}} {r[3]:8} {r[4]}")
    print(f"\n{len(rows)} entries, {diverged} diverged from the 2026-09-14 recording.")
    if diverged:
        print("A divergence is not necessarily an error -- the eCFR revises, Ohio amends, CMS "
              "reissues -- but it is a fact about the world the fixtures no longer hold. Read it, "
              "then re-record the fixture and re-read the heading before the golden set trusts it again.")
    return 1 if diverged else 0


if __name__ == "__main__":
    sys.exit(main())
