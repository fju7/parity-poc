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

from signal_model import MODEL as SIGNAL_MODEL, prompt_version, warn_if_unpinned
from topic_config import get_topic

# Configured in signal_model so pinning is one change, not six.
SCORING_MODEL = SIGNAL_MODEL
BACKOFF_DELAYS = [2, 5, 10]


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


# The model string the API actually used on the most recent call. Read off the
# response rather than assumed from SCORING_MODEL, so the recorded provenance
# is correct even when the configured value is an unpinned alias.
LAST_RESOLVED_MODEL: str | None = None

# A malformed response is not a permanent failure. In a 52-category sweep the
# model once answered with its reasoning instead of JSON; that call was simply
# lost. Retrying costs one call and recovers it.
JSON_RETRIES = 2


def _extract_text(response) -> str:
    """Concatenate the text blocks of a response and reduce them to JSON.

    Strips a code fence, and — as a fallback — pulls the first balanced {...}
    or [...] out of a reply that narrated its reasoning first. That happens on
    the hardest categories: social-media/depression_anxiety (47 claims, genuine
    conflicting effect estimates) answered with "**Step 1: Check for debated
    status first.**" and its working, three attempts running. The prompt now
    forbids the preamble; this makes a lapse recoverable rather than fatal.
    """
    raw = "".join(b.text for b in response.content if hasattr(b, "text")).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    raw = raw.strip()
    if raw[:1] in ("{", "["):
        return raw

    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", raw, re.S)
    if fenced:
        return fenced.group(1).strip()

    salvaged = _first_json_value(raw)
    return salvaged if salvaged is not None else raw


def _first_json_value(text: str) -> str | None:
    """Return the first balanced JSON object or array in `text`, or None.

    Brace counting rather than a regex, because the payload contains prose with
    braces in it. String literals and escapes are tracked so a `{` inside a
    summary_text does not throw the depth off.
    """
    # Whichever bracket appears FIRST wins. Trying objects before arrays would
    # return the first element of a top-level array instead of the array.
    candidates = [(text.find(o), o, c) for o, c in (("{", "}"), ("[", "]")) if text.find(o) != -1]
    for start, opener, closer in sorted(candidates):
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 4096) -> dict | list | None:
    """Call Claude and return parsed JSON.

    Retries on 529 (overloaded) and, separately, on a response that is not
    valid JSON. Records the resolved model in LAST_RESOLVED_MODEL.
    """
    global LAST_RESOLVED_MODEL
    client = _get_anthropic_client()

    for json_attempt in range(JSON_RETRIES + 1):
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

        LAST_RESOLVED_MODEL = getattr(response, "model", None) or SCORING_MODEL
        raw_text = _extract_text(response)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            if json_attempt < JSON_RETRIES:
                print(f"  [RETRY] Response was not JSON, attempt {json_attempt + 1}/{JSON_RETRIES}...")
                time.sleep(1)
                continue
            tail = raw_text[-200:] if len(raw_text) > 200 else ""
            print(f"  [ERROR] Invalid JSON from Claude after {JSON_RETRIES + 1} attempts.")
            print(f"          head: {raw_text[:240]}")
            if tail:
                print(f"          tail: {tail}")
                print("          (if the tail looks like truncated JSON, raise max_tokens)")
            return None

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


def load_scored_claims(sb, issue_slug: str) -> tuple[str, dict[str, list[dict]]]:
    """Load all scored claims grouped by category.

    Returns (issue_id, {category: [claim_dicts]}) where each claim has:
      id, claim_text, category, specificity, composite_score, evidence_category
    """
    resp = sb.table("signal_issues").select("id").eq("slug", issue_slug).execute()
    if not resp.data:
        print(f"ERROR: No '{issue_slug}' issue found. Run earlier pipeline steps first.")
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

