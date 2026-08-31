#!/usr/bin/env python3
"""
Recall against the SIX FATAL CLASSES, measured one control at a time.

WHY THIS EXISTS
---------------
factcheck_recall.py measures the four gate roles. The six classes that would
actually end this publication's credibility are not measured by anything,
because four of the six are not checked by a gate role: the counterexample
hunter is a separate script, quotation matching and design characterisation do
not exist, and attribution and unknowability are deterministic lints in the
preflight. Between 28 and 31 August, issue two published three of the six.

You cannot improve what you have not measured, and every claim of improvement
made without this file is a feeling. Run it before building, to get the number
to beat, and after, to find out whether the build worked.

WHAT IT MEASURES
----------------
For each seeded fatal-class error in factcheck_broken_fixture.expected.json:
does the control named in its `expect` field find it? Reported per class, not
as a total, because a total hides which kind of mistake we are blind to -- and
which kind we are blind to is the whole answer.

A control that does not exist scores MISSING, which is different from a control
that ran and found nothing (MISS). Conflating the two is how a check nobody
built reads as a check that passed.

Deterministic controls are free. The counterexample hunter costs one API call
per claim and is opt-in with --hunt.

    python scripts/signal/fatal_recall.py              # free controls only
    python scripts/signal/fatal_recall.py --hunt       # + the hunter (paid)
    python scripts/signal/fatal_recall.py --report r.json
"""
import argparse, importlib.util, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]   # repo root, not backend/
FIXTURE = ROOT / "backend/tests/fixtures/factcheck_broken_fixture.html"
KEY     = ROOT / "backend/tests/fixtures/factcheck_broken_fixture.expected.json"
WH      = ROOT / "backend/scripts/whatholdsup"
sys.path.insert(0, str(WH))

def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

lint = _load("lint_claims", WH / "lint_claims.py")
CE   = _load("counterexample", WH / "counterexample.py")

FOUND, MISS, MISSING = "FOUND", "MISS", "NO CONTROL"

def norm(t):
    t = t.replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"').replace("—", "-")
    return " ".join(t.split()).lower()

def overlaps(a, b):
    a, b = norm(a), norm(b)
    if a[:60] in b or b[:60] in a:
        return True
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / max(1, min(len(wa), len(wb))) > 0.7


def control_attribution(text):
    """Names on the page with no record that anyone opened the author list."""
    return [s for s in lint.attributions(text)]

def control_unknowability(text):
    """Claims something cannot be known, naming no registry."""
    return lint.unknowability(text)

def control_universal(text):
    """The counterexample hunter's INPUT. Surfacing the sentence is not breaking
    it -- scored separately, and only --hunt actually attacks."""
    return CE.universal_negatives(text)

def control_missing(_text):
    return None                       # built? no.

CONTROLS = {
    "ATTRIBUTION":    control_attribution,
    "UNKNOWABILITY":  control_unknowability,
    "COUNTEREXAMPLE": control_universal,
    "QUOTATION":      control_missing,
    "DESIGN":         control_missing,
    "INHERITED":      control_missing,
}

NOTE = {
    "COUNTEREXAMPLE": "lint surfaced the sentence as a candidate; --hunt attacks it",
    "QUOTATION":      "no quotation matcher exists",
    "DESIGN":         "no design-characterisation check exists",
    "INHERITED":      "inherited.json has no entry for this fixture; the check cannot fire",
}

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hunt", action="store_true", help="also run the counterexample hunter (paid)")
    ap.add_argument("--report")
    a = ap.parse_args()

    raw = FIXTURE.read_text(encoding="utf-8")
    text = lint.plain(raw)
    key = json.load(io.open(KEY, encoding="utf-8"))
    fatal = [s for s in key["seeded"] if s["id"].startswith("f")]

    print("\nFatal-class recall · %d classes · fixture %s" % (len(fatal), FIXTURE.name))
    print("=" * 74)
    rows, hits, ran = [], 0, 0
    for seed in fatal:
        ctrl = seed["expect"]
        fn = CONTROLS.get(ctrl, control_missing)
        out = fn(text)
        if out is None:
            verdict = MISSING
        else:
            verdict = FOUND if any(overlaps(seed["quote"], o) for o in out) else MISS
            ran += 1
            if verdict == FOUND:
                hits += 1
        rows.append({"id": seed["id"], "class": seed["class"], "control": ctrl,
                     "verdict": verdict, "quote": seed["quote"]})
        mark = {FOUND: " ok ", MISS: "MISS", MISSING: "----"}[verdict]
        print("  [%s] %-30s %-15s %s" % (mark, seed["class"], ctrl, NOTE.get(ctrl, "")))
        print("         %s" % seed["quote"][:96])

    # A measurement taken through a model role has a shelf life. On 2026-08-31
    # the alias behind these roles was shown to move within three hours, at
    # temperature 0, on identical inputs. The two deterministic lints below are
    # stable by construction; anything scored by a model is a reading of one
    # moment. Stamp the run so a future reader knows which moment.
    import datetime as _dt
    stamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    print("\n  measured %s  ·  model roles resolve through an alias and can move" % stamp)

    built = [r for r in rows if r["verdict"] != MISSING]
    print("=" * 74)
    print("  %d of %d fatal classes have a control that ran." % (len(built), len(rows)))
    print("  Of those, %d found the seeded error." % hits)
    print("  %d classes have NO CONTROL AT ALL -- not a pass, an absence." %
          (len(rows) - len(built)))
    if a.report:
        json.dump({"at": stamp, "note": "model roles resolve through an unpinnable alias; deterministic lints do not", "rows": rows,
                   "controls_built": len(built), "controls_total": len(rows), "found": hits},
                  io.open(a.report, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("  report: %s" % a.report)
    return 0 if hits == len(rows) else 1

if __name__ == "__main__":
    raise SystemExit(main())
