"""Employer scorecard endpoint — AI-powered plan grading from SBC PDF upload.

POST /scorecard — accepts multipart PDF upload of a Summary of Benefits and Coverage.
Uses Claude AI to extract plan details and score against best-practice criteria.
"""

from __future__ import annotations

import base64
import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from routers.employer_shared import (
    _get_supabase, _call_claude, check_rate_limit,
)

router = APIRouter(tags=["employer"])


# ---------------------------------------------------------------------------
# SBC extraction prompt
# ---------------------------------------------------------------------------

SBC_EXTRACTION_PROMPT = """You are a health benefits analyst. You will receive a Summary of Benefits and Coverage (SBC) document. Extract the key plan design features.

Return ONLY valid JSON matching this exact structure:
{
  "plan_name": "extracted plan name",
  "network_type": "PPO" | "HMO" | "HDHP" | "EPO" | "POS" | "Other",
  "deductible_individual": 1500,
  "deductible_family": 3000,
  "oop_max_individual": 6000,
  "oop_max_family": 12000,
  "coinsurance_pct": 20,
  "primary_care_copay": 25,
  "specialist_copay": 50,
  "er_copay": 250,
  "urgent_care_copay": 75,
  "generic_rx_copay": 10,
  "preferred_rx_copay": 35,
  "specialty_rx_copay": 100,
  "mental_health_copay": 25,
  "preventive_covered": true,
  "hsa_eligible": false,
  "hra_included": false,
  "telehealth_copay": 0,
  "infertility_covered": false,
  "weight_management_covered": false,
  "notes": "any relevant observations about the plan"
}

Rules:
- Extract exact dollar amounts and percentages as shown in the document
- Use null for any field not found in the document
- deductible, oop_max, and copay values should be numbers (no $ signs)
- coinsurance_pct should be the member's share (e.g., 20 for 80/20 plan)
- If in-network and out-of-network values differ, use the in-network values"""


# ---------------------------------------------------------------------------
# Scoring criteria
# ---------------------------------------------------------------------------

SCORING_CRITERIA = [
    {
        "id": "deductible",
        "label": "Deductible",
        "weight": 15,
        "evaluate": lambda p: _score_range(p.get("deductible_individual"), 0, 1500, 3000, 7000),
    },
    {
        "id": "oop_max",
        "label": "Out-of-Pocket Maximum",
        "weight": 15,
        "evaluate": lambda p: _score_range(p.get("oop_max_individual"), 0, 4000, 7000, 9100),
    },
    {
        "id": "coinsurance",
        "label": "Coinsurance",
        "weight": 10,
        "evaluate": lambda p: _score_range_inverse(p.get("coinsurance_pct"), 0, 10, 20, 40),
    },
    {
        "id": "pcp_copay",
        "label": "Primary Care Copay",
        "weight": 10,
        "evaluate": lambda p: _score_range(p.get("primary_care_copay"), 0, 20, 40, 75),
    },
    {
        "id": "specialist_copay",
        "label": "Specialist Copay",
        "weight": 8,
        "evaluate": lambda p: _score_range(p.get("specialist_copay"), 0, 35, 65, 100),
    },
    {
        "id": "er_copay",
        "label": "ER Copay",
        "weight": 5,
        "evaluate": lambda p: _score_range(p.get("er_copay"), 0, 150, 300, 500),
    },
    {
        "id": "rx_generic",
        "label": "Generic Rx Copay",
        "weight": 8,
        "evaluate": lambda p: _score_range(p.get("generic_rx_copay"), 0, 10, 20, 40),
    },
    {
        "id": "rx_specialty",
        "label": "Specialty Rx Copay",
        "weight": 7,
        "evaluate": lambda p: _score_range(p.get("specialty_rx_copay"), 0, 50, 150, 300),
    },
    {
        "id": "mental_health",
        "label": "Mental Health Access",
        "weight": 7,
        "evaluate": lambda p: _score_range(p.get("mental_health_copay"), 0, 20, 40, 75),
    },
    {
        "id": "telehealth",
        "label": "Telehealth Access",
        "weight": 5,
        "evaluate": lambda p: 100 if p.get("telehealth_copay") == 0 else (
            75 if (p.get("telehealth_copay") or 999) <= 25 else 50
        ),
    },
    {
        "id": "preventive",
        "label": "Preventive Care",
        "weight": 5,
        "evaluate": lambda p: 100 if p.get("preventive_covered") else 40,
    },
    {
        "id": "hsa_eligible",
        "label": "HSA/HRA Availability",
        "weight": 5,
        "evaluate": lambda p: 100 if p.get("hsa_eligible") or p.get("hra_included") else 50,
    },
]


