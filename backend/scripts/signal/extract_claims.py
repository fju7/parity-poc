"""
Parity Signal: Extract factual claims from GLP-1 sources using Claude API.

Two-phase pipeline:
  Phase 1 — Send each source's title/summary/key_findings to Claude, get 2-6
             structured claims per source (~120-200 raw candidates).
  Phase 2 — Group raw claims by category, send each group to Claude for
             semantic deduplication. Target: 50-100 final claims.

Results stored in signal_claims + signal_claim_sources (Supabase).

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/extract_claims.py --dry-run
    python scripts/signal/extract_claims.py --phase extract --limit 3
    python scripts/signal/extract_claims.py
    python scripts/signal/extract_claims.py --force   # re-extract (clears existing)
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

EXTRACTION_MODEL = "claude-sonnet-4-6"
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
    """Call Claude API with retry on 529, return parsed JSON (dict or list)."""
    client = _get_anthropic_client()
    response = None

    for attempt in range(len(BACKOFF_DELAYS) + 1):
        try:
            response = client.messages.create(
                model=EXTRACTION_MODEL,
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
        print("  export SUPABASE_SERVICE_KEY=your_service_role_key_here")
        sys.exit(1)
    return sb


def get_issue_and_sources(sb) -> tuple[str, list[dict]]:
    """Read the GLP-1 issue and all its sources from Supabase.

    Returns (issue_id, sources_list) where each source dict has:
      id, title, content_text, metadata (with slug, key_findings, etc.)
    """
    # Get the GLP-1 issue
    resp = sb.table("signal_issues").select("id").eq("slug", "glp1-drugs").execute()
    if not resp.data:
        print("ERROR: No 'glp1-drugs' issue found in signal_issues.")
        print("Run collect_sources.py first to load the source library.")
        sys.exit(1)
    issue_id = resp.data[0]["id"]

    # Get all sources for this issue
    resp = (
        sb.table("signal_sources")
        .select("id, title, content_text, metadata")
        .eq("issue_id", issue_id)
        .execute()
    )
    sources = resp.data or []
    if not sources:
        print("ERROR: No sources found for the GLP-1 issue.")
        print("Run collect_sources.py first to load the source library.")
        sys.exit(1)

    print(f"Found issue '{issue_id}' with {len(sources)} sources")
    return issue_id, sources


def get_existing_claims(sb, issue_id: str) -> list[dict]:
    """Check for already-stored claims for this issue."""
    resp = (
        sb.table("signal_claims")
        .select("id, claim_text, category")
        .eq("issue_id", issue_id)
        .execute()
    )
    return resp.data or []


def clear_existing_claims(sb, issue_id: str) -> int:
    """Delete all claims (and their source links) for this issue.

    Returns count of deleted claims.
    """
    # First get claim IDs
    resp = (
        sb.table("signal_claims")
        .select("id")
        .eq("issue_id", issue_id)
        .execute()
    )
    claim_ids = [row["id"] for row in (resp.data or [])]
    if not claim_ids:
        return 0

    # Delete claim-source links first (foreign key)
    for claim_id in claim_ids:
        sb.table("signal_claim_sources").delete().eq("claim_id", claim_id).execute()

    # Delete claims
    sb.table("signal_claims").delete().eq("issue_id", issue_id).execute()

    return len(claim_ids)


def store_claims(sb, issue_id: str, final_claims: list[dict], source_id_by_slug: dict[str, str]) -> tuple[int, int]:
    """Insert deduplicated claims into signal_claims + signal_claim_sources.

    Each item in final_claims:
      { claim_text, category, specificity, source_slugs: [...], source_contexts: {slug: context} }

    Returns (claims_inserted, links_inserted).
    """
    claims_inserted = 0
    links_inserted = 0

    for claim in final_claims:
        # Insert into signal_claims
        row = {
            "issue_id": issue_id,
            "claim_text": claim["claim_text"],
            "category": claim["category"],
            "specificity": claim.get("specificity", "qualitative"),
            "extraction_model": EXTRACTION_MODEL,
        }
        try:
            resp = sb.table("signal_claims").insert(row).execute()
            claim_id = resp.data[0]["id"]
            claims_inserted += 1
        except Exception as exc:
            print(f"  [ERROR] Failed to insert claim: {exc}")
            print(f"          Claim: {claim['claim_text'][:80]}...")
            continue

        # Insert source links
        source_contexts = claim.get("source_contexts", {})
        for slug in claim.get("source_slugs", []):
            source_id = source_id_by_slug.get(slug)
            if not source_id:
                print(f"  [WARN] Unknown source slug '{slug}', skipping link")
                continue
            link_row = {
                "claim_id": claim_id,
                "source_id": source_id,
                "source_context": source_contexts.get(slug, ""),
            }
            try:
                sb.table("signal_claim_sources").insert(link_row).execute()
                links_inserted += 1
            except Exception as exc:
                print(f"  [WARN] Failed to insert claim-source link: {exc}")

    return claims_inserted, links_inserted


# ---------------------------------------------------------------------------
# Phase 1: Extract raw claims per source
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM_PROMPT = """You are an evidence analyst. Extract discrete factual claims from this source about GLP-1 receptor agonist drugs.

