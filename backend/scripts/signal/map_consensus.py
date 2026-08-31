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
from collections import Counter, defaultdict
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


def _metered(client, *, role=""):
    """Wrap the client so every call lands in the spend ledger.

    By PATH, never by putting backend/scripts on sys.path: scripts/signal/ is a
    package named `signal` and shadows the stdlib from there, which broke the
    gate outright on 2026-08-31.
    """
    try:
        import importlib.util
        from pathlib import Path as _P
        _p = _P(__file__).resolve().parents[1] / "spend_ledger.py"
        _s = importlib.util.spec_from_file_location("spend_ledger", _p)
        _m = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_m)
        return _m.metered(client, script=_P(__file__).name, role=role)
    except Exception:
        return client


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
        _anthropic_client = _metered(anthropic.Anthropic(api_key=api_key))
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


def clear_existing_consensus(sb, issue_id: str, categories: list[str] | None = None) -> int:
    """Delete consensus rows for this issue. Returns count deleted.

    With `categories`, deletes ONLY those. This matters: the write path clears
    before it re-inserts, so a run limited to one category that cleared the
    whole issue would delete every other category's row and never put it back.
    Passing None keeps the original whole-issue behaviour.
    """
    q = sb.table("signal_consensus").delete().eq("issue_id", issue_id)
    if categories is not None:
        if not categories:
            return 0
        q = q.in_("category", list(categories))
    return len((q.execute()).data or [])


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

    # R-01 and the two distinctions that produced it, 2026-08-31.
    #
    # The threshold between consensus and debated had never been written down
    # anywhere. The model applied its own, and four categories flipped across
    # runs with no code change, some of them sitting on the line. A rule nobody
    # has stated cannot be applied consistently and cannot be argued with.
    #
    # The rule is the operator's, in his words: "a real but minority dispute
    # does make a 41 claim category debated. Many times a minority turns out to
    # be more right than wrong." An evidence assessment that rounds minority
    # positions away is doing the thing it exists to criticise.
    #
    # The two distinctions come from reading three drifted categories at source
    # on 2026-08-31, where the model had got each one wrong in a different way.
    RULE = (
        "HOW TO DECIDE consensus vs debated:\n"
        "\n"
        "1. A REAL BUT MINORITY DISPUTE MAKES THE CATEGORY DEBATED. Do not weigh "
        "by headcount. If a substantive, credible position contradicts the "
        "majority on the question this category names, the category is debated, "
        "even if most claims agree. A minority is often right. The only exception "
        "is a position too small or unqualified to take seriously, and that "
        "should be rare.\n"
        "\n"
        "2. A CLAIM ABOUT EVIDENCE QUALITY IS NOT A SECOND SIDE. 'No head-to-head "
        "randomised trial exists', 'the comparison is indirect', 'follow-up is "
        "short' — these describe how good the evidence is, not a competing answer "
        "to the question. A category where every substantive claim agrees, plus "
        "one noting the evidence is indirect, is CONSENSUS with a caveat.\n"
        "\n"
        "3. AGREEMENT ABOUT FINDINGS IS NOT AGREEMENT ABOUT EXPLANATIONS. If the "
        "category asks about a mechanism, a cause, or a reason, then unanimity on "
        "what was OBSERVED does not settle it. Where the claims still call the "
        "explanation 'proposed', or name competing candidate mechanisms, the "
        "category is DEBATED however consistent the observations are.\n"
    )

    parts = [
        RULE,
        "",
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


def _sides(c: dict) -> tuple[int, int]:
    return len(c.get("for_claim_ids") or []), len(c.get("against_claim_ids") or [])


# A run's lean is DECISIVE only if it clears both a floor and a share. One
# claim of difference is not a direction, and neither is a difference smaller
# than a tenth of the claims that were attributed at all. Both tests are
# needed: 6/5 clears neither, 10/3 clears both, 3/2 clears the share but not
# the floor and is correctly read as a tie.
DECISIVE_MIN_CLAIMS = 2
DECISIVE_MIN_SHARE = 0.10


def side_lean(f: int, a: int) -> int:
    """-1, 0 or +1: the direction of a run's side balance, 0 meaning too close to call."""
    total = f + a
    if total == 0:
        return 0
    diff = f - a
    if abs(diff) < DECISIVE_MIN_CLAIMS or abs(diff) / total <= DECISIVE_MIN_SHARE:
        return 0
    return 1 if diff > 0 else -1


def classify_sides(observed: list[list[int]]) -> str:
    """Read K runs of (for, against) counts as 'lean', 'tie' or 'unstable'.

    Three situations look alike in a boolean and are not alike at all:

      unstable  social-media/methodology: 10/3, 2/10, 3/8, 11/4, 4/10.
                Decisive leans in BOTH directions. The model partitions the
                same claims the same way each time and swaps which half is
                'for', because the category names a subject rather than a
                proposition and two near-inverse propositions fit it. Nothing
                about the balance can be published.

      tie       social-media/platform_design: 6/5, 6/6, 6/7, 6/6, 6/6.
                The 'for' side does not move at all across five runs; only the
                'against' side wanders by one, which straddles the tie and so
                reverses the SIGN of a lean that was never there. This is a
                stable measurement of an evenly divided question. It is
                publishable, but as a tie, never as a direction.

      lean      breast-cancer/survival_outcomes: 5/2 five times running.
                A direction that held every time it was decisive.

    The earlier boolean called platform_design unstable, which was a false
    positive of our own guard: it tested the sign of the difference and a sign
    is meaningless within a claim of zero.
    """
    leans = [side_lean(f, a) for f, a in observed]
    decisive = [x for x in leans if x != 0]
    if 1 in decisive and -1 in decisive:
        return "unstable"
    if len(decisive) * 2 > len(leans):
        return "lean"
    return "tie"


def reconcile(runs: list[dict]) -> dict:
    """Collapse K independent mappings of one category into what we can honestly store.

    Returns the chosen mapping with `runs`, `agreement`, `sides_stable`,
    `sides_balance` and `sides_observed` attached.

    Status and side attribution are measured separately because on 2026-08-27
    they behaved differently. Across three sweeps of 53 categories the STATUS
    never moved once, while side attribution for social-media/methodology came
    back 10/3, 2/10, 3/8, 11/4, 4/10 and 10/3 again — three each way, on the
    same 43 claims and the same prompt hash, in one day.

    So: the modal status is stored with the fraction of runs that agreed, and
    the side attribution is stored ONLY if it survives classify_sides. When it
    does not, the side lists are dropped and sides_stable is False, because
    publishing a balance that reverses tells a reader the field is divided
    when what is actually true is that we cannot measure it. That is our
    instability dressed up as the world's, and it is the error this whole
    project exists to name.

    A tie is NOT that error. A category measured at 6/5, 6/6, 6/7 is being
    measured well and is genuinely close, and suppressing it would hide a real
    finding. sides_balance carries the difference through to the frontend.
    """
    statuses = [r["consensus_status"] for r in runs]
    modal = Counter(statuses).most_common(1)[0][0]
    agreeing = [r for r in runs if r["consensus_status"] == modal]

    # Content comes from the first run that produced the modal status — an
    # arbitrary but deterministic choice, and the alternative (stitching prose
    # from several runs) would produce a summary no single run ever wrote.
    chosen = dict(agreeing[0])
    chosen["runs"] = len(runs)
    chosen["agreement"] = round(len(agreeing) / len(runs), 3) if len(runs) > 1 else None

    observed = [list(_sides(r)) for r in agreeing]
    chosen["sides_observed"] = observed if len(runs) > 1 else None

    if len(runs) == 1:
        chosen["sides_stable"] = None
        chosen["sides_balance"] = None
        return chosen

    # A run that put every attributed claim on one side while others did not is
    # a coverage failure, not a balance. Kept separate from classify_sides
    # because it is a different fault with the same remedy.
    collapsed = any(f == 0 or a == 0 for f, a in observed)
    balance = "unstable" if collapsed else classify_sides(observed)

    chosen["sides_balance"] = balance
    chosen["sides_stable"] = balance != "unstable"
    if not chosen["sides_stable"]:
        # Withheld, not missing. Migration 074's CHECK enforces the pairing.
        chosen["for_claim_ids"] = None
        chosen["against_claim_ids"] = None
    return chosen


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
        # Migration 074. Absent on a single-run map, which is what every row
        # written before repeated measurement existed was.
        "runs": consensus.get("runs"),
        "agreement": consensus.get("agreement"),
        "sides_stable": consensus.get("sides_stable"),
        "sides_observed": consensus.get("sides_observed"),
        # Migration 075. 'lean', 'tie' or 'unstable' — the three-way reading
        # that sides_stable flattens into a boolean.
        "sides_balance": consensus.get("sides_balance"),
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
    parser.add_argument(
        "--measure-only",
        action="store_true",
        help="Map and report, write nothing. The only safe way to measure a category "
             "whose published label was a deliberate decision to leave alone — --force "
             "would overwrite that decision with whatever this run happens to produce.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Map each category this many times and store the modal verdict with "
             "its agreement rate. Side attribution is stored only if its direction "
             "held across runs. Default 1, which is the original behaviour.",
    )
    parser.add_argument(
        "--category",
        action="append",
        help="Map only this category. Repeatable. Without it, every category in "
             "the topic is re-mapped, which will overwrite categories whose "
             "current label was a deliberate decision to leave alone.",
    )
    args = parser.parse_args()

    issue_slug = args.issue_slug
    topic = get_topic(issue_slug)
    categories = topic["categories"]
    print(f"Topic: {topic['title']} ({issue_slug})")

    if args.runs < 1:
        print("[ERROR] --runs must be at least 1.")
        sys.exit(2)
    if args.runs > 1:
        print(f"Repeated measurement: {args.runs} runs per category, "
              f"{args.runs}x the API cost.")

    only = None
    if args.category:
        only = list(dict.fromkeys(args.category))
        unknown = [c for c in only if c not in categories]
        if unknown:
            print(f"[ERROR] Not categories of {issue_slug}: {', '.join(unknown)}")
            print(f"        Known: {', '.join(categories)}")
            sys.exit(2)
        categories = [c for c in categories if c in only]
        untouched = [c for c in topic["categories"] if c not in only]
        print(f"Limited to {len(categories)}: {', '.join(categories)}")
        if untouched:
            print(f"NOT touched ({len(untouched)}): {', '.join(untouched)}")

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

        print(f"\nCategories to map{' (limited by --category)' if only else ''}:")
        for cat in categories:
            group = by_category.get(cat, [])
            scored = sum(1 for c in group if c.get("composite_score") is not None)
            avg = 0
            if scored:
                avg = sum(c["composite_score"] for c in group if c.get("composite_score") is not None) / scored
            print(f"  {cat}: {len(group)} claims ({scored} scored, avg composite {avg:.2f})")

        billable = len([c for c in categories if by_category.get(c)])
        if args.runs > 1:
            print(f"\nAPI calls needed: {billable * args.runs}"
                  f"  ({billable} categor{'y' if billable == 1 else 'ies'} x {args.runs} runs)")
        else:
            print(f"\nAPI calls needed: {billable}")
        return

    # --- Idempotency check ---
    existing = get_existing_consensus(sb, issue_id)
    if existing and not args.force and not args.measure_only:
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

        observations = []
        for attempt in range(args.runs):
            got = map_category(cat, group, consensus_prompt)
            if got:
                observations.append(got)
            if attempt < args.runs - 1:
                time.sleep(0.5)

        if not observations:
            failed += 1
            print("-> API FAILED")
        elif args.runs > 1 and len(observations) < args.runs:
            # Some runs succeeded and some did not. Reconciling a partial set
            # would report an agreement rate over a sample we did not choose,
            # which is a worse lie than no number at all.
            failed += 1
            print(f"-> ONLY {len(observations)}/{args.runs} RUNS SUCCEEDED")
        else:
            consensus = reconcile(observations)
            mapped[cat] = consensus
            if args.runs > 1:
                seen = Counter(o["consensus_status"] for o in observations)
                spread = " ".join(f"{s}x{n}" for s, n in seen.most_common())
                line = (f"-> {consensus['consensus_status']}  "
                        f"agreement {consensus['agreement']:.0%}  [{spread}]")
                bal = consensus.get("sides_balance")
                if bal == "unstable":
                    line += f"  SIDES UNSTABLE {consensus['sides_observed']} — withheld"
                elif bal == "tie":
                    line += f"  SIDES TIED {consensus['sides_observed']} — publish as even, not as a lean"
                print(line)
            else:
                print(f"-> {consensus['consensus_status']}")

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

    if args.measure_only:
        print(f"\n{'=' * 60}")
        print("MEASURE ONLY — nothing was cleared, nothing was written")
        print(f"{'=' * 60}")
        for cat, c in mapped.items():
            pub = next((r["consensus_status"] for r in existing if r["category"] == cat), "none")
            line = f"  {cat}: published={pub}  measured={c['consensus_status']}"
            if c.get("agreement") is not None:
                line += f"  agreement {c['agreement']:.0%}"
            print(line)
            if c.get("sides_observed"):
                bal = c.get("sides_balance")
                mark = {"lean": "stable lean",
                        "tie": "stable TIE — no direction",
                        "unstable": "UNSTABLE — direction reverses"}.get(bal, str(bal))
                print(f"    sides {mark}: {c['sides_observed']}")
        return

    scope = list(mapped.keys()) if only else None
    doomed = [r for r in existing if scope is None or r["category"] in scope]
    if doomed:
        print(f"\nAll categories mapped. Clearing {len(doomed)} existing row"
              f"{'' if len(doomed) == 1 else 's'}"
              f"{' (scoped to --category)' if scope else ''}...")
        for r in doomed:
            print(f"  clearing {r['category']} ({r['consensus_status']})")
        cleared = clear_existing_consensus(sb, issue_id, scope)
        print(f"Cleared {cleared} rows.")
        if scope is not None and cleared != len(doomed):
            print(f"[WARN] Expected to clear {len(doomed)} but cleared {cleared}.")

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
