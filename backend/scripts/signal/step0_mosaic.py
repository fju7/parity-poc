"""
Step 0b — can a SET of propositions cover a category that no single one can?

WHY
---
Three attempts on social-media/depression_anxiety, 26 Aug 2026:

    proposition          agreement  bearing  context  unclear  opposing share
    simple                    94%      57%      28%      15%             26%
    broadened                 91%      72%      21%       6%             15%
    compound ("X and Y")      91%      60%      23%      17%             18%

The simple one is the best of the three and still leaves 28% of the evidence
as `context`. Broadening cut the residue by making the question harder to
contradict — falsifiability fell with it. Compounding two questions into one
sentence made the labelling worse outright.

The diagnosis on the third run said the leftovers "share no single common
structure ... genuinely miscellaneous residue that resists a unified pattern."

Which is the finding: `context` is not noise. It is evidence bearing on
questions that were never asked. The suicide-rate trend is not background to
"is use associated with symptoms" — it is bearing evidence for "have outcomes
worsened as adoption grew", a different and equally falsifiable question.

So this measures the alternative: several simple propositions, each judged on
its own, and COVERAGE — the share of claims bearing on at least one of them —
as the metric that replaces residue.

That swap matters beyond bookkeeping. Under one proposition the cheapest way to
absorb stray claims is to broaden it. Under a set, the cheapest way is to add
another question, and each question keeps its own falsifiability. The incentive
toward vagueness disappears rather than being policed.

STRICTLY READ-ONLY. No database writes.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/step0_mosaic.py \
        --issue-slug social-media-teen-mental-health --category depression_anxiety
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc
from signal_model import MODEL, warn_if_unpinned
from step0_proposition import REPORT_DIR, analyse, classify_once
from topic_config import get_topic

MIN_BEARING = 5   # a proposition with fewer bearing claims cannot be assessed


def set_prompt(topic: dict, category: str, n: int) -> str:
    return f"""You are defining the set of questions a body of evidence speaks to.

Topic: {topic['title']}
Context: {topic['prompt_detail']}
Category: {category}

A single proposition cannot capture a subject like this. The evidence bears on
several distinct questions whose answers together form the picture. Write up to
{n} of them.

Each proposition must be:
- FALSIFIABLE — evidence could in principle show it false
- SINGULAR — ONE claim. Never two joined by "and". If you want to say "X is
  true and it is stronger for group G", those are two propositions.
- SPECIFIC — a reader can tell what would count for and against it
- NEUTRAL — not phrased to favour either answer
- DISTINCT — it must be possible for one to be true and another false

Do NOT hedge to make a proposition easier to support. "Effects vary by context"
absorbs all evidence and is worth nothing. A proposition that nothing could
contradict does not belong in the set.

Cover the real structure of the subject. For a health question that typically
includes, where the evidence supports asking them: whether an association
exists; whether it is causal; whether population-level trends track exposure;
whether effects differ by subgroup; whether specific mechanisms operate;
whether interventions change outcomes.

Order them so that logically prior questions come first — an association claim
before the causal claim that depends on it.