def _build_consensus_system_prompt(topic: dict) -> str:
    """Build the consensus mapping system prompt dynamically from topic config."""
    return f"""You are an evidence analyst for an evidence intelligence platform. You are assessing the overall consensus state for a category of claims about {topic['prompt_subject']}.

You will receive a list of claims with their evidence scores. Assess whether the evidence in this category shows consensus, debate, or uncertainty.

Context: {topic['prompt_detail']}

## Consensus Status — work through these IN ORDER, silently, and stop at the first that fits

**1. debated** — Two or more well-scored claims support conclusions that cannot both be true, and you can name the claims on each side. Substantive tension, not minor variation in magnitude.
Conflicting evidence is ALWAYS debated. It is never "uncertain", however unresolved the conflict feels.

**2. uncertain** — No conflict, but the evidence still cannot support a conclusion: too few claims, too early-stage, too indirect, or the claims do not actually address the question.
Uncertain means the evidence is THIN. It does not mean the evidence disagrees.

**3. consensus** — The well-scored claims point the same direction. Minor variation in specifics is still consensus.
A category consisting of undisputed factual claims — prices, dates, dosages, regulatory status — is consensus. Facts that all hold at once are not a debate.

## Output Format

Return a JSON object:
{{
  "consensus_status": "consensus" | "debated" | "uncertain",
  "summary_text": "2-3 sentence plain-language summary of what the evidence says in this category. Written for a general audience — no jargon. Should convey the overall direction and strength of evidence.",
  "supporting_claim_ids": ["id1", "id2", ...],
  "arguments_for": "If debated: 1-2 sentences describing the main argument supported by evidence. If not debated: null.",
  "arguments_against": "If debated: 1-2 sentences describing the opposing argument supported by evidence. If not debated: null.",
  "for_claim_ids": ["id1", "id2", ...],
  "against_claim_ids": ["id1", "id2", ...]
}}

## Rules
- Decide consensus_status FIRST, using only the Consensus Status Definitions above. Every rule below describes how to RECORD that decision; none of them is a reason to change it. A category is never "consensus" merely because that produces a shorter or simpler answer.
- supporting_claim_ids should include the 3-8 most informative claims for this assessment (use the claim IDs provided)
- For "debated" status, for_claim_ids and against_claim_ids must list the specific claim IDs each argument rests on — the actual evidence behind arguments_for and arguments_against respectively. A reader should be able to click through and check your reasoning.
- A claim ID may appear in only one of for_claim_ids / against_claim_ids, never both. Claims that inform the assessment without favouring either side belong in neither — leave them to supporting_claim_ids.
- The two id lists need not be the same length. If one side of a debate rests on more or better-scored evidence, let the lists be uneven; that asymmetry is information, not a flaw to correct. This governs how you divide the evidence of a debate you have ALREADY identified. It is never grounds for concluding that no debate exists.
- Weight higher-scored claims more heavily in your assessment
- summary_text must be understandable to someone with no medical background
- For "debated" status, both arguments_for and arguments_against must reference specific evidence
- For "consensus" or "uncertain" status, arguments_for and arguments_against should be null
- Do not take sides — describe what the evidence shows
- Return the JSON object and NOTHING else. No preamble, no numbered reasoning, no commentary before or after it. Reason silently and emit only the object."""


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


def map_category(category: str, claims: list[dict], consensus_prompt: str) -> dict | None:
    """Send category claims to Claude for consensus assessment.

    Returns consensus dict or None on failure.
    """
    user_text = _build_category_prompt(category, claims)
    result = _call_claude(consensus_prompt, user_text)

    if result is None:
        print(f"  [FAIL] No response for category: {category}")
        return None

    # Validate required fields
    status = result.get("consensus_status")
    if status not in ("consensus", "debated", "uncertain"):
        print(f"  [WARN] Invalid consensus_status '{status}' for {category}, defaulting to 'uncertain'")
        result["consensus_status"] = "uncertain"

    _validate_side_claim_ids(result, category, claims)

    return result


def _validate_side_claim_ids(result: dict, category: str, claims: list[dict]) -> None:
    """Scrub for_claim_ids / against_claim_ids in place (migration 071).

    A hallucinated id would render as a missing claim or vanish silently, and an
    id claimed by both sides would misrepresent the debate. Neither is allowed
    through: ids are intersected with the claims actually sent to the model, and
    any id appearing on both sides is dropped from both. Anything discarded is
    logged rather than swallowed — a high drop rate means the prompt is failing
    and we want to see that in the run output.
    """
    known = {str(c["id"]) for c in claims if c.get("id")}

    for_ids = [str(i) for i in (result.get("for_claim_ids") or [])]
    against_ids = [str(i) for i in (result.get("against_claim_ids") or [])]

    unknown = [i for i in for_ids + against_ids if i not in known]
    if unknown:
        print(f"  [WARN] {category}: dropped {len(unknown)} claim id(s) not in this category")

    for_ids = [i for i in for_ids if i in known]
    against_ids = [i for i in against_ids if i in known]

    overlap = set(for_ids) & set(against_ids)
    if overlap:
        print(f"  [WARN] {category}: dropped {len(overlap)} claim id(s) cited on both sides")
        for_ids = [i for i in for_ids if i not in overlap]
        against_ids = [i for i in against_ids if i not in overlap]

    # Side attribution only means anything on a debated category.
    if result.get("consensus_status") != "debated":
        result["for_claim_ids"] = None
        result["against_claim_ids"] = None
        return

    result["for_claim_ids"] = for_ids or None
    result["against_claim_ids"] = against_ids or None

    if not for_ids and not against_ids:
        print(f"  [WARN] {category}: debated but no side attribution returned")


