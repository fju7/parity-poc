"""Parity Signal — Analytical Profiles endpoints.

GET  /api/signal/profiles           — list all analytical profiles
POST /api/signal/profiles/score     — re-score claims using a named profile's weights
"""

import time
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/signal", tags=["signal"])

_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


# Cache profiles in memory — they rarely change
_profiles_cache = {"data": None, "expires": 0}
CACHE_TTL = 600  # 10 minutes

DEFAULT_WEIGHTS = {
    "source_quality": 0.25,
    "data_support": 0.20,
    "reproducibility": 0.20,
    "consensus": 0.15,
    "recency": 0.10,
    "rigor": 0.10,
}


def _evidence_category(score: float) -> str:
    if score >= 4.0:
        return "strong"
    if score >= 3.0:
        return "moderate"
    if score >= 2.0:
        return "mixed"
    return "weak"


def _compute_composite(dim_scores: dict, weights: dict) -> float | None:
    """Weighted average of dimension scores using given weights."""
    weighted_sum = 0.0
    total_weight = 0.0
    for dim, weight in weights.items():
        score = dim_scores.get(dim)
        if score is not None:
            weighted_sum += score * weight
            total_weight += weight
    return round(weighted_sum / total_weight, 2) if total_weight > 0 else None


@router.get("/profiles")
async def list_profiles():
    """Return all analytical profiles."""
    now = time.time()
    if _profiles_cache["data"] and now < _profiles_cache["expires"]:
        return JSONResponse(content=_profiles_cache["data"])

    sb = _get_sb()
    if not sb:
        return JSONResponse(content=[])

    try:
        res = sb.table("signal_analytical_profiles").select("*").order("is_default", desc=True).order("name").execute()
        profiles = res.data or []
        _profiles_cache["data"] = profiles
        _profiles_cache["expires"] = now + CACHE_TTL
        return JSONResponse(content=profiles)
    except Exception:
        return JSONResponse(content=[])


@router.post("/profiles/score")
async def score_with_profile(
    profile_id: str = Query(..., description="UUID of the analytical profile"),
    issue_id: str = Query(..., description="UUID of the issue to re-score"),
):
    """Re-score all claims for an issue using a named profile's weights.

    Returns per-claim composite scores, evidence categories, and divergence
    from the default (Balanced) scoring.
    """
    sb = _get_sb()
    if not sb:
        raise HTTPException(status_code=500, detail="Database unavailable")

    # Fetch profile
    profile_res = sb.table("signal_analytical_profiles").select("*").eq("id", profile_id).execute()
    if not profile_res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profile_res.data[0]
    profile_weights = profile["weights"]

    # Fetch all claims for this issue
    claims_res = sb.table("signal_claims").select("id, claim_text, category").eq("issue_id", issue_id).execute()
    claims = claims_res.data or []
    if not claims:
        return JSONResponse(content={"profile": profile, "scores": [], "divergences": []})

    claim_ids = [c["id"] for c in claims]

    # Fetch dimension scores for all claims
    scores_res = sb.table("signal_claim_scores").select("claim_id, dimension, score").in_("claim_id", claim_ids).execute()
    dim_scores_map: dict[str, dict] = {}
    for row in (scores_res.data or []):
        if row["claim_id"] not in dim_scores_map:
            dim_scores_map[row["claim_id"]] = {}
        dim_scores_map[row["claim_id"]][row["dimension"]] = row["score"]

    # Fetch existing default composites for divergence comparison
    composites_res = sb.table("signal_claim_composites").select(
        "claim_id, composite_score, evidence_category"
    ).in_("claim_id", claim_ids).execute()
    default_composites = {r["claim_id"]: r for r in (composites_res.data or [])}

    # Compute new scores with profile weights
    scored_claims = []
    divergences = []

    for claim in claims:
        cid = claim["id"]
        dims = dim_scores_map.get(cid, {})

        profile_score = _compute_composite(dims, profile_weights)
        profile_category = _evidence_category(profile_score) if profile_score is not None else None

        default = default_composites.get(cid)
        default_score = float(default["composite_score"]) if default and default["composite_score"] is not None else None
        default_category = default["evidence_category"] if default else None

        scored_claims.append({
            "claim_id": cid,
            "claim_text": claim["claim_text"],
            "category": claim["category"],
            "profile_score": profile_score,
            "profile_category": profile_category,
            "default_score": default_score,
            "default_category": default_category,
        })

        # Flag divergence where evidence category differs
        if profile_category and default_category and profile_category != default_category:
            divergences.append({
                "claim_id": cid,
                "claim_text": claim["claim_text"],
                "category": claim["category"],
                "default_category": default_category,
                "profile_category": profile_category,
                "default_score": default_score,
                "profile_score": profile_score,
                "direction": "stronger" if _cat_rank(profile_category) > _cat_rank(default_category) else "weaker",
            })

    return JSONResponse(content={
        "profile": profile,
        "scores": scored_claims,
        "divergences": divergences,
    })


def _cat_rank(category: str) -> int:
    """Numeric rank for evidence categories (higher = stronger)."""
    return {"strong": 4, "moderate": 3, "mixed": 2, "weak": 1}.get(category, 0)
