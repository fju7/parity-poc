"""
Parity Signal: Classify claims by type and consensus status.

Assigns claim_type and consensus_type to each claim in signal_claims
using Claude API. Runs after extraction and before scoring.

claim_type values:
  efficacy              — Does intervention X produce outcome Y?
  safety                — Does X cause harm Y?
  institutional         — What did institution/official X do, say, or decide?
  values_embedded       — Claim contains both empirical and values components
  foundational_values   — Pure values claim, not empirically resolvable

consensus_type values:
  strong_consensus          — 90%+ of rigorous analysts agree, well-replicated
  active_debate             — Genuine scientific disagreement among rigorous analysts
  manufactured_controversy  — Apparent controversy driven by motivated actors, not evidence
  genuine_uncertainty       — Insufficient evidence to establish consensus either way

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/classify_claims.py --dry-run
    python scripts/signal/classify_claims.py --issue-slug breast-cancer-therapies
    python scripts/signal/classify_claims.py --force --issue-slug breast-cancer-therapies
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

from topic_config import get_topic

SCRIPTS_DIR = Path(__file__).resolve().parent

CLASSIFICATION_MODEL = "claude-sonnet-4-6"
BACKOFF_DELAYS = [2, 5, 10]
DEFAULT_BATCH_SIZE = 15

VALID_CLAIM_TYPES = [
    "efficacy",
    "safety",
    "institutional",
    "values_embedded",
    "foundational_values",
]

VALID_CONSENSUS_TYPES = [
    "strong_consensus",
    "active_debate",
    "manufactured_controversy",
    "genuine_uncertainty",
]

# ---------------------------------------------------------------------------
# Anthropic Claude client (lazy singleton)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_anthropic_client():
    """Lazy singleton for Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set.")
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
                model=CLASSIFICATION_MODEL,
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
    """Import and return the Supabase client."""
    from supabase_client import supabase as sb
    if sb is None:
        print("ERROR: Supabase client not initialized.")
        sys.exit(1)
    return sb


def load_claims(sb, issue_slug: str) -> tuple[str, list[dict]]:
    """Load all claims for the given issue.

    Loads using columns known to be in PostgREST schema cache.
    claim_type and consensus_type are loaded via RPC if available,
    otherwise defaults to None (unclassified).

    Returns (issue_id, claims_list) where each claim dict has:
      id, claim_text, category, specificity, claim_type, consensus_type
    """
    resp = sb.table("signal_issues").select("id").eq("slug", issue_slug).execute()
    if not resp.data:
        print(f"ERROR: No '{issue_slug}' issue found. Run extract_claims.py first.")
        sys.exit(1)
    issue_id = resp.data[0]["id"]

    # Try RPC first (includes new columns), fall back to direct query (old columns only)
    try:
        resp = sb.rpc("get_claims_for_classification", {"p_issue_id": issue_id}).execute()
        claims = resp.data or []
        if claims:
            print(f"Loaded {len(claims)} claims via RPC (issue: {issue_id})")
            return issue_id, claims
    except Exception:
        pass

    # Fallback: load without new columns
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

    # Add empty classification fields
    for c in claims:
        c["claim_type"] = None
        c["consensus_type"] = None

    print(f"Loaded {len(claims)} claims via fallback (issue: {issue_id})")
    return issue_id, claims


# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM_PROMPT = """You are a claim classification analyst for a medical evidence intelligence platform. Classify each claim by its type and consensus status.

## Claim Types

1. **efficacy** — Does intervention X produce outcome Y? Measurable, testable claims about whether a treatment, drug, or intervention works for a specific purpose.
   Example: "Pembrolizumab improves 5-year overall survival in triple-negative breast cancer by 9%."

2. **safety** — Does X cause harm Y? Claims about adverse effects, risks, toxicity, or safety concerns.
   Example: "CDK4/6 inhibitors carry a 5-7% risk of grade 3-4 neutropenia."

3. **institutional** — What did institution/official X do, say, or decide? Claims about actions, decisions, policies, or statements by organizations, agencies, or officials.
   Example: "The FDA granted accelerated approval to sacituzumab govitecan for metastatic TNBC in April 2020."

4. **values_embedded** — Claim contains both empirical and values components intertwined. The empirical part could be tested, but the claim as stated also implies a value judgment.
   Example: "The cost of CAR-T therapy ($475,000) is not justified by its modest survival benefit."

