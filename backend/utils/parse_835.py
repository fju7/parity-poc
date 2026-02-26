"""
Pure-Python 835 EDI (Electronic Remittance Advice) parser.

Parses X12 835 transaction sets to extract:
- Payer and payee information
- Production date
- Claim-level data (CLP segments)
- Service line items (SVC segments)
- Adjustment codes (CAS segments)

No external EDI libraries required.
"""

from typing import Optional


def parse_835(content: str) -> dict:
    """Parse an 835 EDI file and return structured data.

    Args:
        content: Raw text content of the 835 file.

    Returns:
        Dict with payer_name, payee_name, production_date, total_billed,
        total_paid, claim_count, claims, line_items.
    """
    # Detect segment delimiter
    segment_delim = _detect_segment_delimiter(content)

    # Split into segments and clean
    raw_segments = content.split(segment_delim)
    segments = [s.strip() for s in raw_segments if s.strip()]

    # Detect element delimiter from ISA segment
    element_delim = _detect_element_delimiter(segments)

    payer_name = ""
    payee_name = ""
    production_date = ""

    claims = []
    current_claim = None
    current_svc = None

    for seg in segments:
        elements = seg.split(element_delim)
        seg_id = elements[0].strip()

        if seg_id == "N1" and len(elements) > 2:
            qualifier = elements[1]
            name = elements[2] if len(elements) > 2 else ""
            if qualifier == "PR":
                payer_name = name
            elif qualifier == "PE":
                payee_name = name

        elif seg_id == "DTM" and len(elements) > 2:
            qualifier = elements[1]
            if qualifier == "405":
                production_date = _format_date(elements[2])

        elif seg_id == "CLP":
            # Save previous claim
            if current_claim is not None:
                if current_svc is not None:
                    current_claim["line_items"].append(current_svc)
                    current_svc = None
                claims.append(current_claim)

            current_claim = _parse_clp(elements)
            current_svc = None

        elif seg_id == "SVC" and current_claim is not None:
            # Save previous SVC if any
            if current_svc is not None:
                current_claim["line_items"].append(current_svc)

            current_svc = _parse_svc(elements)

        elif seg_id == "CAS" and current_claim is not None:
            adjustments = _parse_cas(elements)
            if current_svc is not None:
                current_svc.setdefault("adjustments", []).extend(adjustments)
            else:
                current_claim.setdefault("claim_adjustments", []).extend(adjustments)

        elif seg_id == "DTM" and current_svc is not None and len(elements) > 2:
            qualifier = elements[1]
            if qualifier == "472":
                current_svc["service_date"] = _format_date(elements[2])

    # Append final claim/svc
    if current_claim is not None:
        if current_svc is not None:
            current_claim["line_items"].append(current_svc)
        claims.append(current_claim)

    # Build flat line_items list and compute totals
    all_line_items = []
    total_billed = 0.0
    total_paid = 0.0

    for claim in claims:
        for item in claim.get("line_items", []):
            item["claim_id"] = claim.get("claim_id", "")
            all_line_items.append(item)

        total_billed += claim.get("billed_amount", 0)
        total_paid += claim.get("paid_amount", 0)

    return {
        "payer_name": payer_name,
        "payee_name": payee_name,
        "production_date": production_date,
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "claim_count": len(claims),
        "claims": claims,
        "line_items": all_line_items,
    }


def _detect_segment_delimiter(content: str) -> str:
    """Detect the segment delimiter (~ or newline after ISA)."""
    # ISA segment is always exactly 106 characters (including delimiters)
    # The segment terminator is at position 105
    isa_pos = content.find("ISA")
    if isa_pos >= 0:
        # Check for ~ after ISA content
        tilde_pos = content.find("~", isa_pos)
        newline_pos = content.find("\n", isa_pos)

        if tilde_pos >= 0 and (newline_pos < 0 or tilde_pos < newline_pos):
            return "~"

    # Default to ~ which is most common
    if "~" in content:
        return "~"

    return "\n"


def _detect_element_delimiter(segments: list[str]) -> str:
    """Detect element delimiter from ISA segment."""
    for seg in segments:
        if seg.startswith("ISA"):
            # Element delimiter is the character right after "ISA"
            if len(seg) > 3:
                return seg[3]
    # Default
    return "*"