# ---------------------------------------------------------------------------
# POST /scorecard
# ---------------------------------------------------------------------------

@router.post("/scorecard")
async def employer_scorecard(
    request: Request,
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
    plan_name: Optional[str] = Form(None),
    network_type: Optional[str] = Form(None),
):
    """Parse an SBC PDF and return a scored plan grading."""
    check_rate_limit(request, max_requests=20)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Encode PDF for Claude vision
    b64_content = base64.b64encode(content).decode("utf-8")

    # Call Claude to extract plan details from PDF
    parsed = _call_claude(
        system_prompt=SBC_EXTRACTION_PROMPT,
        user_content=[
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64_content,
                },
            },
            {
                "type": "text",
                "text": "Please extract the plan details from this Summary of Benefits and Coverage document.",
            },
        ],
        max_tokens=2048,
    )

    if not parsed:
        raise HTTPException(status_code=422, detail="Could not parse the SBC document. Please try a clearer PDF.")

    # Override with user-provided values if present
    if plan_name:
        parsed["plan_name"] = plan_name
    if network_type:
        parsed["network_type"] = network_type

    # --- Score the plan ---
    scored_criteria = []
    total_weighted_score = 0.0
    total_weight = 0

    for criterion in SCORING_CRITERIA:
        try:
            score = criterion["evaluate"](parsed)
        except Exception:
            score = 50  # neutral default if evaluation fails

        if score is None:
            score = 50

        weighted = score * criterion["weight"] / 100
        total_weighted_score += weighted
        total_weight += criterion["weight"]

        scored_criteria.append({
            "id": criterion["id"],
            "label": criterion["label"],
            "weight": criterion["weight"],
            "score": round(score, 1),
            "weighted_score": round(weighted, 2),
        })

    overall_score = round((total_weighted_score / total_weight) * 100, 1) if total_weight > 0 else 50.0
    grade = _score_to_grade(overall_score)

    # --- Savings estimate ---
    savings_per_ee = _estimate_savings(parsed, overall_score)

    result = {
        "plan_name": parsed.get("plan_name", plan_name or "Unknown Plan"),
        "network_type": parsed.get("network_type", network_type or "Unknown"),
        "grade": grade,
        "score": overall_score,
        "savings_estimate_per_ee": savings_per_ee,
        "parsed_plan": parsed,
        "scored_criteria": scored_criteria,
    }

    # --- Persist to Supabase ---
    try:
        sb = _get_supabase()
        sb.table("employer_scorecard_sessions").insert({
            "email": email,
            "plan_name": result["plan_name"],
            "network_type": result["network_type"],
            "grade": grade,
            "score": float(overall_score),
            "savings_estimate_per_ee": float(savings_per_ee) if savings_per_ee else None,
            "parsed_plan_json": parsed,
            "scored_criteria_json": scored_criteria,
        }).execute()
    except Exception as exc:
        print(f"[Employer Scorecard] Failed to save session: {exc}")

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_range(value, best, good, fair, poor) -> float:
    """Score a value where lower is better (deductibles, copays)."""
    if value is None:
        return None
    value = float(value)
    if value <= best:
        return 100
    elif value <= good:
        return 100 - 25 * ((value - best) / (good - best)) if (good - best) > 0 else 87.5
    elif value <= fair:
        return 75 - 25 * ((value - good) / (fair - good)) if (fair - good) > 0 else 62.5
    elif value <= poor:
        return 50 - 25 * ((value - fair) / (poor - fair)) if (poor - fair) > 0 else 37.5
    else:
        return max(10, 25 - 25 * ((value - poor) / poor)) if poor > 0 else 10


def _score_range_inverse(value, best, good, fair, poor) -> float:
    """Score where lower is better (coinsurance percentage)."""
    return _score_range(value, best, good, fair, poor)


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C+"
    elif score >= 50:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def _estimate_savings(parsed: dict, score: float) -> Optional[float]:
    """Estimate annual per-employee savings potential based on plan inefficiencies."""
    if score >= 85:
        return 0  # already well-optimized

    # Rough heuristic: each 10 points below 85 = ~$200/yr savings opportunity
    gap = 85 - score
    base_savings = (gap / 10) * 200

    # Adjust for specific high-cost indicators
    deductible = parsed.get("deductible_individual")
    if deductible and deductible < 500:
        base_savings += 300  # low deductible = premium drag

    oop = parsed.get("oop_max_individual")
    if oop and oop > 8000:
        base_savings += 150  # high OOP may indicate poor network negotiation

    specialty_rx = parsed.get("specialty_rx_copay")
    if specialty_rx and specialty_rx > 200:
        base_savings += 250  # specialty Rx cost containment opportunity

    return round(base_savings, 0)
