"""
Parity Signal: Evidence Scoring Engine.

Scores each claim across six dimensions using Claude API, then computes
weighted composite scores in Python. Results stored in signal_claim_scores
(per-dimension) and signal_claim_composites (weighted aggregate).

Per-dimension storage is critical for Analytical Paths — alternative weighting
profiles that show how different analytical perspectives reach different
conclusions from the same underlying evidence.

Six dimensions (default weights):
  source_quality  25%   How authoritative is the primary source?
  data_support    20%   Is there quantitative data directly supporting the claim?
  reproducibility 20%   Has the finding been replicated independently?
  consensus       15%   What proportion of credible sources agree?
  recency         10%   How current is the evidence?
  rigor           10%   Study design quality / analytical rigor

Composite: weighted average → Strong (4.0-5.0), Moderate (3.0-3.9),
Mixed (2.0-2.9), Weak (1.0-1.9).

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/score_claims.py --dry-run
    python scripts/signal/score_claims.py --limit 5
    python scripts/signal/score_claims.py
    python scripts/signal/score_claims.py --force   # re-score (clears existing)
"""
from __future__ import annotations

import argparse
import json
import math
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

DIMENSIONS = ["source_quality", "data_support", "reproducibility", "consensus", "recency", "rigor"]

DEFAULT_WEIGHTS = {
    "source_quality": 0.25,
    "data_support": 0.20,
    "reproducibility": 0.20,
    "consensus": 0.15,
    "recency": 0.10,
    "rigor": 0.10,
}

EVIDENCE_CATEGORIES = [
    (4.0, "strong"),
    (3.0, "moderate"),
    (2.0, "mixed"),
    (0.0, "weak"),
]

DEFAULT_BATCH_SIZE = 10


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


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 8192) -> dict | list | None:
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


def load_claims_with_sources(sb) -> tuple[str, list[dict]]:
    """Load all claims for the GLP-1 issue with their supporting sources.

    Returns (issue_id, claims_list) where each claim dict has:
      id, claim_text, category, specificity, sources: [{title, source_type, publication_date}]
    """
    # Get the GLP-1 issue
    resp = sb.table("signal_issues").select("id").eq("slug", "glp1-drugs").execute()
    if not resp.data:
        print("ERROR: No 'glp1-drugs' issue found. Run extract_claims.py first.")
        sys.exit(1)
    issue_id = resp.data[0]["id"]

    # Get all claims for this issue
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

    # Get all claim-source links
    claim_ids = [c["id"] for c in claims]
    source_links: dict[str, list[str]] = defaultdict(list)

    # Fetch in chunks to avoid URL length limits
    chunk_size = 50
    for i in range(0, len(claim_ids), chunk_size):
        chunk = claim_ids[i:i + chunk_size]
        resp = (
            sb.table("signal_claim_sources")
            .select("claim_id, source_id, source_context")
            .in_("claim_id", chunk)
            .execute()
        )
        for link in (resp.data or []):
            source_links[link["claim_id"]].append({
                "source_id": link["source_id"],
                "source_context": link.get("source_context", ""),
            })

    # Get all source metadata we need
    all_source_ids = list({
        link["source_id"]
        for links in source_links.values()
        for link in links
    })
    source_meta: dict[str, dict] = {}

    for i in range(0, len(all_source_ids), chunk_size):
        chunk = all_source_ids[i:i + chunk_size]
        resp = (
            sb.table("signal_sources")
            .select("id, title, source_type, publication_date")
            .in_("id", chunk)
            .execute()
        )
        for src in (resp.data or []):
            source_meta[src["id"]] = src

    # Attach source metadata to each claim
    for claim in claims:
        links = source_links.get(claim["id"], [])
        claim["sources"] = []
        for link in links:
            meta = source_meta.get(link["source_id"], {})
            claim["sources"].append({
                "title": meta.get("title", "Unknown"),
                "source_type": meta.get("source_type", "unknown"),
                "publication_date": meta.get("publication_date"),
                "source_context": link.get("source_context", ""),
            })

    print(f"Loaded {len(claims)} claims (issue: {issue_id})")
    return issue_id, claims


def get_existing_scores(sb, claim_ids: list[str]) -> int:
    """Check how many dimension scores already exist for these claims."""
    if not claim_ids:
        return 0
    # Check first chunk only — if any exist, they all likely do
    chunk = claim_ids[:50]
    resp = (
        sb.table("signal_claim_scores")
        .select("id", count="exact")
        .in_("claim_id", chunk)
        .execute()
    )
    return resp.count or 0