A claim is a specific, testable assertion of fact — not a summary, opinion, or recommendation.

Categories (pick exactly one per claim):
- efficacy: treatment outcomes, weight loss, A1C reduction, dose-response
- safety: adverse events, side effects, contraindications, warnings
- cardiovascular: heart outcomes, MACE, blood pressure, heart failure
- pricing: cost, insurance coverage, market dynamics, affordability
- regulatory: FDA approvals, labeling changes, indications, policy
- emerging: new formulations, pipeline drugs, novel applications

Specificity:
- quantitative: claim contains specific numbers, percentages, or statistical results
- qualitative: claim describes a direction or relationship without specific numbers
- mixed: claim has some numbers but key part is qualitative

Return a JSON array of 2-6 claims. Each claim object:
{
  "claim_text": "The specific factual assertion (one sentence, precise)",
  "category": "one of the six categories above",
  "specificity": "quantitative|qualitative|mixed",
  "source_context": "The key phrase or sentence from the source that supports this claim"
}

Rules:
- Each claim must be independently understandable (no pronouns referring to the source)
- Include drug names when relevant (semaglutide, tirzepatide, etc.)
- Quantitative claims should preserve exact numbers from the source
- Do not invent facts not present in the source material
- Prefer claims that would be useful for evidence assessment"""


def _build_source_text(source: dict) -> str:
    """Build the user prompt text from a source's fields."""
    meta = source.get("metadata", {}) or {}
    parts = [f"Source Title: {source.get('title', 'Unknown')}"]

    content = source.get("content_text", "")
    if content:
        # Truncate very long content to keep within token limits
        if len(content) > 8000:
            content = content[:8000] + "\n\n[truncated]"
        parts.append(f"\nContent:\n{content}")

    key_findings = meta.get("key_findings", [])
    if key_findings:
        parts.append("\nKey Findings:")
        for kf in key_findings:
            parts.append(f"  - {kf}")

    slug = meta.get("slug", "")
    if slug:
        parts.append(f"\nSource Slug (for reference): {slug}")

    return "\n".join(parts)


def extract_from_source(source: dict) -> list[dict] | None:
    """Phase 1: Send one source to Claude, get back 2-6 raw claims.

    Returns list of claim dicts with source slug attached, or None on failure.
    """
    meta = source.get("metadata", {}) or {}
    slug = meta.get("slug", "unknown")

    user_text = _build_source_text(source)
    result = _call_claude(EXTRACT_SYSTEM_PROMPT, user_text)

    if result is None:
        print(f"  [FAIL] No response for source: {slug}")
        return None

    # Handle both list and dict-with-claims-key responses
    claims = result if isinstance(result, list) else result.get("claims", [])

    if not claims:
        print(f"  [WARN] Zero claims extracted from: {slug}")
        return None

    # Tag each claim with its source slug
    for claim in claims:
        claim["source_slug"] = slug

    return claims


# ---------------------------------------------------------------------------
# Phase 2: Deduplicate by category
# ---------------------------------------------------------------------------

DEDUP_SYSTEM_PROMPT = """You are an evidence analyst. Review these candidate claims about GLP-1 drugs and merge any that assert the same fact.

Rules:
- Two claims are duplicates if they assert the same core fact, even if worded differently
- When merging, keep the most precise wording (prefer quantitative over qualitative)
- For each final claim, list ALL source slugs that support it
- Preserve source_context entries — collect them keyed by source slug
- Do NOT invent new claims; only merge and deduplicate
- Keep claims that are related but assert different facts as separate entries

Return a JSON array of deduplicated claims. Each object:
{
  "claim_text": "The most precise version of this claim",
  "category": "the category (same for all in this batch)",
  "specificity": "quantitative|qualitative|mixed",
  "source_slugs": ["slug1", "slug2"],
  "source_contexts": {"slug1": "supporting passage", "slug2": "supporting passage"}
}"""


