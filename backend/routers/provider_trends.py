"""Provider trend detection engine — monthly analysis, alerts, AI narrative."""

from __future__ import annotations

import json
from collections import Counter

from routers.provider_shared import (
    _get_supabase, _call_claude_text,
)


def _aggregate_cpt_flags(line_items: list) -> dict:
    """Group line items by CPT, return {cpt: {flag, avg_variance, count, total_paid, total_expected}}."""
    cpt_data = {}
    for li in line_items:
        cpt = li.get("cpt_code", "")
        if not cpt:
            continue
        if cpt not in cpt_data:
            cpt_data[cpt] = {"flags": [], "variances": [], "paid": [], "expected": [], "count": 0}
        cpt_data[cpt]["flags"].append(li.get("flag", ""))
        if li.get("variance") is not None:
            cpt_data[cpt]["variances"].append(li["variance"])
        cpt_data[cpt]["paid"].append(li.get("paid_amount", 0))
        cpt_data[cpt]["expected"].append(li.get("expected_payment") or 0)
        cpt_data[cpt]["count"] += 1

    result = {}
    for cpt, d in cpt_data.items():
        # Predominant flag = most common
        flag_counts = Counter(d["flags"])
        predominant_flag = flag_counts.most_common(1)[0][0] if flag_counts else "UNKNOWN"
        avg_variance = round(sum(d["variances"]) / len(d["variances"]), 2) if d["variances"] else 0
        result[cpt] = {
            "flag": predominant_flag,
            "avg_variance": avg_variance,
            "count": d["count"],
            "total_paid": round(sum(d["paid"]), 2),
            "total_expected": round(sum(d["expected"]), 2),
        }
    return result


def _extract_denial_codes(denial_intel: dict) -> set:
    """Extract adjustment/reason codes from denial intelligence result."""
    codes = set()
    if not denial_intel:
        return codes
    for dt in denial_intel.get("denial_types", []):
        rc = dt.get("reason_code", "")
        if rc:
            codes.add(rc)
    for dl in denial_intel.get("denied_lines", []):
        adj = dl.get("adjustment_codes", "")
        if adj:
            for part in adj.split(","):
                codes.add(part.strip())
    return codes


