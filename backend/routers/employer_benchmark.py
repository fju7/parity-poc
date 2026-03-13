"""Employer benchmark endpoint — PEPM comparison against compiled benchmarks.

POST /benchmark — accepts industry, company_size, state, pepm_input.
Returns percentile ranking, dollar gap, and contextual benchmarks.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from routers.employer_shared import (
    _get_supabase, get_benchmarks, _call_claude,
    BenchmarkRequest, check_rate_limit,
)
from data.employer_benchmarks.industry_mapping import resolve_industry

router = APIRouter(tags=["employer"])


# ---------------------------------------------------------------------------
# POST /benchmark
# ---------------------------------------------------------------------------

@router.post("/benchmark")
async def employer_benchmark(req: BenchmarkRequest, request: Request):
    """Compare employer PEPM against industry/size benchmarks."""
    check_rate_limit(request, max_requests=30)
    benchmarks = get_benchmarks()
    if not benchmarks:
        raise HTTPException(status_code=503, detail="Benchmark data not loaded")

    national = benchmarks.get("national_averages", {})
    by_industry = benchmarks.get("by_industry", {})
    by_size = benchmarks.get("by_company_size", {})
    by_state = benchmarks.get("by_state", {})

    # --- Industry lookup (map display name → MEPS key) ---
    meps_industry = resolve_industry(req.industry)
    industry_data = by_industry.get(meps_industry, {})
    industry_median = industry_data.get("employer_single_pepm") or national.get("employer_single_monthly_pepm", 558)

    # --- Size band lookup ---
    size_data = by_size.get(req.company_size, {})
    size_median = size_data.get("employer_single_pepm") or industry_median

    # --- State lookup ---
    state_data = by_state.get(req.state, {})
    state_factor = state_data.get("cost_index", 1.0)

    # Use industry + size median adjusted by state factor as the primary benchmark
    adjusted_median = round(industry_median * state_factor, 2)

    # --- Percentile estimation ---
    # Prefer industry-specific percentiles; fall back to national
    has_industry_pctiles = bool(industry_data.get("p10_pepm"))
    if has_industry_pctiles:
        p10 = industry_data["p10_pepm"]
        p25 = industry_data["p25_pepm"]
        p50 = industry_data["p50_pepm"]
        p75 = industry_data["p75_pepm"]
        p90 = industry_data["p90_pepm"]
        percentile_source = "industry"
    else:
        p10 = national.get("p10_pepm", 342)
        p25 = national.get("p25_pepm", 441)
        p50 = national.get("p50_pepm", 552)
        p75 = national.get("p75_pepm", 658)
        p90 = national.get("p90_pepm", 789)
        percentile_source = "national"

    # Scale percentiles by state factor
    p10 *= state_factor
    p25 *= state_factor
    p50 *= state_factor
    p75 *= state_factor
    p90 *= state_factor

    pepm = req.pepm_input
    percentile = _estimate_percentile(pepm, p10, p25, p50, p75, p90)

    # --- Dollar gap ---
    dollar_gap_monthly = round(pepm - adjusted_median, 2)
    dollar_gap_annual = round(dollar_gap_monthly * 12, 2)

    # --- Build result ---
    result = {
        "input": {
            "industry": req.industry,
            "company_size": req.company_size,
            "state": req.state,
            "pepm_input": pepm,
        },
        "benchmarks": {
            "national_median_pepm": round(p50, 2),
            "industry_median_pepm": round(industry_median, 2),
            "adjusted_median_pepm": adjusted_median,
            "size_band_median_pepm": round(size_median, 2),
            "state_cost_index": state_factor,
        },
        "result": {
            "percentile": round(percentile, 1),
            "dollar_gap_monthly": dollar_gap_monthly,
            "dollar_gap_annual": dollar_gap_annual,
            "interpretation": _interpret_percentile(percentile),
            "percentile_source": percentile_source,
        },
        "distribution": {
            "p10": round(p10, 2),
            "p25": round(p25, 2),
            "p50": round(p50, 2),
            "p75": round(p75, 2),
            "p90": round(p90, 2),
        },
    }

    # --- AI narrative + talking points ---
    narrative = None
    talking_points = None
    try:
        bench_prompt = (
            f"Industry: {req.industry}. State: {req.state}. Company size: {req.company_size}.\n"
            f"PEPM: ${pepm}. Adjusted median: ${adjusted_median}. Percentile: {round(percentile, 1)}.\n"
            f"Annual gap per employee: ${round(dollar_gap_annual, 2)}.\n"
            f"State cost index: {state_factor}.\n\n"
            "Write a JSON object with two keys:\n"
            '1. "narrative": A 2-3 paragraph executive summary for an HR director or CFO. '
            "Open with the specific finding (PEPM, percentile, annual dollar gap). "
            "Explain what typically drives costs at this percentile for this specific industry and state. "
            'Close with: "This benchmark is a starting point — the data shows where to focus, not a verdict on your plan." '
            "Tone: calm, authoritative, factual. Like a trusted advisor.\n"
            '2. "talking_points": An array of exactly 3 strings. Each is a specific renewal question the employer can ask verbatim. '
            "Format each as: 'Ask your broker: \"[exact question]\"' or 'Ask your carrier: \"[exact question]\"'. "
            f"Tailor to their percentile ({round(percentile,1)}): "
            "above 75th = aggressive negotiation; 50-75th = monitoring/benchmark questions; below 50th = affirmation + watch items. "
            "1-2 sentences each.\n\n"
            "Return ONLY valid JSON. No markdown, no preamble."
        )
        ai_result = _call_claude(
            system_prompt="You are a senior benefits consultant writing for HR directors. Return valid JSON only.",
            user_content=bench_prompt,
            max_tokens=1200,
        )
        if ai_result:
            narrative = ai_result.get("narrative")
            tp = ai_result.get("talking_points")
            if isinstance(tp, list) and len(tp) >= 1:
                talking_points = tp[:3]
    except Exception as exc:
        print(f"[Employer Benchmark] AI narrative non-fatal: {exc}")

    result["narrative"] = narrative
    result["talking_points"] = talking_points

    # --- Persist to Supabase ---
    try:
        sb = _get_supabase()
        sb.table("employer_benchmark_sessions").insert({
            "email": req.email,
            "industry": req.industry,
            "company_size": req.company_size,
            "state": req.state,
            "pepm_input": float(pepm),
            "pepm_median": float(adjusted_median),
            "percentile": float(percentile),
            "dollar_gap_annual": float(dollar_gap_annual),
            "result_json": result,
        }).execute()
    except Exception as exc:
        print(f"[Employer Benchmark] Failed to save session: {exc}")

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_percentile(
    value: float, p10: float, p25: float, p50: float, p75: float, p90: float,
) -> float:
    """Estimate percentile via linear interpolation between known percentile points."""
    if value <= p10:
        return max(1.0, 10.0 * (value / p10)) if p10 > 0 else 5.0
    elif value <= p25:
        return 10.0 + 15.0 * ((value - p10) / (p25 - p10)) if (p25 - p10) > 0 else 17.5
    elif value <= p50:
        return 25.0 + 25.0 * ((value - p25) / (p50 - p25)) if (p50 - p25) > 0 else 37.5
    elif value <= p75:
        return 50.0 + 25.0 * ((value - p50) / (p75 - p50)) if (p75 - p50) > 0 else 62.5
    elif value <= p90:
        return 75.0 + 15.0 * ((value - p75) / (p90 - p75)) if (p90 - p75) > 0 else 82.5
    else:
        return min(99.0, 90.0 + 10.0 * ((value - p90) / (p90 * 0.3))) if p90 > 0 else 95.0


def _interpret_percentile(pct: float) -> str:
    """Human-readable interpretation of percentile ranking."""
    if pct <= 25:
        return "Well below average — your costs are lower than most employers in your segment."
    elif pct <= 40:
        return "Below average — you are spending less than the typical employer."
    elif pct <= 60:
        return "Near average — your costs are in line with similar employers."
    elif pct <= 75:
        return "Above average — you are spending more than the typical employer."
    else:
        return "Well above average — your costs significantly exceed most employers. A plan audit may identify savings."