def deduplicate_category(category: str, raw_claims: list[dict]) -> list[dict] | None:
    """Phase 2: Send all raw claims in one category to Claude for dedup.

    Returns list of deduplicated claim dicts, or None on failure.
    """
    # Build the user prompt with all claims for this category
    claims_for_prompt = []
    for i, c in enumerate(raw_claims, 1):
        entry = {
            "id": i,
            "claim_text": c.get("claim_text", ""),
            "specificity": c.get("specificity", "qualitative"),
            "source_slug": c.get("source_slug", ""),
            "source_context": c.get("source_context", ""),
        }
        claims_for_prompt.append(entry)

    user_text = (
        f"Category: {category}\n"
        f"Number of candidate claims: {len(claims_for_prompt)}\n\n"
        f"Candidate claims:\n{json.dumps(claims_for_prompt, indent=2)}"
    )

    result = _call_claude(DEDUP_SYSTEM_PROMPT, user_text, max_tokens=8192)

    if result is None:
        print(f"  [FAIL] Dedup failed for category: {category}")
        return None

    deduped = result if isinstance(result, list) else result.get("claims", [])

    if not deduped:
        print(f"  [WARN] Zero claims after dedup for: {category}")
        return None

    # Ensure category is set on all claims
    for claim in deduped:
        claim["category"] = category

    return deduped


