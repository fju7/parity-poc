"""Parity Signal Intelligence API.

Connects Signal evidence to billing products via CPT code mappings.
Provides evidence lookups and denial intelligence for appeal support.
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/signal", tags=["signal-intelligence"])

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

        # Generate verdict
        if overall_score and overall_score >= 4.0:
            verdict = f"Strong evidence base for treatments related to CPT {cpt_code}."
        elif overall_score and overall_score >= 3.0:
            verdict = f"Moderate evidence base for treatments related to CPT {cpt_code}."
        elif overall_score and overall_score >= 2.0:
            verdict = f"Mixed evidence for treatments related to CPT {cpt_code}. Review analytical paths."
        elif overall_score:
            verdict = f"Weak evidence base for CPT {cpt_code}."
        else:
            verdict = f"Evidence available but not yet scored for CPT {cpt_code}."

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

        # Fetch analytical profiles
        profiles_res = sb.table("signal_analytical_profiles").select("name, description, weights").execute()
        analytical_paths = [
            {"name": p["name"], "description": p.get("description", "")}
            for p in (profiles_res.data or [])
        ]

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

        # Map denial codes to likely payer analytical paths
        denial_path_map = {
            # Medical necessity denials
            "CO-50": "Payer likely weighted recency and rigor heavily, discounting older but well-replicated evidence.",
            "CO-97": "Payer applied narrow interpretation of medical necessity, likely underweighting consensus evidence.",
            "PR-204": "Payer required specific authorization criteria not met — check if evidence supports broader coverage.",
            # Not covered denials
            "CO-4": "Service not covered under benefit plan — evidence may support medical necessity override.",
            "CO-11": "Diagnosis inconsistent with procedure — evidence may demonstrate clinical pathway.",
            # Experimental/investigational
            "CO-56": "Payer classified service as experimental — evidence strength directly challenges this.",
            "CO-181": "Procedure code inconsistent with modifier — possible coding issue rather than evidence gap.",
        }

        payer_path = denial_path_map.get(
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
