"""Parity Signal Intelligence API.

Connects Signal evidence to billing products via CPT code mappings.
Provides evidence lookups and denial intelligence for appeal support.
Includes denial playbook population and pattern aggregation.
"""

import json
import logging

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signal", tags=["signal-intelligence"])

# Denial codes → likely payer analytical paths (shared across endpoints)
DENIAL_PATH_MAP = {
    "CO-50": "Payer likely weighted recency and rigor heavily, discounting older but well-replicated evidence.",
    "CO-97": "Payer applied narrow interpretation of medical necessity, likely underweighting consensus evidence.",
    "PR-204": "Payer required specific authorization criteria not met — check if evidence supports broader coverage.",
    "CO-4": "Service not covered under benefit plan — evidence may support medical necessity override.",
    "CO-11": "Diagnosis inconsistent with procedure — evidence may demonstrate clinical pathway.",
    "CO-56": "Payer classified service as experimental — evidence strength directly challenges this.",
    "CO-181": "Procedure code inconsistent with modifier — possible coding issue rather than evidence gap.",
}

_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


# ---------------------------------------------------------------------------
# Endpoint 1: Evidence for CPT Code
# ---------------------------------------------------------------------------

@router.get("/evidence-for-code")
async def evidence_for_code(
    cpt_code: str = Query(..., description="CPT code to look up"),
    icd10_code: str = Query(None, description="Optional ICD-10 diagnosis code"),
    context: str = Query(None, description="Optional clinical context"),
):
    """Look up Signal evidence for a CPT code.

    Finds matching Signal topic(s) via signal_cpt_mappings, returns
    evidence summary including score, verdict, key claims, and
    analytical paths.
    """
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    try:
        # Find mappings for this CPT code
        mappings_res = (
            sb.table("signal_cpt_mappings")
            .select("*")
            .eq("cpt_code", cpt_code)
            .order("relevance_score", desc=True)
            .execute()
        )
        mappings = mappings_res.data or []

        if not mappings:
            return JSONResponse(content={
                "cpt_code": cpt_code,
                "coverage": "none",
                "topic_slug": None,
                "topic_title": None,
                "score": None,
                "verdict": f"No Signal evidence coverage for CPT {cpt_code}.",
                "key_claims": [],
                "analytical_paths": [],
            })

        # Use the highest-relevance mapping
        best = mappings[0]
        topic_slug = best["topic_slug"]

        # Fetch topic
        issue_res = (
            sb.table("signal_issues")
            .select("id, slug, title, description")
            .eq("slug", topic_slug)
            .execute()
        )
        if not issue_res.data:
            return JSONResponse(content={
                "cpt_code": cpt_code,
                "coverage": "none",
                "topic_slug": topic_slug,
                "topic_title": None,
                "score": None,
                "verdict": f"Mapped topic '{topic_slug}' not found.",
                "key_claims": [],
                "analytical_paths": [],
            })

        issue = issue_res.data[0]
        issue_id = issue["id"]

        # Fetch claims with composites
        claims_res = (
            sb.table("signal_claims")
            .select("id, claim_text, category, claim_type, consensus_type")
            .eq("issue_id", issue_id)
            .execute()
        )
        claims = claims_res.data or []

        # Fetch composites
        claim_ids = [c["id"] for c in claims]
        composites = {}
        if claim_ids:
            chunk_size = 50
            for i in range(0, len(claim_ids), chunk_size):
                chunk = claim_ids[i:i + chunk_size]
                comp_res = (
                    sb.table("signal_claim_composites")
                    .select("claim_id, composite_score, evidence_category")
                    .in_("claim_id", chunk)
                    .execute()
                )
                for c in (comp_res.data or []):
                    composites[c["claim_id"]] = c

        # Compute overall score
        scores = [float(composites[cid]["composite_score"])
                  for cid in composites if composites[cid].get("composite_score")]
        overall_score = round(sum(scores) / len(scores), 2) if scores else None

        # Generate verdict from topic summary if available, otherwise from score
        verdict = None
        try:
            summary_res = (
                sb.table("signal_summaries")
                .select("summary_json")
                .eq("issue_id", issue_id)
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
            if summary_res.data:
                sj = summary_res.data[0].get("summary_json")
                if isinstance(sj, dict):
                    verdict = sj.get("overall_summary")
        except Exception:
            pass

        if not verdict:
            if overall_score and overall_score >= 4.0:
                verdict = f"Strong evidence base ({overall_score}/5.0) across {len(claims)} claims for {issue['title']}."
            elif overall_score and overall_score >= 3.0:
                verdict = f"Moderate evidence base ({overall_score}/5.0) across {len(claims)} claims for {issue['title']}."
            elif overall_score and overall_score >= 2.0:
                verdict = f"Mixed evidence ({overall_score}/5.0) for {issue['title']}. Review analytical paths."
            elif overall_score:
                verdict = f"Weak evidence base ({overall_score}/5.0) for {issue['title']}."
            else:
                verdict = f"Evidence available but not yet scored for {issue['title']}."

        # Key claims: top 5 by composite score
        scored_claims = []
        for c in claims:
            comp = composites.get(c["id"])
            if comp:
                scored_claims.append({
                    "claim_text": c["claim_text"],
                    "category": c.get("category"),
                    "claim_type": c.get("claim_type"),
                    "consensus_type": c.get("consensus_type"),
                    "composite_score": float(comp["composite_score"]) if comp.get("composite_score") else None,
                    "evidence_category": comp.get("evidence_category"),
                })
        scored_claims.sort(key=lambda x: x.get("composite_score") or 0, reverse=True)
        key_claims = scored_claims[:5]

        # Fetch analytical profiles (deduplicate by name)
        profiles_res = sb.table("signal_analytical_profiles").select("name, description, weights").execute()
        seen_names = set()
        analytical_paths = []
        for p in (profiles_res.data or []):
            if p["name"] not in seen_names:
                seen_names.add(p["name"])
                analytical_paths.append({"name": p["name"], "description": p.get("description", "")})

        coverage = "full" if len(mappings) == 1 else "partial"
        if len(claims) == 0:
            coverage = "partial"

        return JSONResponse(content={
            "cpt_code": cpt_code,
            "topic_slug": issue["slug"],
            "topic_title": issue["title"],
            "score": overall_score,
            "verdict": verdict,
            "key_claims": key_claims,
            "analytical_paths": analytical_paths,
            "coverage": coverage,
            "mapping_relevance": float(best.get("relevance_score", 0)),
            "mapping_notes": best.get("mapping_notes", ""),
            "all_mappings": [
                {"topic_slug": m["topic_slug"], "relevance_score": float(m.get("relevance_score", 0))}
                for m in mappings
            ],
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Endpoint 2: Denial Intelligence
# ---------------------------------------------------------------------------

@router.get("/denial-intelligence")
async def denial_intelligence(
    denial_code: str = Query(..., description="Denial reason code"),
    cpt_code: str = Query(..., description="CPT code that was denied"),
    icd10_code: str = Query(None, description="Optional ICD-10 diagnosis code"),
    payer: str = Query(None, description="Optional payer name"),
):
    """Find evidence to challenge a claim denial.

    Identifies the analytical path a payer likely followed to deny,
    then returns evidence that challenges that reasoning.
    """
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    try:
        # Find Signal topic for this CPT code
        mappings_res = (
            sb.table("signal_cpt_mappings")
            .select("*")
            .eq("cpt_code", cpt_code)
            .order("relevance_score", desc=True)
            .execute()
        )
        mappings = mappings_res.data or []

        if not mappings:
            return JSONResponse(content={
                "denial_code": denial_code,
                "cpt_code": cpt_code,
                "payer_analytical_path": None,
                "challenging_evidence": [],
                "recommended_claims": [],
                "appeal_strength": "weak",
                "message": f"No Signal evidence coverage for CPT {cpt_code}.",
            })

        topic_slug = mappings[0]["topic_slug"]

        # Fetch topic and claims
        issue_res = (
            sb.table("signal_issues")
            .select("id, slug, title")
            .eq("slug", topic_slug)
            .execute()
        )
        if not issue_res.data:
            return JSONResponse(content={
                "denial_code": denial_code,
                "cpt_code": cpt_code,
                "payer_analytical_path": None,
                "challenging_evidence": [],
                "recommended_claims": [],
                "appeal_strength": "weak",
                "message": f"Topic '{topic_slug}' not found.",
            })

        issue = issue_res.data[0]
        issue_id = issue["id"]

        payer_path = DENIAL_PATH_MAP.get(
            denial_code,
            f"Denial code {denial_code} suggests payer applied restrictive evidence weighting."
        )
        if payer:
            payer_path = f"{payer}: {payer_path}"

        # Fetch claims with scores — focus on strong consensus claims
        claims_res = (
            sb.table("signal_claims")
            .select("id, claim_text, category, claim_type, consensus_type")
            .eq("issue_id", issue_id)
            .execute()
        )
        claims = claims_res.data or []

        # Fetch composites
        claim_ids = [c["id"] for c in claims]
        composites = {}
        if claim_ids:
            chunk_size = 50
            for i in range(0, len(claim_ids), chunk_size):
                chunk = claim_ids[i:i + chunk_size]
                comp_res = (
                    sb.table("signal_claim_composites")
                    .select("claim_id, composite_score, evidence_category")
                    .in_("claim_id", chunk)
                    .execute()
                )
                for c in (comp_res.data or []):
                    composites[c["claim_id"]] = c

        # Challenging evidence: strong consensus claims with high scores
        challenging = []
        recommended = []
        for c in claims:
            comp = composites.get(c["id"])
            if not comp or not comp.get("composite_score"):
                continue
            score = float(comp["composite_score"])
            entry = {
                "claim_text": c["claim_text"],
                "claim_type": c.get("claim_type"),
                "consensus_type": c.get("consensus_type"),
                "composite_score": score,
                "evidence_category": comp.get("evidence_category"),
            }
            # Strong/moderate evidence with consensus = good for appeals
            if score >= 3.5 and c.get("consensus_type") == "strong_consensus":
                challenging.append(entry)
            # Efficacy claims are particularly useful for necessity appeals
            if c.get("claim_type") == "efficacy" and score >= 3.0:
                recommended.append(entry)

        challenging.sort(key=lambda x: x["composite_score"], reverse=True)
        recommended.sort(key=lambda x: x["composite_score"], reverse=True)

        # Appeal strength
        strong_count = len([e for e in challenging if e["composite_score"] >= 4.0])
        if strong_count >= 3:
            appeal_strength = "strong"
        elif len(challenging) >= 2:
            appeal_strength = "moderate"
        else:
            appeal_strength = "weak"

        return JSONResponse(content={
            "denial_code": denial_code,
            "cpt_code": cpt_code,
            "topic_slug": issue["slug"],
            "topic_title": issue["title"],
            "payer": payer,
            "payer_analytical_path": payer_path,
            "challenging_evidence": challenging[:10],
            "recommended_claims": recommended[:5],
            "appeal_strength": appeal_strength,
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Addition 1: Populate Denial Playbook
# ---------------------------------------------------------------------------

async def populate_denial_playbook() -> int:
    """Build signal_denial_playbook from CPT mappings × denial codes.

    For every (denial_code, cpt_code) combination where the CPT has a
    Signal topic mapping, fetches the top claims and upserts a playbook row.
    Returns the number of rows upserted.
    """
    sb = _get_sb()
    if not sb:
        raise RuntimeError("DB not available")

    # Fetch all CPT → topic mappings
    mappings_res = (
        sb.table("signal_cpt_mappings")
        .select("cpt_code, topic_slug")
        .order("relevance_score", desc=True)
        .execute()
    )
    mappings = mappings_res.data or []
    if not mappings:
        return 0

    # Resolve topic slugs → issue IDs
    slugs = list({m["topic_slug"] for m in mappings})
    issues_res = (
        sb.table("signal_issues")
        .select("id, slug")
        .in_("slug", slugs)
        .execute()
    )
    slug_to_issue = {i["slug"]: i["id"] for i in (issues_res.data or [])}

    # Pre-fetch top 5 claims per issue (by specificity DESC)
    issue_claims: dict[str, list] = {}
    for issue_id in slug_to_issue.values():
        claims_res = (
            sb.table("signal_claims")
            .select("claim_text, plain_summary, consensus_type, claim_type, specificity")
            .eq("issue_id", issue_id)
            .order("specificity", desc=True)
            .limit(5)
            .execute()
        )
        issue_claims[issue_id] = claims_res.data or []

    upserted = 0

    for mapping in mappings:
        cpt_code = mapping["cpt_code"]
        topic_slug = mapping["topic_slug"]
        issue_id = slug_to_issue.get(topic_slug)
        if not issue_id:
            continue

        claims = issue_claims.get(issue_id, [])

        # Build evidence summary from plain_summary fields
        summaries = [c["plain_summary"] for c in claims if c.get("plain_summary")]
        evidence_summary = ", ".join(summaries) if summaries else None

        # Build recommended_claims JSON array (top 3)
        recommended = [
            {
                "claim_text": c["claim_text"],
                "consensus_type": c.get("consensus_type"),
                "claim_type": c.get("claim_type"),
            }
            for c in claims[:3]
        ]

        # Determine appeal strength based on claim count
        if len(claims) >= 3:
            appeal_strength = "strong"
        elif len(claims) >= 1:
            appeal_strength = "moderate"
        else:
            appeal_strength = "weak"

        # Upsert one row per (denial_code, cpt_code) for each denial code
        for denial_code, payer_path in DENIAL_PATH_MAP.items():
            row = {
                "denial_code": denial_code,
                "cpt_code": cpt_code,
                "appeal_strength": appeal_strength,
                "payer_analytical_path": payer_path,
                "challenging_evidence_summary": evidence_summary,
                "recommended_claims": json.dumps(recommended),
                "signal_topic_slug": topic_slug,
                "signal_issue_id": issue_id,
            }
            sb.table("signal_denial_playbook").upsert(
                row, on_conflict="denial_code,cpt_code"
            ).execute()
            upserted += 1

    return upserted


# ---------------------------------------------------------------------------
# Addition 2: Admin endpoint to populate denial playbook
# ---------------------------------------------------------------------------

@router.post("/admin/populate-denial-playbook")
async def admin_populate_denial_playbook(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
):
    """Populate the signal_denial_playbook table. Requires admin auth via cron secret."""
    import os

    cron_secret = os.environ.get("CRON_SECRET")
    if not cron_secret or x_cron_secret != cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    count = await populate_denial_playbook()
    return {"populated": count}


@router.get("/admin/denial-patterns")
async def admin_denial_patterns(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
    limit: int = 50,
):
    """Return provider_denial_patterns ordered by occurrence_count DESC. Admin only."""
    import os

    cron_secret = os.environ.get("CRON_SECRET")
    if not cron_secret or x_cron_secret != cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    try:
        result = (
            sb.table("provider_denial_patterns")
            .select("*")
            .order("occurrence_count", desc=True)
            .limit(limit)
            .execute()
        )
        return {"patterns": result.data or [], "count": len(result.data or [])}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Addition 3: Aggregate denial patterns from provider 835 analyses
# ---------------------------------------------------------------------------

async def aggregate_denial_patterns(denied_lines: list, payer_name: str) -> None:
    """Upsert provider_denial_patterns from denied claim lines.

    Runs silently — catches all exceptions so it never disrupts the
    caller's flow.
    """
    try:
        sb = _get_sb()
        if not sb:
            return

        for line in denied_lines:
            cpt_code = line.get("cpt_code") or line.get("cpt", "")
            billed = float(line.get("billed_amount", 0) or 0)
            adj_codes = line.get("adjustment_codes", [])
            if isinstance(adj_codes, str):
                adj_codes = [adj_codes]

            for denial_code in adj_codes:
                if not denial_code:
                    continue

                # Check if playbook has coverage for this combo
                playbook_res = (
                    sb.table("signal_denial_playbook")
                    .select("id")
                    .eq("denial_code", denial_code)
                    .eq("cpt_code", cpt_code)
                    .limit(1)
                    .execute()
                )
                has_coverage = bool(playbook_res.data)

                # Try update first (existing row)
                existing = (
                    sb.table("provider_denial_patterns")
                    .select("id, occurrence_count, total_value_at_risk")
                    .eq("denial_code", denial_code)
                    .eq("cpt_code", cpt_code)
                    .eq("payer", payer_name)
                    .limit(1)
                    .execute()
                )

                if existing.data:
                    row = existing.data[0]
                    sb.table("provider_denial_patterns").update({
                        "occurrence_count": row["occurrence_count"] + 1,
                        "total_value_at_risk": float(row["total_value_at_risk"]) + billed,
                        "last_seen": "now()",
                        "signal_coverage": has_coverage,
                    }).eq("id", row["id"]).execute()
                else:
                    sb.table("provider_denial_patterns").insert({
                        "denial_code": denial_code,
                        "cpt_code": cpt_code,
                        "payer": payer_name,
                        "occurrence_count": 1,
                        "total_value_at_risk": billed,
                        "signal_coverage": has_coverage,
                    }).execute()

        # Check for patterns hitting thresholds → auto-create topic requests
        threshold_rows = (
            sb.table("provider_denial_patterns")
            .select("id, denial_code, cpt_code, payer, occurrence_count, total_value_at_risk")
            .eq("topic_request_created", False)
            .execute()
        )

        for row in (threshold_rows.data or []):
            count = row["occurrence_count"]
            value = float(row["total_value_at_risk"])
            if count < 5 and value < 10000:
                continue

            topic_name = f"Denial pattern: {row['denial_code']} on CPT {row['cpt_code']}"
            description = (
                f"Auto-generated from denial pattern aggregation. "
                f"Payer: {row['payer']}. "
                f"Occurrences: {count}. "
                f"Total value at risk: ${value:,.2f}. "
                f"Source: denial_pattern"
            )

            sb.table("signal_topic_requests").insert({
                "topic_name": topic_name,
                "description": description,
                "status": "pending",
            }).execute()

            sb.table("provider_denial_patterns").update({
                "topic_request_created": True,
            }).eq("id", row["id"]).execute()

    except Exception:
        logger.exception("aggregate_denial_patterns failed silently")