# ---------------------------------------------------------------------------
# CLI orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract factual claims from GLP-1 sources using Claude API."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without API calls or DB writes",
    )
    parser.add_argument(
        "--phase",
        choices=["extract", "dedup", "all"],
        default="all",
        help="Run specific phase: extract (phase 1 only), dedup (phase 2 only), all (default)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N sources (0 = all, for testing)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear existing claims before re-extracting",
    )
    args = parser.parse_args()

    # --- Dry run mode ---
    if args.dry_run:
        print("\n--- DRY RUN MODE (no API calls, no DB writes) ---\n")
        sb = _get_supabase()
        issue_id, sources = get_issue_and_sources(sb)

        if args.limit:
            sources = sources[:args.limit]

        existing = get_existing_claims(sb, issue_id)
        print(f"Existing claims in DB: {len(existing)}")
        print(f"Sources to process: {len(sources)}")
        print(f"\nPhase 1 would extract claims from {len(sources)} sources")
        print(f"Phase 2 would deduplicate across {len(CATEGORIES)} categories")
        print(f"Estimated raw claims: {len(sources) * 3}-{len(sources) * 6}")

        for i, src in enumerate(sources, 1):
            meta = src.get("metadata", {}) or {}
            slug = meta.get("slug", "?")
            title = src.get("title", "?")
            has_content = bool(src.get("content_text"))
            kf_count = len(meta.get("key_findings", []))
            print(f"  [{i:>2}/{len(sources)}] {slug}: \"{title[:60]}\" "
                  f"(content={'yes' if has_content else 'no'}, key_findings={kf_count})")
        return

    # --- Live mode ---
    sb = _get_supabase()
    issue_id, sources = get_issue_and_sources(sb)

    # Build slug -> source_id mapping
    source_id_by_slug = {}
    for src in sources:
        meta = src.get("metadata", {}) or {}
        slug = meta.get("slug")
        if slug:
            source_id_by_slug[slug] = src["id"]

    # Idempotency check
    existing = get_existing_claims(sb, issue_id)
    if existing and not args.force:
        print(f"\nFound {len(existing)} existing claims for this issue.")
        print("Use --force to clear and re-extract.")
        return

    if existing and args.force:
        print(f"\n--force: clearing {len(existing)} existing claims...")
        cleared = clear_existing_claims(sb, issue_id)
        print(f"Cleared {cleared} claims and their source links.")

    if args.limit:
        sources = sources[:args.limit]
        print(f"Limited to first {args.limit} sources")

    # =======================================================================
    # Phase 1: Extract raw claims per source
    # =======================================================================
    raw_claims: list[dict] = []

    if args.phase in ("extract", "all"):
        print(f"\n{'='*60}")
        print(f"PHASE 1: Extracting claims from {len(sources)} sources")
        print(f"{'='*60}\n")

        succeeded = 0
        failed = 0

        for i, source in enumerate(sources, 1):
            meta = source.get("metadata", {}) or {}
            slug = meta.get("slug", "?")
            print(f"[{i:>2}/{len(sources)}] Extracting from: {slug}...")

            claims = extract_from_source(source)
            if claims:
                raw_claims.extend(claims)
                print(f"  -> {len(claims)} claims extracted")
                succeeded += 1
            else:
                failed += 1

            # Small delay between API calls to avoid rate limits
            if i < len(sources):
                time.sleep(0.5)

        print(f"\nPhase 1 complete: {len(raw_claims)} raw claims from "
              f"{succeeded} sources ({failed} failed)")

        # Show category distribution
        cat_counts = defaultdict(int)
        for c in raw_claims:
            cat_counts[c.get("category", "unknown")] += 1
        print("Category distribution:")
        for cat in CATEGORIES:
            print(f"  {cat}: {cat_counts.get(cat, 0)}")

    # If phase=extract only, store raw claims directly (no dedup)
    if args.phase == "extract":
        print(f"\n--phase=extract: Storing {len(raw_claims)} raw claims (no dedup)...")
        # Convert raw claims to storage format
        final_claims = []
        for c in raw_claims:
            final_claims.append({
                "claim_text": c["claim_text"],
                "category": c.get("category", "emerging"),
                "specificity": c.get("specificity", "qualitative"),
                "source_slugs": [c["source_slug"]],
                "source_contexts": {c["source_slug"]: c.get("source_context", "")},
            })
        claims_ins, links_ins = store_claims(sb, issue_id, final_claims, source_id_by_slug)
        print(f"Stored {claims_ins} claims with {links_ins} source links.")
        return

    # =======================================================================
    # Phase 2: Deduplicate by category
    # =======================================================================
    final_claims: list[dict] = []

    if args.phase in ("dedup", "all"):
        # If running dedup-only, we need raw claims from somewhere
        if args.phase == "dedup" and not raw_claims:
            print("ERROR: --phase=dedup requires existing raw claims.")
            print("Run with --phase=all or --phase=extract first.")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"PHASE 2: Deduplicating across {len(CATEGORIES)} categories")
        print(f"{'='*60}\n")

        # Group raw claims by category
        by_category: dict[str, list[dict]] = defaultdict(list)
        for c in raw_claims:
            cat = c.get("category", "emerging")
            if cat not in CATEGORIES:
                cat = "emerging"  # fallback
            by_category[cat].append(c)

        for cat in CATEGORIES:
            group = by_category.get(cat, [])
            if not group:
                print(f"[{cat}] No claims, skipping")
                continue

            print(f"[{cat}] Deduplicating {len(group)} raw claims...")
            deduped = deduplicate_category(cat, group)

            if deduped:
                final_claims.extend(deduped)
                print(f"  -> {len(deduped)} claims after dedup "
                      f"(merged {len(group) - len(deduped)})")
            else:
                # Fallback: keep raw claims if dedup fails
                print(f"  [WARN] Dedup failed, keeping {len(group)} raw claims")
                for c in group:
                    final_claims.append({
                        "claim_text": c["claim_text"],
                        "category": cat,
                        "specificity": c.get("specificity", "qualitative"),
                        "source_slugs": [c["source_slug"]],
                        "source_contexts": {c["source_slug"]: c.get("source_context", "")},
                    })

            # Small delay between category calls
            time.sleep(0.5)

        print(f"\nPhase 2 complete: {len(final_claims)} final claims "
              f"(from {len(raw_claims)} raw)")

    # =======================================================================
    # Store results
    # =======================================================================
    if final_claims:
        print(f"\nStoring {len(final_claims)} claims in Supabase...")
        claims_ins, links_ins = store_claims(sb, issue_id, final_claims, source_id_by_slug)
        print(f"Stored {claims_ins} claims with {links_ins} source links.")

        # Final summary
        print(f"\n{'='*60}")
        print("EXTRACTION COMPLETE")
        print(f"{'='*60}")
        cat_counts = defaultdict(int)
        for c in final_claims:
            cat_counts[c.get("category", "unknown")] += 1
        print(f"Total claims: {claims_ins}")
        print(f"Total source links: {links_ins}")
        print("By category:")
        for cat in CATEGORIES:
            print(f"  {cat}: {cat_counts.get(cat, 0)}")
    else:
        print("\nNo claims to store.")


if __name__ == "__main__":
    main()