def clear_existing_scores(sb, claim_ids: list[str]) -> tuple[int, int]:
    """Delete all scores and composites for these claims.

    Returns (scores_deleted, composites_deleted).
    """
    if not claim_ids:
        return 0, 0

    scores_deleted = 0
    composites_deleted = 0
    chunk_size = 50

    for i in range(0, len(claim_ids), chunk_size):
        chunk = claim_ids[i:i + chunk_size]

        # Delete dimension scores
        resp = (
            sb.table("signal_claim_scores")
            .delete()
            .in_("claim_id", chunk)
            .execute()
        )
        scores_deleted += len(resp.data or [])

        # Delete composites
        resp = (
            sb.table("signal_claim_composites")
            .delete()
            .in_("claim_id", chunk)
            .execute()
        )
        composites_deleted += len(resp.data or [])

    return scores_deleted, composites_deleted


# ---------------------------------------------------------------------------
# Scoring prompt
# ---------------------------------------------------------------------------

SCORE_SYSTEM_PROMPT = """You are an evidence scoring analyst for a medical evidence intelligence platform. Score each claim across six dimensions on a 1-5 integer scale.

## Dimensions

1. **source_quality** (1-5): How authoritative are the sources supporting this claim?
   - 5: FDA approval/label, major peer-reviewed RCT (NEJM, Lancet, JAMA)
   - 4: Government agency report (CMS, CDC, WHO), systematic review
   - 3: Peer-reviewed observational study, reputable health policy analysis (KFF, RAND)
   - 2: News reporting on primary source, industry press release, advocacy group
   - 1: Opinion, social media, non-peer-reviewed preprint

2. **data_support** (1-5): Is there quantitative data directly supporting this claim?
   - 5: Specific statistical results (p-values, confidence intervals, effect sizes)
   - 4: Specific numbers (percentages, dollar amounts, patient counts)
   - 3: Quantitative direction with approximate magnitudes
   - 2: Qualitative assertion with indirect numeric context
   - 1: Purely qualitative assertion with no numeric support

3. **reproducibility** (1-5): Has this finding been confirmed by independent sources?
   - 5: Multiple independent RCTs or large studies confirm the finding
   - 4: At least 2 independent sources with consistent findings
   - 3: One strong primary source plus corroborating secondary sources
   - 2: Single source, not yet independently confirmed
   - 1: Preliminary or contested finding

4. **consensus** (1-5): What proportion of credible sources agree with this claim?
   - 5: Universal agreement across all relevant source types
   - 4: Strong majority agreement with minor variation in specifics
   - 3: General agreement but some credible dissent or caveats
   - 2: Divided — credible sources on both sides
   - 1: Minority position or actively debated

5. **recency** (1-5): How current is the evidence?
   - 5: Published within the last 12 months (2025-2026)
   - 4: Published 1-2 years ago (2024)
   - 3: Published 2-4 years ago (2022-2023)
   - 2: Published 4-6 years ago (2020-2021)
   - 1: Published more than 6 years ago (before 2020)

6. **rigor** (1-5): What is the methodological quality?
   - 5: Phase 3 RCT, large N, pre-registered, peer-reviewed
   - 4: Well-designed controlled study or comprehensive regulatory review
   - 3: Observational study with appropriate controls, or rigorous policy analysis
   - 2: Descriptive analysis, market report, or uncontrolled comparison
   - 1: Anecdotal, opinion-based, or methodologically flawed

## Output Format

Return a JSON array with one object per claim. Each object:
{
  "claim_id": "the claim ID provided",
  "scores": {
    "source_quality": {"score": 4, "rationale": "One sentence explaining the score"},
    "data_support": {"score": 3, "rationale": "..."},
    "reproducibility": {"score": 3, "rationale": "..."},
    "consensus": {"score": 4, "rationale": "..."},
    "recency": {"score": 5, "rationale": "..."},
    "rigor": {"score": 4, "rationale": "..."}
  }
}

## Rules
- Score ONLY based on the information provided about each claim and its sources
- Be calibrated: use the full 1-5 range across the batch
- Rationale must be one concise sentence referencing specific evidence
- Do not invent information not present in the claim or source metadata"""


def _build_batch_prompt(batch: list[dict], category: str, total_in_category: int) -> str:
    """Build user prompt for a batch of claims to score."""
    parts = [
        f"Category: {category}",
        f"Batch size: {len(batch)} claims (out of {total_in_category} total in this category)",
        "",
    ]

    for i, claim in enumerate(batch, 1):
        parts.append(f"--- Claim {i} ---")
        parts.append(f"ID: {claim['id']}")
        parts.append(f"Text: {claim['claim_text']}")
        parts.append(f"Specificity: {claim.get('specificity', 'unknown')}")

        sources = claim.get("sources", [])
        if sources:
            parts.append(f"Supporting sources ({len(sources)}):")
            for s in sources:
                pub = s.get("publication_date", "unknown date")
                parts.append(f"  - [{s['source_type']}] {s['title']} ({pub})")
                ctx = s.get("source_context", "")
                if ctx:
                    parts.append(f"    Context: {ctx[:200]}")
        else:
            parts.append("Supporting sources: none linked")
        parts.append("")

    return "\n".join(parts)


