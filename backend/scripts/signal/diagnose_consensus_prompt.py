"""
Diagnostic: which variable flipped GLP-1 'pricing' from debated to consensus?

The consensus rows on production were written in March 2026. Since then THREE
things changed, and a single re-run cannot tell them apart:

  1. the prompt (the A2/A4 side-attribution rules were added),
  2. the claim set for the category,
  3. whatever snapshot the "claude-sonnet-4-6" alias resolves to.

This runs ONE category against three prompt variants over the SAME claims and
the SAME model, so the only variable is the prompt:

  v0  the original prompt, as it was before the A2/A4 commit
  v1  the first A2/A4 version (the one with the "should be null" effort rule)
  v2  the current, corrected version

If all three return the same status, the prompt is exonerated and the cause is
the claim set or the model. If they differ, the prompt is the cause and this
says exactly which line did it.

Read-only: no database writes, no consensus rows touched.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)
    python scripts/signal/diagnose_consensus_prompt.py --issue-slug glp1-drugs --category pricing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc
from topic_config import get_topic


V0_RULES = '''## Rules
- supporting_claim_ids should include the 3-8 most informative claims for this assessment (use the claim IDs provided)
- Weight higher-scored claims more heavily in your assessment'''

V1_RULES = '''## Rules
- supporting_claim_ids should include the 3-8 most informative claims for this assessment (use the claim IDs provided)
- For "debated" status, for_claim_ids and against_claim_ids must list the specific claim IDs each argument rests on — the actual evidence behind arguments_for and arguments_against respectively. A reader should be able to click through and check your reasoning.
- A claim ID may appear in only one of for_claim_ids / against_claim_ids, never both. Claims that inform the assessment without favouring either side belong in neither — leave them to supporting_claim_ids.
- Do not force balance. If one side genuinely rests on more or better-scored evidence, the lists should be uneven; that asymmetry is information, not a flaw to correct.
- For "consensus" or "uncertain" status, for_claim_ids and against_claim_ids should be null.
- Weight higher-scored claims more heavily in your assessment'''

CURRENT_RULES_HEAD = '''## Rules
- Decide consensus_status FIRST'''


def build_variants(topic: dict) -> dict[str, str]:
    """Return {label: system_prompt}. v2 is whatever the file currently says."""
    v2 = mc._build_consensus_system_prompt(topic)

    start = v2.index(CURRENT_RULES_HEAD)
    end = v2.index("- Weight higher-scored claims more heavily in your assessment")
    current_rules = v2[start:end] + "- Weight higher-scored claims more heavily in your assessment"

    v1 = v2.replace(current_rules, V1_RULES)
    v0 = v2.replace(current_rules, V0_RULES)

    # v0 predates side attribution entirely — strip the two output fields too.
    v0 = v0.replace(
        '''  "arguments_against": "If debated: 1-2 sentences describing the opposing argument supported by evidence. If not debated: null.",
  "for_claim_ids": ["id1", "id2", ...],
  "against_claim_ids": ["id1", "id2", ...]''',
        '''  "arguments_against": "If debated: 1-2 sentences describing the opposing argument supported by evidence. If not debated: null."''',
    )

    assert "for_claim_ids" not in v0, "v0 still mentions side attribution"
    assert "should be null." in v1, "v1 lost the effort-gradient rule"
    assert "Decide consensus_status FIRST" in v2, "v2 lost the ordering rule"
    return {"v0 original": v0, "v1 first A2/A4": v1, "v2 corrected": v2}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--issue-slug", default="glp1-drugs")
    ap.add_argument("--category", default="pricing")
    args = ap.parse_args()

    topic = get_topic(args.issue_slug)
    sb = mc._get_supabase()
    _issue_id, by_category = mc.load_scored_claims(sb, args.issue_slug)

    claims = by_category.get(args.category, [])
    if not claims:
        print(f"No claims in category '{args.category}'. Categories: {sorted(by_category)}")
        return

    print(f"\nTopic:    {topic['title']}")
    print(f"Category: {args.category} ({len(claims)} claims)")
    print(f"Model:    {mc.SCORING_MODEL}  (temperature 0)")
    print("Same claims, same model — the prompt is the only variable.\n")

    user_content = mc._build_category_prompt(args.category, claims)

    results = {}
    for label, system_prompt in build_variants(topic).items():
        print(f"[{label}] calling...", end=" ", flush=True)
        out = mc._call_claude(system_prompt, user_content)
        if not isinstance(out, dict):
            print("FAILED")
            results[label] = None
            continue
        status = out.get("consensus_status")
        results[label] = status
        extra = ""
        if status == "debated":
            n_for = len(out.get("for_claim_ids") or [])
            n_against = len(out.get("against_claim_ids") or [])
            if n_for or n_against:
                extra = f"  (for={n_for}, against={n_against})"
        print(f"-> {status}{extra}")

    print("\n" + "=" * 60)
    distinct = {v for v in results.values() if v}
    if len(distinct) <= 1:
        print("VERDICT: the prompt is NOT the cause.")
        print("All three variants agree, so the change came from the claim set")
        print("or the model snapshot — not from the A2/A4 edit.")
    else:
        print("VERDICT: the prompt IS the cause.")
        for label, status in results.items():
            print(f"  {label:18s} -> {status}")
    print("=" * 60)
    print("\nNo rows were written. Production consensus is untouched.")


if __name__ == "__main__":
    main()