def _compute_trends(subscription_id: str, sb=None) -> dict:
    """Compute month-over-month trends for a subscription.

    Returns: {monthly_summary, per_payer_trends, alerts}
    """
    if sb is None:
        sb = _get_supabase()

    sub_result = sb.table("provider_subscriptions").select("*").eq("id", subscription_id).execute()
    if not sub_result.data:
        return {"monthly_summary": [], "per_payer_trends": [], "alerts": []}

    sub = sub_result.data[0]
    monthly_analyses = sub.get("monthly_analyses", []) or []

    if not monthly_analyses:
        return {"monthly_summary": [], "per_payer_trends": [], "alerts": []}

    # Fetch all analysis records for all months
    month_data = []  # [{month, label, analyses: [{payer_name, summary, line_items, denial_intel}]}]
    for ma in monthly_analyses:
        aids = ma.get("analysis_ids", []) or []
        analyses = []
        for aid in aids:
            try:
                row = sb.table("provider_analyses").select("*").eq("id", aid).execute()
                if row.data:
                    rec = row.data[0]
                    rj = rec.get("result_json", {})
                    analyses.append({
                        "payer_name": rec.get("payer_name", ""),
                        "summary": rj.get("summary", {}),
                        "line_items": rj.get("line_items", []),
                        "denial_intel": rj.get("denial_intel"),
                        "scorecard": rj.get("scorecard", {}),
                    })
            except Exception:
                pass
        month_data.append({
            "month": ma.get("month", ""),
            "label": ma.get("label", ""),
            "analyses": analyses,
        })

    # Build monthly_summary: per-month, per-payer totals
    monthly_summary = []
    for md in month_data:
        payers = []
        for a in md["analyses"]:
            s = a["summary"]
            sc = a.get("scorecard", {})
            payers.append({
                "payer_name": a["payer_name"],
                "total_contracted": s.get("total_contracted", 0),
                "total_paid": s.get("total_paid", 0),
                "total_underpayment": s.get("total_underpayment", 0),
                "adherence_rate": s.get("adherence_rate", 0),
                "denial_rate": sc.get("denial_rate", 0),
                "line_count": s.get("line_count", 0),
                "underpaid_count": s.get("underpaid_count", 0),
                "denied_count": s.get("denied_count", 0),
                "correct_count": s.get("correct_count", 0),
            })
        monthly_summary.append({
            "month": md["month"],
            "label": md["label"],
            "payers": payers,
        })

    # Build per_payer_trends: per-payer, per-CPT across months
    all_payers = set()
    for md in month_data:
        for a in md["analyses"]:
            all_payers.add(a["payer_name"])

    per_payer_trends = []
    for payer in sorted(all_payers):
        payer_months = []
        payer_cpt_by_month = []  # [{month, cpt_flags: {cpt: {flag, avg_variance, ...}}}]

        for md in month_data:
            payer_analysis = None
            for a in md["analyses"]:
                if a["payer_name"] == payer:
                    payer_analysis = a
                    break
            if not payer_analysis:
                continue

            s = payer_analysis["summary"]
            sc = payer_analysis.get("scorecard", {})
            payer_months.append({
                "month": md["month"],
                "total_underpayment": s.get("total_underpayment", 0),
                "adherence_rate": s.get("adherence_rate", 0),
                "denial_rate": sc.get("denial_rate", 0),
                "total_contracted": s.get("total_contracted", 0),
                "total_paid": s.get("total_paid", 0),
                "line_count": s.get("line_count", 0),
            })

            cpt_flags = _aggregate_cpt_flags(payer_analysis.get("line_items", []))
            payer_cpt_by_month.append({
                "month": md["month"],
                "cpt_flags": cpt_flags,
                "denial_codes": _extract_denial_codes(payer_analysis.get("denial_intel")),
            })

        # Build CPT trends
        all_cpts = set()
        for pcm in payer_cpt_by_month:
            all_cpts.update(pcm["cpt_flags"].keys())

        cpt_trends = []
        for cpt in sorted(all_cpts):
            cpt_month_data = []
            for pcm in payer_cpt_by_month:
                cf = pcm["cpt_flags"].get(cpt)
                if cf:
                    cpt_month_data.append({
                        "month": pcm["month"],
                        "paid_amount": cf["total_paid"],
                        "expected_amount": cf["total_expected"],
                        "variance": cf["avg_variance"],
                        "flag": cf["flag"],
                        "count": cf["count"],
                    })
            if cpt_month_data:
                cpt_trends.append({"cpt_code": cpt, "months": cpt_month_data})

        per_payer_trends.append({
            "payer_name": payer,
            "months": payer_months,
            "cpt_trends": cpt_trends,
        })

    # Generate alerts by comparing last two months
    alerts = []
    if len(month_data) >= 2:
        prev_md = month_data[-2]
        curr_md = month_data[-1]

        for payer in all_payers:
            prev_analysis = next((a for a in prev_md["analyses"] if a["payer_name"] == payer), None)
            curr_analysis = next((a for a in curr_md["analyses"] if a["payer_name"] == payer), None)

            if not prev_analysis or not curr_analysis:
                continue

            prev_cpt = _aggregate_cpt_flags(prev_analysis.get("line_items", []))
            curr_cpt = _aggregate_cpt_flags(curr_analysis.get("line_items", []))

            # New underpayment: CPT was CORRECT last month, UNDERPAID this month
            for cpt, curr_info in curr_cpt.items():
                prev_info = prev_cpt.get(cpt)
                if curr_info["flag"] == "UNDERPAID":
                    if prev_info and prev_info["flag"] == "CORRECT":
                        alerts.append({
                            "type": "new_underpayment",
                            "severity": "high",
                            "payer_name": payer,
                            "cpt_code": cpt,
                            "detail": f"CPT {cpt} was correctly paid last month but is now underpaid (avg variance: ${curr_info['avg_variance']:+.2f})",
                            "financial_impact": round(abs(curr_info["avg_variance"]) * curr_info["count"], 2),
                            "month": curr_md["month"],
                        })
                    elif prev_info and prev_info["flag"] == "UNDERPAID":
                        # Worsening underpayment
                        if curr_info["avg_variance"] < prev_info["avg_variance"] - 0.50:
                            alerts.append({
                                "type": "worsening_underpayment",
                                "severity": "high",
                                "payer_name": payer,
                                "cpt_code": cpt,
                                "detail": f"CPT {cpt} underpayment worsened from ${prev_info['avg_variance']:+.2f} to ${curr_info['avg_variance']:+.2f}",
                                "financial_impact": round(abs(curr_info["avg_variance"] - prev_info["avg_variance"]) * curr_info["count"], 2),
                                "month": curr_md["month"],
                            })

            # Resolved underpayment: was UNDERPAID, now CORRECT
            for cpt, prev_info in prev_cpt.items():
                curr_info = curr_cpt.get(cpt)
                if prev_info["flag"] == "UNDERPAID" and curr_info and curr_info["flag"] == "CORRECT":
                    alerts.append({
                        "type": "resolved_underpayment",
                        "severity": "positive",
                        "payer_name": payer,
                        "cpt_code": cpt,
                        "detail": f"CPT {cpt} underpayment has been resolved — now paying at contracted rate",
                        "financial_impact": round(abs(prev_info["avg_variance"]) * prev_info["count"], 2),
                        "month": curr_md["month"],
                    })

            # Denial code changes
            prev_denial_codes = _extract_denial_codes(prev_analysis.get("denial_intel"))
            curr_denial_codes = _extract_denial_codes(curr_analysis.get("denial_intel"))
            new_denial_codes = curr_denial_codes - prev_denial_codes
            for code in new_denial_codes:
                alerts.append({
                    "type": "new_denial_pattern",
                    "severity": "medium",
                    "payer_name": payer,
                    "cpt_code": None,
                    "detail": f"New denial reason code {code} appeared this month for {payer}",
                    "financial_impact": None,
                    "month": curr_md["month"],
                })

            # Denial rate change (>=2 percentage points)
            prev_sc = prev_analysis.get("scorecard", {})
            curr_sc = curr_analysis.get("scorecard", {})
            prev_dr = prev_sc.get("denial_rate", 0)
            curr_dr = curr_sc.get("denial_rate", 0)
            if abs(curr_dr - prev_dr) >= 2.0:
                severity = "high" if curr_dr > prev_dr else "positive"
                direction = "increased" if curr_dr > prev_dr else "decreased"
                alerts.append({
                    "type": "denial_rate_change",
                    "severity": severity,
                    "payer_name": payer,
                    "cpt_code": None,
                    "detail": f"{payer} denial rate {direction} from {prev_dr}% to {curr_dr}%",
                    "financial_impact": None,
                    "month": curr_md["month"],
                })

        # Revenue gap trajectory (cumulative across all months and payers)
        cumulative_underpayment = 0
        months_count = len(month_data)
        for md in month_data:
            for a in md["analyses"]:
                cumulative_underpayment += a["summary"].get("total_underpayment", 0)

        if cumulative_underpayment > 0 and months_count > 0:
            monthly_avg = cumulative_underpayment / months_count
            projected_annual = round(monthly_avg * 12, 2)
            severity = "high" if projected_annual > 10000 else "medium"
            alerts.append({
                "type": "revenue_gap_trajectory",
                "severity": severity,
                "payer_name": None,
                "cpt_code": None,
                "detail": f"Cumulative underpayment of ${cumulative_underpayment:,.2f} over {months_count} month(s). Projected annual revenue gap: ${projected_annual:,.2f}",
                "financial_impact": projected_annual,
                "month": curr_md["month"] if len(month_data) >= 2 else month_data[-1]["month"],
            })

    return {
        "monthly_summary": monthly_summary,
        "per_payer_trends": per_payer_trends,
        "alerts": alerts,
    }