def score_batch(batch: list[dict], category: str, total_in_category: int) -> list[dict] | None:
    """Send a batch of claims to Claude for 6-dimension scoring.

    Returns list of {claim_id, scores: {dim: {score, rationale}}} or None on failure.
    """
    user_text = _build_batch_prompt(batch, category, total_in_category)
    result = _call_claude(SCORE_SYSTEM_PROMPT, user_text)

    if result is None:
        return None

    scored = result if isinstance(result, list) else result.get("claims", result.get("scores", []))

    if not scored:
        print(f"  [WARN] Empty scoring response")
        return None

    return scored


# ---------------------------------------------------------------------------
# Composite calculation (deterministic Python, not Claude)
# ---------------------------------------------------------------------------

def compute_composite(dimension_scores: dict[str, int], weights: dict[str, float] = None) -> tuple[float, str]:
    """Compute weighted composite score and evidence category.

    Args:
        dimension_scores: {dimension_key: score_int}
        weights: {dimension_key: weight_float} — defaults to DEFAULT_WEIGHTS

    Returns:
        (composite_score, evidence_category)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    total_weight = 0.0
    weighted_sum = 0.0

    for dim, weight in weights.items():
        score = dimension_scores.get(dim)
        if score is not None:
            weighted_sum += score * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0, "weak"

    composite = weighted_sum / total_weight
    # Round to 2 decimal places
    composite = round(composite, 2)

    category = "weak"
    for threshold, cat in EVIDENCE_CATEGORIES:
        if composite >= threshold:
            category = cat
            break

    return composite, category


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def store_scores(sb, scored_claims: list[dict]) -> int:
    """Insert per-dimension scores into signal_claim_scores.

    Each scored_claim: {claim_id, scores: {dim: {score, rationale}}}
    Returns count of rows inserted.
    """
    rows_inserted = 0

    for item in scored_claims:
        claim_id = item.get("claim_id")
        scores = item.get("scores", {})

        for dim in DIMENSIONS:
            dim_data = scores.get(dim, {})
            score_val = dim_data.get("score")
            rationale = dim_data.get("rationale", "")

            if score_val is None:
                continue

            # Clamp to valid range
            score_val = max(1, min(5, int(score_val)))

            row = {
                "claim_id": claim_id,
                "dimension": dim,
                "score": score_val,
                "rationale": rationale,
                "scoring_model": SCORING_MODEL,
            }
            try:
                sb.table("signal_claim_scores").insert(row).execute()
                rows_inserted += 1
            except Exception as exc:
                print(f"  [ERROR] Failed to insert score for {claim_id}/{dim}: {exc}")

    return rows_inserted


def store_composites(sb, composites: list[dict]) -> int:
    """Insert composite scores into signal_claim_composites.

    Each composite: {claim_id, composite_score, evidence_category, weights_used}
    Returns count of rows inserted.
    """
    rows_inserted = 0

    for comp in composites:
        row = {
            "claim_id": comp["claim_id"],
            "composite_score": comp["composite_score"],
            "evidence_category": comp["evidence_category"],
            "weights_used": comp["weights_used"],
        }
        try:
            sb.table("signal_claim_composites").insert(row).execute()
            rows_inserted += 1
        except Exception as exc:
            print(f"  [ERROR] Failed to insert composite for {comp['claim_id']}: {exc}")

    return rows_inserted


# ---------------------------------------------------------------------------
# CLI orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score GLP-1 claims across six evidence dimensions using Claude API."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scored without API calls or DB writes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Score only first N claims (0 = all, for testing)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear existing scores before re-scoring",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Claims per Claude API call (default: {DEFAULT_BATCH_SIZE})",
    )
    args = parser.parse_args()

    sb = _get_supabase()
    issue_id, claims = load_claims_with_sources(sb)

    if args.limit:
        claims = claims[:args.limit]
        print(f"Limited to first {args.limit} claims")

    claim_ids = [c["id"] for c in claims]

    # --- Dry run ---
    if args.dry_run:
        print(f"\n--- DRY RUN MODE (no API calls, no DB writes) ---\n")
        existing_count = get_existing_scores(sb, claim_ids)
        print(f"Existing dimension scores in DB: {existing_count}")
        print(f"Claims to score: {len(claims)}")
        print(f"Batch size: {args.batch_size}")

        # Category breakdown
        by_cat = defaultdict(list)
        for c in claims:
            by_cat[c.get("category", "unknown")].append(c)

        total_batches = 0
        for cat, group in sorted(by_cat.items()):
            n_batches = math.ceil(len(group) / args.batch_size)
            total_batches += n_batches
            src_counts = [len(c.get("sources", [])) for c in group]
            avg_sources = sum(src_counts) / len(src_counts) if src_counts else 0
            print(f"  {cat}: {len(group)} claims → {n_batches} batches "
                  f"(avg {avg_sources:.1f} sources/claim)")

        print(f"\nTotal API calls: {total_batches}")
        print(f"Dimension scores to write: {len(claims) * 6}")
        print(f"Composite scores to write: {len(claims)}")
        print(f"\nDefault weights: {json.dumps(DEFAULT_WEIGHTS)}")
        return

    # --- Idempotency check ---
    existing_count = get_existing_scores(sb, claim_ids)
    if existing_count > 0 and not args.force:
        print(f"\nFound {existing_count} existing dimension scores.")
        print("Use --force to clear and re-score.")
        return

    if existing_count > 0 and args.force:
        print(f"\n--force: clearing existing scores...")
        scores_del, comp_del = clear_existing_scores(sb, claim_ids)
        print(f"Cleared {scores_del} dimension scores and {comp_del} composites.")

    # --- Group by category and batch ---
    by_category: dict[str, list[dict]] = defaultdict(list)
    for c in claims:
        by_category[c.get("category", "emerging")].append(c)

    all_scored: list[dict] = []
    total_batches = 0
    failed_batches = 0

    for cat in sorted(by_category.keys()):
        group = by_category[cat]
        n_batches = math.ceil(len(group) / args.batch_size)
        print(f"\n[{cat}] Scoring {len(group)} claims in {n_batches} batches...")

        for batch_idx in range(n_batches):
            start = batch_idx * args.batch_size
            end = start + args.batch_size
            batch = group[start:end]
            total_batches += 1

            batch_label = f"  batch {batch_idx + 1}/{n_batches} ({len(batch)} claims)"
            print(f"{batch_label}...", end=" ", flush=True)

            scored = score_batch(batch, cat, len(group))

            if scored:
                all_scored.extend(scored)
                print(f"OK ({len(scored)} scored)")
            else:
                failed_batches += 1
                print("FAILED")

            # Delay between API calls
            if batch_idx < n_batches - 1 or cat != sorted(by_category.keys())[-1]:
                time.sleep(0.5)

    print(f"\nScoring complete: {len(all_scored)} claims scored in "
          f"{total_batches} batches ({failed_batches} failed)")

    if not all_scored:
        print("No scores to store.")
        return

    # --- Store dimension scores ---
    print(f"\nStoring dimension scores...")
    dim_rows = store_scores(sb, all_scored)
    print(f"Stored {dim_rows} dimension score rows")

    # --- Compute and store composites ---
    print(f"Computing composites...")
    composites = []
    for item in all_scored:
        claim_id = item.get("claim_id")
        scores = item.get("scores", {})

        # Extract just the integer scores
        dim_scores = {}
        for dim in DIMENSIONS:
            dim_data = scores.get(dim, {})
            s = dim_data.get("score")
            if s is not None:
                dim_scores[dim] = max(1, min(5, int(s)))

        composite_score, evidence_category = compute_composite(dim_scores)

        composites.append({
            "claim_id": claim_id,
            "composite_score": composite_score,
            "evidence_category": evidence_category,
            "weights_used": DEFAULT_WEIGHTS,
        })

    comp_rows = store_composites(sb, composites)
    print(f"Stored {comp_rows} composite scores")

    # --- Summary ---
    print(f"\n{'='*60}")
    print("SCORING COMPLETE")
    print(f"{'='*60}")
    print(f"Claims scored: {len(all_scored)}")
    print(f"Dimension scores: {dim_rows}")
    print(f"Composite scores: {comp_rows}")

    # Evidence category distribution
    cat_dist = defaultdict(int)
    for comp in composites:
        cat_dist[comp["evidence_category"]] += 1
    print(f"\nEvidence strength distribution:")
    for cat in ["strong", "moderate", "mixed", "weak"]:
        count = cat_dist.get(cat, 0)
        pct = (count / len(composites) * 100) if composites else 0
        print(f"  {cat:>8}: {count:>3} ({pct:.0f}%)")

    # Average composite by claim category
    cat_composites = defaultdict(list)
    for item, comp in zip(all_scored, composites):
        # Find the original claim's category
        for c in claims:
            if c["id"] == item.get("claim_id"):
                cat_composites[c["category"]].append(comp["composite_score"])
                break

    print(f"\nAverage composite by category:")
    for cat in sorted(cat_composites.keys()):
        scores = cat_composites[cat]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {cat:>16}: {avg:.2f} ({len(scores)} claims)")


if __name__ == "__main__":
    main()
