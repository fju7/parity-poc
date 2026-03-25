"""
Pre-submission risk scoring engine for 837P claims.

Applies rule-based checks to each service line and returns
risk flags with severity levels.
"""

from __future__ import annotations

from typing import List


# Bilateral procedure codes that typically require LT/RT/50 modifiers
BILATERAL_CODES = {"27447", "27130", "27486", "69210", "67028"}
BILATERAL_MODIFIERS = {"50", "LT", "RT"}

# Modifier 59 conflicts with X{EPSU} modifiers (CMS replaced 59 with X-mods)
MODIFIER_59_CONFLICTS = {"XE", "XS", "XP", "XU"}


def score_claims(parsed_837: dict) -> dict:
    """Score parsed 837P claims for pre-submission risk.

    Args:
        parsed_837: Output from parse_837().

    Returns:
        Dict with risk_flags (list) and summary.
    """
    risk_flags: List[dict] = []
    total_lines = 0
    total_billed = 0.0

    for claim in parsed_837.get("claims", []):
        claim_id = claim.get("claim_id", "")
        lines = claim.get("service_lines", [])

        # Build index for duplicate detection: (procedure_code, date_of_service) -> count
        line_key_counts: dict[tuple, int] = {}
        for line in lines:
            key = (line.get("procedure_code", ""), line.get("date_of_service", ""))
            line_key_counts[key] = line_key_counts.get(key, 0) + 1

        for line in lines:
            total_lines += 1
            code = line.get("procedure_code", "")
            modifiers = set(line.get("modifiers", []))
            billed = line.get("billed_amount", 0.0)
            line_num = line.get("line_number", 0)
            dos = line.get("date_of_service", "")

            total_billed += billed

            # Rule 1: HIGH_DOLLAR
            if billed > 5000:
                risk_flags.append({
                    "rule_id": "HIGH_DOLLAR",
                    "rule_name": "High Dollar Charge",
                    "risk_level": "HIGH",
                    "claim_id": claim_id,
                    "line_number": line_num,
                    "procedure_code": code,
                    "description": f"Billed amount ${billed:,.2f} exceeds $5,000 threshold — likely to trigger payer review.",
                })

            # Rule 2: BILATERAL_NO_MODIFIER
            if code in BILATERAL_CODES and not modifiers.intersection(BILATERAL_MODIFIERS):
                risk_flags.append({
                    "rule_id": "BILATERAL_NO_MODIFIER",
                    "rule_name": "Bilateral Procedure Missing Modifier",
                    "risk_level": "HIGH",
                    "claim_id": claim_id,
                    "line_number": line_num,
                    "procedure_code": code,
                    "description": f"CPT {code} is a bilateral procedure but lacks modifier 50, LT, or RT — high denial risk.",
                })

            # Rule 3: DUPLICATE_LINE
            key = (code, dos)
            if line_key_counts.get(key, 0) > 1:
                risk_flags.append({
                    "rule_id": "DUPLICATE_LINE",
                    "rule_name": "Duplicate Service Line",
                    "risk_level": "MEDIUM",
                    "claim_id": claim_id,
                    "line_number": line_num,
                    "procedure_code": code,
                    "description": f"CPT {code} appears multiple times on {dos} in claim {claim_id} — may be flagged as duplicate.",
                })

            # Rule 4: UNLISTED_CODE
            if code.endswith("99"):
                risk_flags.append({
                    "rule_id": "UNLISTED_CODE",
                    "rule_name": "Unlisted Procedure Code",
                    "risk_level": "MEDIUM",
                    "claim_id": claim_id,
                    "line_number": line_num,
                    "procedure_code": code,
                    "description": f"CPT {code} is an unlisted procedure — requires supporting documentation for adjudication.",
                })

            # Rule 5: MODIFIER_CONFLICT
            if "59" in modifiers and modifiers.intersection(MODIFIER_59_CONFLICTS):
                conflicting = modifiers.intersection(MODIFIER_59_CONFLICTS)
                risk_flags.append({
                    "rule_id": "MODIFIER_CONFLICT",
                    "rule_name": "Modifier 59 Conflict",
                    "risk_level": "MEDIUM",
                    "claim_id": claim_id,
                    "line_number": line_num,
                    "procedure_code": code,
                    "description": f"Modifier 59 used with {', '.join(sorted(conflicting))} — CMS replaced 59 with X-modifiers; using both may cause denial.",
                })

    high_count = sum(1 for f in risk_flags if f["risk_level"] == "HIGH")
    medium_count = sum(1 for f in risk_flags if f["risk_level"] == "MEDIUM")
    low_count = sum(1 for f in risk_flags if f["risk_level"] == "LOW")
    clean_count = total_lines - len(set(
        (f["claim_id"], f["line_number"]) for f in risk_flags
    ))

    return {
        "risk_flags": risk_flags,
        "summary": {
            "total_claims": len(parsed_837.get("claims", [])),
            "total_lines": total_lines,
            "total_billed": round(total_billed, 2),
            "high_risk_count": high_count,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "clean_count": max(clean_count, 0),
        },
    }