5. **foundational_values** — Pure values claim, not empirically resolvable. Claims about what *should* be, what is *fair*, or what is *right*.
   Example: "All breast cancer patients deserve equal access to genomic testing regardless of insurance status."

## Consensus Types

1. **strong_consensus** — 90%+ of rigorous analysts agree, well-replicated. The evidence base is deep and consistent.
   Example: Tamoxifen reduces recurrence in ER+ breast cancer.

2. **active_debate** — Genuine scientific disagreement among rigorous analysts. Credible experts hold different positions based on legitimate interpretation of evidence.
   Example: Optimal duration of adjuvant endocrine therapy (5 vs 10 years).

3. **manufactured_controversy** — Apparent controversy driven by motivated actors, not evidence. The scientific consensus is clear but public debate is fueled by commercial, political, or ideological interests.
   Example: Claims that mammography screening has no net benefit (contradicted by strong RCT evidence).

4. **genuine_uncertainty** — Insufficient evidence to establish consensus either way. The question is empirically resolvable but we don't have enough data yet.
   Example: Long-term cardiac effects of proton vs photon radiation for left-sided breast cancer.

## Output Format

Return a JSON array with one object per claim:
[
  {
    "claim_id": "the claim ID provided",
    "claim_type": "one of: efficacy, safety, institutional, values_embedded, foundational_values",
    "consensus_type": "one of: strong_consensus, active_debate, manufactured_controversy, genuine_uncertainty",
    "type_rationale": "One sentence explaining the claim_type classification",
    "consensus_rationale": "One sentence explaining the consensus_type classification"
  }
]

