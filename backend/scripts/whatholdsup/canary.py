#!/usr/bin/env python3
"""Can the checks read this document at all? — a round-trip per held document.

WHY
---
The Lancet writes its decimals with a middle dot: 0·561, two-sided p=0·053.
Every span check in this repository searched for "0.053" with a full stop, so
on 2026-09-01 B2 reported three times that a figure was absent from a document
we had held since morning, and sent the operator hunting for a paywalled PDF he
did not need.

Nothing was broken in a way any check could see. The document was held, its
hash matched, its identity was confirmed, its substance was confirmed. The
pipeline that the checks read it THROUGH was broken, silently, for that one
publisher's typography.

THE TEST
--------
Take figures out of the document using the same extraction the checks use, then
look for them using the same search the checks use. A figure that came OUT of a
document must be findable IN it. If it is not, the pipeline cannot read this
document, and every "not found" it reports about this document is worthless.

This is deliberately a round trip rather than a fixed list of known strings.
A list would be another allow-list, wrong the moment a new publisher arrives —
which is the failure it exists to catch.

WHAT IT LICENSES
----------------
A document that fails is not unusable; it is UNREADABLE BY THESE CHECKS. An
absence reported against it must be recorded as "could not determine", never as
"not there". Those are different states, and merging them is the oldest error
in this project — eight instances by the evening this was written, the last one
caused by a character.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store  # noqa: E402
import spancheck as SC        # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# Figures worth round-tripping: decimals and thousands, which is what the page
# actually prints and what every span check actually searches for.
# Decimals only. The first version also matched comma-grouped thousands —
# 1,143 — and then "bridged" the comma to a full stop, so it demanded 1.143 of
# a document that says 1,143 and reported eight readable documents unreadable.
# A comma is not a decimal separator in any of these publishers.
FIGURE = re.compile(r"(?<![0-9.])\d+[.·•]\d{2,}(?![0-9])")


def sample(slug: str, sid: str, n: int = 6) -> list[str]:
    text = SC._text(slug, sid) or ""
    seen, out = set(), []
    for m in FIGURE.finditer(text):
        f = m.group(0)
        if f in seen:
            continue
        seen.add(f)
        out.append(f)
        if len(out) >= n:
            break
    return out


def ascii_form(fig: str) -> str:
    """The figure as THE PAGE would write it, computed here and not by the
    pipeline under test.

    THE FIRST VERSION OF THIS CANARY PASSED WITH THE BUG IN PLACE. It took a
    figure out of the document and searched for it, and both sides went through
    the same normaliser -- so a normaliser that could not read middle dots
    failed to read them consistently on both sides and the round trip closed.
    A self-consistent broken pipeline is exactly what a round trip through
    itself cannot see.

    The bug only ever showed as a MISMATCH BETWEEN REPRESENTATIONS: the page
    prints 0.053, the document prints 0·053. So the canary has to synthesise
    the page's representation independently, and ask the pipeline to bridge to
    it. That is the thing that was broken, so that is the thing to test.
    """
    return fig.replace("·", ".").replace("•", ".")


def check(slug: str, sid: str) -> dict:
    figs = sample(slug, sid)
    if not figs:
        return {"source": sid, "state": "NO_FIGURES",
                "why": "no decimal figures to round-trip; the checks cannot be "
                       "shown to read this document, only assumed to"}
    # search for the PAGE's form of each figure, not the document's
    # `is not True`, NOT `not`. b2_present returns True, False or the string
    # UNDETERMINED, and a non-empty string is truthy — so written as a boolean
    # this counted "could not tell" as "found", one function after the tri-state
    # was introduced to stop exactly that conflation.
    bad = [f for f in figs
           if SC.b2_present(ascii_form(f), slug, sid, trust_canary=False)[0]
           is not True]
    if bad:
        return {"source": sid, "state": "UNREADABLE", "tried": figs,
                "failed": bad,
                "why": "%d of %d figures taken OUT of this document cannot be "
                       "found IN it when written the way the page writes them "
                       "(%s) — the checks cannot bridge this publisher's "
                       "typography, so every absence reported against this "
                       "document is worthless until it passes"
                       % (len(bad), len(figs),
                          ", ".join("%s->%s" % (f, ascii_form(f)) for f in bad[:3]))}
    return {"source": sid, "state": "READABLE", "tried": figs,
            "why": "%d figures round-tripped" % len(figs)}


def run(slug: str) -> dict:
    out = {}
    for sid in sorted(store.held(slug) or {}):
        out[sid] = check(slug, sid)
    path = store.case_dir(slug) / "canary.json"
    path.write_text(json.dumps(
        {"_what_this_is":
            "Whether the span checks can read each held document at all. A "
            "figure taken out of a document must be findable in it through the "
            "same pipeline the checks use. Where it is not, an absence "
            "reported against that document means 'could not determine'.",
         "checked": out}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def unreadable(slug: str) -> list[str]:
    p = store.case_dir(slug) / "canary.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8")).get("checked") or {}
    return [k for k, v in d.items() if v.get("state") == "UNREADABLE"]


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    p = store.case_dir(slug) / "canary.json"
    if not p.exists():
        return [("checks can read the documents", WARN,
                 "never run — nothing has shown that the span checks can read "
                 "these documents, only assumed it. Run canary.py %s" % slug)]
    d = json.loads(p.read_text(encoding="utf-8")).get("checked") or {}
    held = set(store.held(slug) or {})
    stale = held - set(d)
    bad = [k for k, v in d.items() if v.get("state") == "UNREADABLE"]
    blind = [k for k, v in d.items() if v.get("state") == "NO_FIGURES"]
    rows = []
    if bad:
        rows.append(("documents the checks cannot read", BAD,
                     "%d document(s) fail the round trip: %s — an absence "
                     "reported against these means 'could not determine'"
                     % (len(bad), ", ".join(bad[:6]))))
    if stale:
        rows.append(("documents never round-tripped", WARN,
                     "%d held document(s) have no canary result: %s"
                     % (len(stale), ", ".join(sorted(stale)[:6]))))
    if not bad and not stale:
        rows.append(("checks can read the documents", OK,
                     "%d of %d held document(s) round-trip their own figures%s"
                     % (len(d) - len(blind), len(d),
                        "" if not blind else
                        "; %d carry no decimal figures to test with" % len(blind))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", default="")
    args = ap.parse_args()
    for slug in ([args.slug] if args.slug else ["melanoma", "cdk46", "deskilling"]):
        res = run(slug)
        print("\n### %s" % slug)
        for sid, r in sorted(res.items()):
            if r["state"] != "READABLE":
                print("  %-11s %-5s %s" % (r["state"], sid, r["why"][:110]))
        for label, state, detail in preflight_rows(slug):
            print("  %-7s %-34s %s" % (state, label, detail[:130]))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