Return JSON only:
{{"propositions": [
   {{"statement": "...", "why_it_matters": "one line", "depends_on": null }},
   {{"statement": "...", "why_it_matters": "one line", "depends_on": 0 }}
 ]}}"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--issue-slug", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--max-propositions", type=int, default=6)
    ap.add_argument("--runs", type=int, default=1,
                    help="Passes per proposition. Stability is already measured "
                         "at 94%%; 1 is enough for a coverage reading.")
    ap.add_argument("--baseline", type=float, default=None,
                    help="Single-proposition bearing rate to compare against, e.g. 0.57")
    args = ap.parse_args()

    topic = get_topic(args.issue_slug)
    sb = mc._get_supabase()
    _issue_id, by_category = mc.load_scored_claims(sb, args.issue_slug)
    claims = by_category.get(args.category, [])
    if not claims:
        return print(f"No claims in '{args.category}'.") or 1

    print(f"\nTopic    : {topic['title']}")
    print(f"Category : {args.category}  ({len(claims)} claims)")
    print(f"Model    : {MODEL}")
    warn_if_unpinned(MODEL)
    print("READ-ONLY — nothing is written to the database.\n")

    print("Writing the proposition set...", end=" ", flush=True)
    out = mc._call_claude(set_prompt(topic, args.category, args.max_propositions),
                          "Write the set.", max_tokens=2048)
    props = (out or {}).get("propositions") if isinstance(out, dict) else None
    if not props:
        return print("FAILED — no set generated.") or 1
    print(f"{len(props)} propositions\n")

    for i, p in enumerate(props):
        dep = p.get("depends_on")
        tag = f"  (depends on #{dep + 1})" if isinstance(dep, int) else ""
        print(f"  {i + 1}. {p['statement']}{tag}")
        if p.get("why_it_matters"):
            print(f"     — {p['why_it_matters']}")
    print()

    # --- classify against each proposition, independently -----------------
    results = []
    covered: set[str] = set()
    for i, p in enumerate(props):
        print(f"Proposition {i + 1} of {len(props)}:")
        runs = [classify_once(claims, p["statement"], r + 1) for r in range(args.runs)]
        a = analyse(claims, runs)
        bearing_ids = {cid for cid, m in a["modal"].items() if m in ("supports", "opposes")}
        covered |= bearing_ids
        d = a["distribution"]
        assessable = len(bearing_ids) >= MIN_BEARING
        print(f"    supports={d.get('supports', 0)}  opposes={d.get('opposes', 0)}  "
              f"bearing={len(bearing_ids)}  opposing share={a['opposing_share']:.0%}"
              + ("" if assessable else f"   [THIN — under {MIN_BEARING} bearing claims]"))
        results.append({**p, "index": i + 1, "analysis": a,
                        "bearing_ids": sorted(bearing_ids), "assessable": assessable})
        print()

    # --- coverage ---------------------------------------------------------
    coverage = len(covered) / len(claims)
    uncovered = [c for c in claims if str(c["id"]) not in covered]

    print("=" * 70)
    print("MOSAIC COVERAGE")
    print("=" * 70)
    print(f"Claims in category                  : {len(claims)}")
    print(f"Bearing on at least one proposition  : {len(covered)}  ({coverage:.0%})")
    print(f"Bearing on none                      : {len(uncovered)}  ({1 - coverage:.0%})")
    if args.baseline is not None:
        delta = coverage - args.baseline
        print(f"Single-proposition baseline          : {args.baseline:.0%}  "
              f"({'+' if delta >= 0 else ''}{delta:.0%})")

    thin = [r for r in results if not r["assessable"]]
    weak = [r for r in results if r["assessable"] and r["analysis"]["opposing_share"] < 0.10]
    print(f"\nPropositions that can be assessed    : {len(results) - len(thin)} of {len(results)}")
    if thin:
        print("  too thin to assess (drop or merge):")
        for r in thin:
            print(f"    {r['index']}. {r['statement'][:88]}")
    if weak:
        print("  hard to contradict — check they are not hedged:")
        for r in weak:
            print(f"    {r['index']}. ({r['analysis']['opposing_share']:.0%} opposing) {r['statement'][:70]}")

    if uncovered:
        print(f"\nCLAIMS BEARING ON NO PROPOSITION ({len(uncovered)})")
        print("These are the prompt to ask another question — not leftovers.")
        for c in uncovered[:15]:
            print(f"  - {c['claim_text'][:150]}")
        if len(uncovered) > 15:
            print(f"  ... and {len(uncovered) - 15} more")

    print("\nWHAT THIS TELLS YOU")
    if args.baseline is not None and coverage > args.baseline + 0.15:
        print(f"The set covers substantially more evidence than one proposition could")
        print(f"({args.baseline:.0%} -> {coverage:.0%}). The mosaic is real: these claims were")
        print("answering questions that were never asked, not sitting idle.")
    elif args.baseline is not None and coverage <= args.baseline + 0.05:
        print("The set covers little more than a single proposition did. Either the")
        print("propositions overlap heavily, or the uncovered claims genuinely are")
        print("background. Read the uncovered list before adding more questions.")
    else:
        print("Compare against a single-proposition run with --baseline to see whether")
        print("the set actually covers more.")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"mosaic_{args.issue_slug}_{args.category}.json"
    out_path.write_text(json.dumps({
        "topic": args.issue_slug, "category": args.category, "model": MODEL,
        "coverage": coverage, "n_claims": len(claims),
        "baseline": args.baseline,
        "propositions": [{
            "index": r["index"], "statement": r["statement"],
            "why_it_matters": r.get("why_it_matters"), "depends_on": r.get("depends_on"),
            "assessable": r["assessable"],
            "distribution": r["analysis"]["distribution"],
            "opposing_share": r["analysis"]["opposing_share"],
            "bearing_ids": r["bearing_ids"],
        } for r in results],
        "uncovered_claims": [c["claim_text"] for c in uncovered],
    }, indent=2) + "\n")
    print(f"\nReport: {out_path}")
    print("No database rows were written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