## Rules
- Classify ONLY based on the claim text and category provided
- Every claim must receive exactly one claim_type and one consensus_type
- Use the full range of types — not everything is efficacy or strong_consensus
- Be precise: institutional claims are about what institutions DID, not about treatment outcomes
- values_embedded requires BOTH empirical and values components in the same claim
- manufactured_controversy should be rare — only use when scientific consensus is clear but public debate persists due to non-scientific actors"""


def _build_batch_prompt(batch: list[dict]) -> str:
    """Build user prompt for a batch of claims to classify."""
    parts = [f"Classify the following {len(batch)} claims:\n"]

    for i, claim in enumerate(batch, 1):
        parts.append(f"--- Claim {i} ---")
        parts.append(f"ID: {claim['id']}")
        parts.append(f"Text: {claim['claim_text']}")
        parts.append(f"Category: {claim.get('category', 'unknown')}")
        parts.append(f"Specificity: {claim.get('specificity', 'unknown')}")
        parts.append("")

    return "\n".join(parts)


def classify_batch(batch: list[dict]) -> list[dict] | None:
    """Send a batch of claims to Claude for classification.

    Returns list of {claim_id, claim_type, consensus_type, type_rationale, consensus_rationale}.
    """
    user_text = _build_batch_prompt(batch)
    result = _call_claude(CLASSIFY_SYSTEM_PROMPT, user_text)

    if result is None:
        return None

    classified = result if isinstance(result, list) else result.get("claims", [])

    if not classified:
        print(f"  [WARN] Empty classification response")
        return None

    # Validate and clamp values
    for item in classified:
        if item.get("claim_type") not in VALID_CLAIM_TYPES:
            print(f"  [WARN] Invalid claim_type '{item.get('claim_type')}' for {item.get('claim_id', '?')[:8]}, defaulting to efficacy")
            item["claim_type"] = "efficacy"
        if item.get("consensus_type") not in VALID_CONSENSUS_TYPES:
            print(f"  [WARN] Invalid consensus_type '{item.get('consensus_type')}' for {item.get('claim_id', '?')[:8]}, defaulting to genuine_uncertainty")
            item["consensus_type"] = "genuine_uncertainty"

    return classified


def store_classifications(sb, classifications: list[dict], output_path: Path | None = None) -> int:
    """Update signal_claims with claim_type and consensus_type.

    Tries three strategies in order:
      1. RPC classify_claim() — bypasses PostgREST column cache
      2. Raw HTTP PATCH — bypasses supabase-py client
      3. Local JSON fallback — saves to file for manual SQL import

    Always saves a local JSON backup regardless of DB success.

    Returns count of rows updated in DB (0 if only JSON written).
    """
    import requests as req

    # Always save local JSON backup
    if output_path:
        with open(output_path, "w") as f:
            json.dump(classifications, f, indent=2)
        print(f"  Saved {len(classifications)} classifications to {output_path}")

    # Strategy 1: Try RPC
    updated = 0
    first_item = classifications[0] if classifications else None
    if first_item:
        try:
            sb.rpc("classify_claim", {
                "p_claim_id": first_item["claim_id"],
                "p_claim_type": first_item["claim_type"],
                "p_consensus_type": first_item["consensus_type"],
            }).execute()
            print("  RPC classify_claim works — using RPC strategy")
            updated = 1
            for item in classifications[1:]:
                cid = item.get("claim_id")
                ct = item.get("claim_type")
                cst = item.get("consensus_type")
                if not cid or not ct or not cst:
                    continue
                try:
                    sb.rpc("classify_claim", {
                        "p_claim_id": cid,
                        "p_claim_type": ct,
                        "p_consensus_type": cst,
                    }).execute()
                    updated += 1
                except Exception as exc:
                    print(f"  [ERROR] RPC failed for {cid}: {exc}")
            return updated
        except Exception:
            print("  RPC not available, trying raw HTTP PATCH...")

    # Strategy 2: Try raw HTTP PATCH
    supabase_url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    if first_item:
        try:
            r = req.patch(
                f"{supabase_url}/rest/v1/signal_claims?id=eq.{first_item['claim_id']}",
                json={"claim_type": first_item["claim_type"], "consensus_type": first_item["consensus_type"]},
                headers=headers,
            )
            if r.status_code < 300:
                print("  Raw HTTP PATCH works — using HTTP strategy")
                updated = 1
                for item in classifications[1:]:
                    cid = item.get("claim_id")
                    ct = item.get("claim_type")
                    cst = item.get("consensus_type")
                    if not cid or not ct or not cst:
                        continue
                    try:
                        r = req.patch(
                            f"{supabase_url}/rest/v1/signal_claims?id=eq.{cid}",
                            json={"claim_type": ct, "consensus_type": cst},
                            headers=headers,
                        )
                        if r.status_code < 300:
                            updated += 1
                        else:
                            print(f"  [ERROR] PATCH {cid}: {r.status_code} {r.text[:100]}")
                    except Exception as exc:
                        print(f"  [ERROR] PATCH failed for {cid}: {exc}")
                return updated
            else:
                print(f"  Raw HTTP PATCH failed ({r.status_code}), falling back to JSON only")
        except Exception as exc:
            print(f"  Raw HTTP PATCH error: {exc}, falling back to JSON only")

    # Strategy 3: JSON-only (already saved above)
    if output_path:
        print(f"\n  DB writes blocked by PostgREST schema cache.")
        print(f"  Classifications saved to: {output_path}")
        print(f"  Apply with SQL: see apply_classifications.sql")
    return 0


# ---------------------------------------------------------------------------
# CLI orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Classify claims by type and consensus status using Claude API."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be classified without API calls or DB writes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-classify claims that already have claim_type set",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Classify only first N claims (0 = all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Claims per Claude API call (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--issue-slug",
        type=str,
        default="glp1-drugs",
        help="Topic slug (default: glp1-drugs)",
    )
    args = parser.parse_args()

    issue_slug = args.issue_slug
    try:
        topic = get_topic(issue_slug)
        print(f"Topic: {topic['title']} ({issue_slug})")
    except KeyError:
        # Topic not in static config — look up title from Supabase
        sb_tmp = _get_supabase()
        resp = sb_tmp.table("signal_issues").select("title").eq("slug", issue_slug).execute()
        title = resp.data[0]["title"] if resp.data else issue_slug
        print(f"Topic: {title} ({issue_slug}) [from DB]")

    sb = _get_supabase()
    issue_id, claims = load_claims(sb, issue_slug)

    # Filter to unclassified claims unless --force
    if not args.force:
        unclassified = [c for c in claims if not c.get("claim_type")]
        if len(unclassified) < len(claims):
            print(f"Skipping {len(claims) - len(unclassified)} already-classified claims (use --force to re-classify)")
        claims = unclassified

    if not claims:
        print("All claims already classified. Use --force to re-classify.")
        return

    if args.limit:
        claims = claims[:args.limit]
        print(f"Limited to first {args.limit} claims")

    # --- Dry run ---
    if args.dry_run:
        print(f"\n--- DRY RUN MODE (no API calls, no DB writes) ---\n")
        print(f"Claims to classify: {len(claims)}")
        print(f"Batch size: {args.batch_size}")
        n_batches = math.ceil(len(claims) / args.batch_size)
        print(f"API calls needed: {n_batches}")

        by_cat = defaultdict(int)
        for c in claims:
            by_cat[c.get("category", "unknown")] += 1
        print(f"\nBy category:")
        for cat, count in sorted(by_cat.items()):
            print(f"  {cat}: {count}")
        return

    # --- Live mode ---
    print(f"\n{'='*60}")
    print(f"CLASSIFYING {len(claims)} CLAIMS")
    print(f"{'='*60}\n")

    n_batches = math.ceil(len(claims) / args.batch_size)
    all_classified: list[dict] = []
    failed_batches = 0

    for batch_idx in range(n_batches):
        start = batch_idx * args.batch_size
        batch = claims[start:start + args.batch_size]

        print(f"  batch {batch_idx + 1}/{n_batches} ({len(batch)} claims)...", end=" ", flush=True)

        classified = classify_batch(batch)

        if classified:
            all_classified.extend(classified)
            print(f"OK ({len(classified)} classified)")
        else:
            failed_batches += 1
            print("FAILED")

        # Delay between API calls
        if batch_idx < n_batches - 1:
            time.sleep(0.5)

    print(f"\nClassification complete: {len(all_classified)} claims in "
          f"{n_batches} batches ({failed_batches} failed)")

    if not all_classified:
        print("No classifications to store.")
        return

    # --- Store results ---
    output_dir = SCRIPTS_DIR / "output"
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / f"classifications_{issue_slug}.json"
    sql_path = output_dir / f"apply_classifications_{issue_slug}.sql"

    print(f"Storing classifications...")
    updated = store_classifications(sb, all_classified, output_path=json_path)
    print(f"Updated {updated} claims in DB")

    # Generate SQL apply script (always, as backup or primary import path)
    _generate_sql_script(all_classified, sql_path)

    # --- Summary ---
    print(f"\n{'='*60}")
    print("CLASSIFICATION COMPLETE")
    print(f"{'='*60}")

    type_dist = defaultdict(int)
    consensus_dist = defaultdict(int)
    for item in all_classified:
        type_dist[item.get("claim_type", "unknown")] += 1
        consensus_dist[item.get("consensus_type", "unknown")] += 1

    print(f"\nClaim type distribution:")
    for ct in VALID_CLAIM_TYPES:
        count = type_dist.get(ct, 0)
        pct = (count / len(all_classified) * 100) if all_classified else 0
        print(f"  {ct:>20}: {count:>3} ({pct:.0f}%)")

    print(f"\nConsensus type distribution:")
    for ct in VALID_CONSENSUS_TYPES:
        count = consensus_dist.get(ct, 0)
        pct = (count / len(all_classified) * 100) if all_classified else 0
        print(f"  {ct:>25}: {count:>3} ({pct:.0f}%)")

    if updated == 0:
        print(f"\n--- DB NOT UPDATED (PostgREST schema cache stale) ---")
        print(f"Run this SQL in Supabase SQL Editor to apply:")
        print(f"  {sql_path}")


def _generate_sql_script(classifications: list[dict], sql_path: Path):
    """Generate a SQL script to apply classifications via SQL Editor."""
    lines = [
        "-- Auto-generated by classify_claims.py",
        "-- Apply claim_type and consensus_type classifications to signal_claims",
        "-- Run in Supabase SQL Editor if PostgREST schema cache is stale",
        "",
        "BEGIN;",
        "",
    ]

    for item in classifications:
        cid = item.get("claim_id", "")
        ct = item.get("claim_type", "")
        cst = item.get("consensus_type", "")
        if cid and ct and cst:
            lines.append(
                f"UPDATE signal_claims SET claim_type = '{ct}', "
                f"consensus_type = '{cst}' WHERE id = '{cid}';"
            )

    lines.extend(["", "COMMIT;", ""])
    sql_path.write_text("\n".join(lines))
    print(f"  Generated SQL apply script: {sql_path}")


if __name__ == "__main__":
    main()