def _generate_trend_narrative(sub: dict, monthly_summary: list, alerts: list) -> str:
    """Generate AI narrative summarizing month-over-month trends."""
    months_count = len(monthly_summary)
    if months_count < 2:
        return ""

    # Build context for Claude
    high_alerts = [a for a in alerts if a.get("severity") == "high"]
    positive_alerts = [a for a in alerts if a.get("severity") == "positive"]
    medium_alerts = [a for a in alerts if a.get("severity") == "medium"]

    # Calculate total underpayment trend
    month_totals = []
    for ms in monthly_summary:
        total_underpayment = sum(p.get("total_underpayment", 0) for p in ms.get("payers", []))
        month_totals.append({"month": ms.get("month"), "label": ms.get("label"), "total_underpayment": total_underpayment})

    practice_name = sub.get("practice_name", "the practice")

    prompt_data = json.dumps({
        "practice_name": practice_name,
        "months_analyzed": months_count,
        "month_totals": month_totals,
        "high_severity_alerts": [a["detail"] for a in high_alerts[:5]],
        "positive_alerts": [a["detail"] for a in positive_alerts[:3]],
        "medium_alerts": [a["detail"] for a in medium_alerts[:3]],
        "latest_month": monthly_summary[-1] if monthly_summary else {},
    }, default=str)

    system_prompt = (
        "You are a medical billing analytics expert writing a trend summary for a healthcare practice. "
        "Write a 3-5 sentence professional narrative paragraph. "
        "Open with the biggest financial impact finding. "
        "Highlight worsening patterns that need immediate action. "
        "Acknowledge any resolved issues. "
        "Close with the projected annual impact. "
        f"{'Note that this is based on only ' + str(months_count) + ' months of data (preliminary trends). ' if months_count <= 2 else ''}"
        "Use specific dollar amounts and percentages. Be direct and actionable. Do not use markdown formatting."
    )

    narrative = _call_claude_text(
        system_prompt=system_prompt,
        user_content=prompt_data,
        max_tokens=512,
    )

    return narrative or ""


def _compute_and_cache_trends(subscription_id: str, sb=None) -> dict:
    """Compute trends and cache the AI narrative on the subscription."""
    if sb is None:
        sb = _get_supabase()
    from datetime import datetime

    trends = _compute_trends(subscription_id, sb=sb)

    # Fetch subscription for narrative generation
    sub_result = sb.table("provider_subscriptions").select("*").eq("id", subscription_id).execute()
    if not sub_result.data:
        return trends

    sub = sub_result.data[0]

    narrative = _generate_trend_narrative(sub, trends["monthly_summary"], trends["alerts"])

    if narrative:
        sb.table("provider_subscriptions").update({
            "trend_narrative": narrative,
            "trend_narrative_updated_at": datetime.utcnow().isoformat(),
        }).eq("id", subscription_id).execute()

    trends["trend_narrative"] = narrative
    return trends
