"""
Parity Signal: Consensus Mapping.

Analyzes scored claims within each category to determine whether the evidence
shows consensus, debate, or uncertainty. Produces one signal_consensus row
per category (6 total) with structured summaries and supporting claim IDs.

Consensus statuses:
  consensus  — Strong majority of well-scored claims point in the same direction
  debated    — Credible claims support opposing conclusions
  uncertain  — Insufficient or conflicting evidence, no clear direction

For "debated" categories, Claude also provides arguments_for and arguments_against.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/map_consensus.py --dry-run
    python scripts/signal/map_consensus.py
    python scripts/signal/map_consensus.py --force   # re-map (clears existing)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add backend/ to sys.path so we can import supabase_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

SCORING_MODEL = "claude-sonnet-4-6"
BACKOFF_DELAYS = [2, 5, 10]
CATEGORIES = ["efficacy", "safety", "cardiovascular", "pricing", "regulatory", "emerging"]


# ---------------------------------------------------------------------------
# Anthropic Claude client (lazy singleton)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_anthropic_client():
    """Lazy singleton for Anthropic client. Reads ANTHROPIC_API_KEY from env."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set.")
            print("  export ANTHROPIC_API_KEY=your_key_here")
            sys.exit(1)
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 4096) -> dict | list | None:
    """Call Claude API with retry on 529, return parsed JSON."""
    client = _get_anthropic_client()
    response = None

    for attempt in range(len(BACKOFF_DELAYS) + 1):
        try:
            response = client.messages.create(
                model=SCORING_MODEL,
                max_tokens=max_tokens,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(BACKOFF_DELAYS):
                delay = BACKOFF_DELAYS[attempt]
                print(f"  [RETRY] Claude overloaded (529), attempt {attempt + 1}/{len(BACKOFF_DELAYS)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"  [ERROR] Claude API error: {exc}")
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"  [ERROR] Invalid JSON from Claude: {raw_text[:500]}")
        return None


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _get_supabase():
    """Import and return the Supabase client, or exit with message."""
    from supabase_client import supabase as sb
    if sb is None:
        print("ERROR: Supabase client not initialized.")
        print("Set SUPABASE_SERVICE_KEY environment variable before running.")
        sys.exit(1)
    return sb


def load_scored_claims(sb) -> tuple[str, dict[str, list[dict]]]:
    """Load all scored claims grouped by category.

    Returns (issue_id, {category: [claim_dicts]}) where each claim has:
      id, claim_text, category, specificity, composite_score, evidence_category
    """
    # Get the GLP-1 issue
    resp = sb.table("signal_issues").select("id").eq("slug", "glp1-drugs").execute()
    if not resp.data:
        print("ERROR: No 'glp1-drugs' issue found. Run earlier pipeline steps first.")
        sys.exit(1)
    issue_id = resp.data[0]["id"]

    # Get all claims
    resp = (
        sb.table("signal_claims")
        .select("id, claim_text, category, specificity")
        .eq("issue_id", issue_id)
        .execute()
    )
    claims = resp.data or []
    if not claims:
        print("ERROR: No claims found. Run extract_claims.py first.")
        sys.exit(1)

    # Get composites for these claims
    claim_ids = [c["id"] for c in claims]
    composites: dict[str, dict] = {}

    chunk_size = 50
    for i in range(0, len(claim_ids), chunk_size):
        chunk = claim_ids[i:i + chunk_size]
        resp = (
            sb.table("signal_claim_composites")
            .select("claim_id, composite_score, evidence_category")
            .in_("claim_id", chunk)
            .execute()
        )
        for comp in (resp.data or []):
            composites[comp["claim_id"]] = comp

    # Attach composites and group by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    unscored = 0
    for claim in claims:
        comp = composites.get(claim["id"])
        if comp:
            claim["composite_score"] = float(comp["composite_score"])
            claim["evidence_category"] = comp["evidence_category"]
        else:
            claim["composite_score"] = None
            claim["evidence_category"] = None
            unscored += 1
        by_category[claim.get("category", "emerging")].append(claim)

    total = len(claims)
    scored = total - unscored
    print(f"Loaded {total} claims ({scored} scored, {unscored} unscored) for issue {issue_id}")

    return issue_id, by_category


def get_existing_consensus(sb, issue_id: str) -> list[dict]:
    """Check for existing consensus rows for this issue."""
    resp = (
        sb.table("signal_consensus")
        .select("id, category, consensus_status")
        .eq("issue_id", issue_id)
        .execute()
    )
    return resp.data or []


def clear_existing_consensus(sb, issue_id: str) -> int:
    """Delete all consensus rows for this issue. Returns count deleted."""
    resp = (
        sb.table("signal_consensus")
        .delete()
        .eq("issue_id", issue_id)
        .execute()
    )
    return len(resp.data or [])


# ---------------------------------------------------------------------------
# Consensus mapping prompt
# ---------------------------------------------------------------------------

CONSENSUS_SYSTEM_PROMPT = """You are an evidence analyst for a medical evidence intelligence platform. You are assessing the overall consensus state for a category of claims about GLP-1 receptor agonist drugs.

You will receive a list of claims with their evidence scores. Assess whether the evidence in this category shows consensus, debate, or uncertainty.

## Consensus Status Definitions

- **consensus**: The strong majority of well-scored claims point in the same direction. There may be minor variations in specifics, but the overall evidence direction is clear and agreed upon.

- **debated**: Credible claims support meaningfully different or opposing conclusions. The debate is substantive — not just minor disagreements in magnitude, but genuine tension in what the evidence suggests.

- **uncertain**: The evidence is insufficient, too early-stage, or too conflicting to determine a clear direction. This is different from "debated" — uncertain means we don't have enough evidence, while debated means we have evidence pointing in multiple directions.

## Output Format

Return a JSON object:
{
  "consensus_status": "consensus" | "debated" | "uncertain",
  "summary_text": "2-3 sentence plain-language summary of what the evidence says in this category. Written for a general audience — no jargon. Should convey the overall direction and strength of evidence.",
  "supporting_claim_ids": ["id1", "id2", ...],
  "arguments_for": "If debated: 1-2 sentences describing the main argument supported by evidence. If not debated: null.",
  "arguments_against": "If debated: 1-2 sentences describing the opposing argument supported by evidence. If not debated: null."
}

## Rules
- supporting_claim_ids should include the 3-8 most informative claims for this assessment (use the claim IDs provided)
- Weight higher-scored claims more heavily in your assessment
- summary_text must be understandable to someone with no medical background
- For "debated" status, both arguments_for and arguments_against must reference specific evidence
- For "consensus" or "uncertain" status, arguments_for and arguments_against should be null
- Do not take sides — describe what the evidence shows"""


def _build_category_prompt(category: str, claims: list[dict]) -> str:
    """Build user prompt with all claims in a category and their scores."""
    # Sort by composite score descending (strongest evidence first)
    scored = [c for c in claims if c.get("composite_score") is not None]
    unscored = [c for c in claims if c.get("composite_score") is None]
    scored.sort(key=lambda c: c["composite_score"], reverse=True)
    all_claims = scored + unscored

    parts = [
        f"Category: {category}",
        f"Total claims: {len(all_claims)}",
        "",
    ]

    for i, claim in enumerate(all_claims, 1):
        score_str = f"{claim['composite_score']:.2f} ({claim['evidence_category']})" if claim.get("composite_score") is not None else "unscored"
        parts.append(
            f"{i}. [{score_str}] (ID: {claim['id']})\n"
            f"   {claim['claim_text']}"
        )

    return "\n".join(parts)


def map_category(category: str, claims: list[dict]) -> dict | None:
    """Send category claims to Claude for consensus assessment.

    Returns consensus dict or None on failure.
    """
    user_text = _build_category_prompt(category, claims)
    result = _call_claude(CONSENSUS_SYSTEM_PROMPT, user_text)

    if result is None:
        print(f"  [FAIL] No response for category: {category}")
        return None

    # Validate required fields
    status = result.get("consensus_status")
    if status not in ("consensus", "debated", "uncertain"):
        print(f"  [WARN] Invalid consensus_status '{status}' for {category}, defaulting to 'uncertain'")
        result["consensus_status"] = "uncertain"

    return result


def store_consensus(sb, issue_id: str, category: str, consensus: dict) -> bool:
    """Insert one consensus row. Returns True on success."""
    row = {
        "issue_id": issue_id,
        "category": category,
        "consensus_status": consensus["consensus_status"],
        "summary_text": consensus.get("summary_text", ""),
        "supporting_claim_ids": consensus.get("supporting_claim_ids", []),
        "arguments_for": consensus.get("arguments_for"),
        "arguments_against": consensus.get("arguments_against"),
    }
    try:
        sb.table("signal_consensus").insert(row).execute()
        return True
    except Exception as exc:
        print(f"  [ERROR] Failed to insert consensus for {category}: {exc}")
        return False


# ---------------------------------------------------------------------------
# CLI orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Map consensus status for each claim category using Claude API."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be mapped without API calls or DB writes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear existing consensus rows before re-mapping",
    )
    args = parser.parse_args()

    sb = _get_supabase()
    issue_id, by_category = load_scored_claims(sb)

    # --- Dry run ---
    if args.dry_run:
        print(f"\n--- DRY RUN MODE (no API calls, no DB writes) ---\n")
        existing = get_existing_consensus(sb, issue_id)
        print(f"Existing consensus rows: {len(existing)}")
        if existing:
            for row in existing:
                print(f"  {row['category']}: {row['consensus_status']}")

        print(f"\nCategories to map:")
        for cat in CATEGORIES:
            group = by_category.get(cat, [])
            scored = sum(1 for c in group if c.get("composite_score") is not None)
            avg = 0
            if scored:
                avg = sum(c["composite_score"] for c in group if c.get("composite_score") is not None) / scored
            print(f"  {cat}: {len(group)} claims ({scored} scored, avg composite {avg:.2f})")

        print(f"\nAPI calls needed: {len([c for c in CATEGORIES if by_category.get(c)])}")
        return

    # --- Idempotency check ---
    existing = get_existing_consensus(sb, issue_id)
    if existing and not args.force:
        print(f"\nFound {len(existing)} existing consensus rows:")
        for row in existing:
            print(f"  {row['category']}: {row['consensus_status']}")
        print("Use --force to clear and re-map.")
        return

    if existing and args.force:
        print(f"\n--force: clearing {len(existing)} existing consensus rows...")
        cleared = clear_existing_consensus(sb, issue_id)
        print(f"Cleared {cleared} rows.")

    # --- Map each category ---
    print(f"\nMapping consensus for {len(CATEGORIES)} categories...\n")

    results = {}
    succeeded = 0
    failed = 0

    for cat in CATEGORIES:
        group = by_category.get(cat, [])
        if not group:
            print(f"[{cat}] No claims, skipping")
            continue

        scored_count = sum(1 for c in group if c.get("composite_score") is not None)
        print(f"[{cat}] Mapping {len(group)} claims ({scored_count} scored)...", end=" ", flush=True)

        consensus = map_category(cat, group)
        if consensus:
            stored = store_consensus(sb, issue_id, cat, consensus)
            if stored:
                results[cat] = consensus
                succeeded += 1
                print(f"-> {consensus['consensus_status']}")
            else:
                failed += 1
                print("-> STORE FAILED")
        else:
            failed += 1
            print("-> API FAILED")

        # Delay between API calls
        time.sleep(0.5)

    # --- Summary ---
    print(f"\n{'='*60}")
    print("CONSENSUS MAPPING COMPLETE")
    print(f"{'='*60}")
    print(f"Categories mapped: {succeeded} ({failed} failed)")

    status_counts = defaultdict(int)
    for cat, cons in results.items():
        status = cons["consensus_status"]
        status_counts[status] += 1
        print(f"\n  [{status.upper()}] {cat}")
        print(f"    {cons.get('summary_text', '')}")
        if status == "debated":
            print(f"    FOR:     {cons.get('arguments_for', '')}")
            print(f"    AGAINST: {cons.get('arguments_against', '')}")

    print(f"\nDistribution: {dict(status_counts)}")


if __name__ == "__main__":
    main()