def _format_date(date_str: str) -> str:
    """Format CCYYMMDD or YYMMDD date string to YYYY-MM-DD."""
    date_str = date_str.strip()
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) == 6:
        year = int(date_str[:2])
        prefix = "20" if year < 50 else "19"
        return f"{prefix}{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
    return date_str


def _safe_float(value: str) -> float:
    """Convert string to float, returning 0.0 on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value: str) -> int:
    """Convert string to int, returning 0 on failure."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def _parse_clp(elements: list[str]) -> dict:
    """Parse a CLP (claim-level) segment.

    CLP*claim_id*status*billed*paid*patient_resp*...
    """
    claim = {
        "claim_id": elements[1] if len(elements) > 1 else "",
        "status_code": elements[2] if len(elements) > 2 else "",
        "billed_amount": _safe_float(elements[3]) if len(elements) > 3 else 0.0,
        "paid_amount": _safe_float(elements[4]) if len(elements) > 4 else 0.0,
        "patient_responsibility": _safe_float(elements[5]) if len(elements) > 5 else 0.0,
        "line_items": [],
        "claim_adjustments": [],
    }

    # Map status codes
    status_map = {
        "1": "PROCESSED_PRIMARY",
        "2": "PROCESSED_SECONDARY",
        "3": "PROCESSED_TERTIARY",
        "4": "DENIED",
        "19": "PROCESSED_PRIMARY_FORWARD",
        "20": "PROCESSED_SECONDARY_FORWARD",
        "21": "PROCESSED_TERTIARY_FORWARD",
        "22": "REVERSAL",
        "23": "NOT_OUR_CLAIM",
    }
    claim["status"] = status_map.get(claim["status_code"], f"UNKNOWN_{claim['status_code']}")

    return claim


def _parse_svc(elements: list[str]) -> dict:
    """Parse a SVC (service line) segment.

    SVC*qualifier:code*billed*paid*...*units
    """
    # First element after SVC is the composite: qualifier:code
    composite = elements[1] if len(elements) > 1 else ""
    sub_delim = ":"
    parts = composite.split(sub_delim)

    qualifier = parts[0] if len(parts) > 0 else ""
    code = parts[1] if len(parts) > 1 else composite

    # Determine code type from qualifier
    # HC = HCPCS/CPT, WK = workers comp, etc.
    code_type = "CPT" if qualifier in ("HC", "WK") else "REVENUE" if qualifier == "RB" else "OTHER"

    return {
        "cpt_code": code,
        "code_type": code_type,
        "qualifier": qualifier,
        "billed_amount": _safe_float(elements[2]) if len(elements) > 2 else 0.0,
        "paid_amount": _safe_float(elements[3]) if len(elements) > 3 else 0.0,
        "units": _safe_int(elements[6]) if len(elements) > 6 else 1,
        "adjustments": [],
        "service_date": "",
    }


def _parse_cas(elements: list[str]) -> list[dict]:
    """Parse a CAS (adjustment) segment.

    CAS*group*reason1*amount1*quantity1*reason2*amount2*...
    Adjustments come in groups of 3 after the group code.
    """
    if len(elements) < 4:
        return []

    group_code = elements[1]
    adjustments = []

    # Group code meanings
    group_names = {
        "CO": "Contractual Obligation",
        "PR": "Patient Responsibility",
        "OA": "Other Adjustment",
        "PI": "Payer Initiated",
        "CR": "Correction/Reversal",
    }

    # Parse triplets: reason_code, amount, quantity
    idx = 2
    while idx < len(elements):
        reason_code = elements[idx] if idx < len(elements) else ""
        amount = _safe_float(elements[idx + 1]) if idx + 1 < len(elements) else 0.0
        quantity = _safe_int(elements[idx + 2]) if idx + 2 < len(elements) else 0

        if reason_code:
            adjustments.append({
                "group_code": group_code,
                "group_name": group_names.get(group_code, group_code),
                "reason_code": reason_code,
                "amount": amount,
                "quantity": quantity,
                "code": f"{group_code}-{reason_code}",
            })

        idx += 3

    return adjustments