def store_consensus(sb, issue_id: str, category: str, consensus: dict,
                    system_prompt: str | None = None) -> bool:
    """Insert one consensus row. Returns True on success."""
    row = {
        "issue_id": issue_id,
        "category": category,
        "consensus_status": consensus["consensus_status"],
        "summary_text": consensus.get("summary_text", ""),
        "supporting_claim_ids": consensus.get("supporting_claim_ids", []),
        "arguments_for": consensus.get("arguments_for"),
        "arguments_against": consensus.get("arguments_against"),
        # Migration 071. Left NULL rather than [] when absent so the frontend can
        # tell "this row predates side attribution" from "this side has no claims".
        "for_claim_ids": consensus.get("for_claim_ids") or None,
        "against_claim_ids": consensus.get("against_claim_ids") or None,
        # Migration 073. The resolved model, not the configured one — those
        # differ whenever SIGNAL_MODEL is an alias, and it is the resolved
        # value that explains the output.
        "model_id": LAST_RESOLVED_MODEL,
        "prompt_version": prompt_version(system_prompt) if system_prompt else None,
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
    parser.add_argument(
        "--issue-slug",
        type=str,
        default="glp1-drugs",
        help="Topic slug (default: glp1-drugs)",
    )
    args = parser.parse_args()

    issue_slug = args.issue_slug
    topic = get_topic(issue_slug)
    categories = topic["categories"]
    print(f"Topic: {topic['title']} ({issue_slug})")

    sb = _get_supabase()
    issue_id, by_category = load_scored_claims(sb, issue_slug)

    # --- Dry run ---
    if args.dry_run:
        print(f"\n--- DRY RUN MODE (no API calls, no DB writes) ---\n")
        existing = get_existing_consensus(sb, issue_id)
        print(f"Existing consensus rows: {len(existing)}")
        if existing:
            for row in existing:
                print(f"  {row['category']}: {row['consensus_status']}")

        print(f"\nCategories to map:")
        for cat in categories:
            group = by_category.get(cat, [])
            scored = sum(1 for c in group if c.get("composite_score") is not None)
            avg = 0
            if scored:
                avg = sum(c["composite_score"] for c in group if c.get("composite_score") is not None) / scored
            print(f"  {cat}: {len(group)} claims ({scored} scored, avg composite {avg:.2f})")

        print(f"\nAPI calls needed: {len([c for c in categories if by_category.get(c)])}")
        return

    # --- Idempotency check ---
    existing = get_existing_consensus(sb, issue_id)
    if existing and not args.force:
        print(f"\nFound {len(existing)} existing consensus rows:")
        for row in existing:
            print(f"  {row['category']}: {row['consensus_status']}")
        print("Use --force to clear and re-map.")
        return

    # --- Map every category BEFORE touching the database ---
    #
    # This used to clear the existing rows first and then rebuild them one
    # category at a time. A failure partway through left the topic with a
    # partial consensus map — and consensus drives the contested lede and the
    # debates panel, so the live topic page would silently lose sections.
    # There is no transaction available here, so the order is the safeguard:
    # nothing is deleted until every category has been mapped successfully.
    consensus_prompt = _build_consensus_system_prompt(topic)
    print(f"\nModel: {SCORING_MODEL}   prompt: {prompt_version(consensus_prompt)}")
    warn_if_unpinned(SCORING_MODEL)
    print(f"\nMapping consensus for {len(categories)} categories...\n")

    mapped: dict[str, dict] = {}
    failed = 0

    for cat in categories:
        group = by_category.get(cat, [])
        if not group:
            print(f"[{cat}] No claims, skipping")
            continue

        scored_count = sum(1 for c in group if c.get("composite_score") is not None)
        print(f"[{cat}] Mapping {len(group)} claims ({scored_count} scored)...", end=" ", flush=True)

        consensus = map_category(cat, group, consensus_prompt)
        if consensus:
            mapped[cat] = consensus
            print(f"-> {consensus['consensus_status']}")
        else:
            failed += 1
            print("-> API FAILED")

        # Delay between API calls
        time.sleep(0.5)

    if failed:
        print(f"\n[ABORT] {failed} categor{'y' if failed == 1 else 'ies'} failed to map.")
        print("Existing consensus rows were NOT touched. Fix the failure and re-run.")
        return

    if not mapped:
        print("\n[ABORT] Nothing mapped. Existing consensus rows were NOT touched.")
        return

    # --- Compare against what is already published, then swap ---
    previous = {row["category"]: row["consensus_status"] for row in existing}
    flips = [
        (cat, previous[cat], c["consensus_status"])
        for cat, c in mapped.items()
        if cat in previous and previous[cat] != c["consensus_status"]
    ]
    if flips:
        print(f"\n[NOTICE] {len(flips)} categor{'y' if len(flips) == 1 else 'ies'} changed status:")
        for cat, was, now in flips:
            print(f"  {cat}: {was} -> {now}")
        lost = [f for f in flips if f[1] == "debated" and f[2] != "debated"]
        if lost:
            print(f"  {len(lost)} of these STOPPED being debated. If that was not expected,")
            print("  the prompt is flattening disagreement — check before publishing.")

    if existing:
        print(f"\nAll categories mapped. Clearing {len(existing)} existing rows...")
        cleared = clear_existing_consensus(sb, issue_id)
        print(f"Cleared {cleared} rows.")

    results = {}
    succeeded = 0
    for cat, consensus in mapped.items():
        if store_consensus(sb, issue_id, cat, consensus, consensus_prompt):
            results[cat] = consensus
            succeeded += 1
        else:
            failed += 1
            print(f"[{cat}] -> STORE FAILED")

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
