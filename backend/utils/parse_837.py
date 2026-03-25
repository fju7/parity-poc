"""
Pure-Python 837P EDI (Professional Claim) parser.

Parses X12 837P transaction sets to extract:
- Submitter and billing provider information
- Patient demographics (NM1*QC / NM1*IL)
- Claim-level data (CLM segments)
- Diagnosis codes (HI segments with ABK/ABF qualifiers)
- Service line items (SV1 segments under LX loops)
- Rendering provider NPI (NM1*82)
- Dates of service (DTP*472)

No external EDI libraries required.
"""

from __future__ import annotations

from typing import List


def parse_837(file_content: str) -> dict:
    """Parse an 837P EDI file and return structured data.

    Args:
        file_content: Raw text content of the 837P file.

    Returns:
        Dict with submitter_name, billing_provider_name, billing_provider_npi,
        parser_version, claims (array of claim dicts with service_lines).
    """
    segment_delim = _detect_segment_delimiter(file_content)
    raw_segments = file_content.split(segment_delim)
    segments = [s.strip() for s in raw_segments if s.strip()]
    element_delim = _detect_element_delimiter(segments)

    submitter_name = ""
    billing_provider_name = ""
    billing_provider_npi = ""

    claims: List[dict] = []
    current_claim: dict | None = None
    current_line: dict | None = None

    # In 837P, NM1*IL/QC appear BEFORE the CLM segment in the same HL loop.
    # We buffer patient info and apply it when the CLM is created.
    pending_patient_name = ""
    pending_subscriber_id = ""

    # Track NM1 context: are we at header level or inside a claim?
    # NM1*41 = submitter, NM1*85 = billing provider (header-level)
    # NM1*QC = patient, NM1*IL = subscriber, NM1*82 = rendering (claim-level)

    for seg in segments:
        elements = seg.split(element_delim)
        seg_id = elements[0].strip()

        if seg_id == "HL":
            # New hierarchical level — save current claim if any, reset pending
            if current_claim is not None:
                if current_line is not None:
                    current_claim["service_lines"].append(current_line)
                    current_line = None
                claims.append(current_claim)
                current_claim = None
            pending_patient_name = ""
            pending_subscriber_id = ""

        elif seg_id == "NM1" and len(elements) > 2:
            qualifier = elements[1]

            if qualifier == "41":
                # Submitter
                submitter_name = _build_name(elements)

            elif qualifier == "85" and current_claim is None:
                # Billing provider (header level, before any CLM)
                billing_provider_name = _build_name(elements)
                billing_provider_npi = _extract_npi(elements)

            elif qualifier in ("QC", "IL"):
                # Patient (QC) or subscriber/insured (IL)
                # These may appear before or after CLM — buffer if no current claim
                name = _build_name(elements)
                sub_id = _extract_npi(elements) if qualifier == "IL" else ""
                if current_claim is not None:
                    if qualifier == "QC":
                        current_claim["patient_name"] = name
                    elif qualifier == "IL":
                        if not current_claim.get("patient_name"):
                            current_claim["patient_name"] = name
                        current_claim["subscriber_id"] = sub_id
                else:
                    # Buffer for the next CLM
                    if qualifier == "QC":
                        pending_patient_name = name
                    elif qualifier == "IL":
                        if not pending_patient_name:
                            pending_patient_name = name
                        pending_subscriber_id = sub_id

            elif qualifier == "82" and current_claim is not None:
                # Rendering provider
                current_claim["rendering_provider_npi"] = _extract_npi(elements)

        elif seg_id == "CLM" and len(elements) > 2:
            # Save previous claim
            if current_claim is not None:
                if current_line is not None:
                    current_claim["service_lines"].append(current_line)
                    current_line = None
                claims.append(current_claim)

            pos = ""
            if len(elements) > 5:
                pos_composite = elements[5]
                pos_parts = pos_composite.split(":")
                pos = pos_parts[0] if pos_parts else ""

            current_claim = {
                "claim_id": elements[1],
                "total_billed": _safe_float(elements[2]),
                "place_of_service": pos,
                "patient_name": pending_patient_name,
                "subscriber_id": pending_subscriber_id,
                "date_of_service": "",
                "diagnosis_codes": [],
                "rendering_provider_npi": "",
                "service_lines": [],
            }
            pending_patient_name = ""
            pending_subscriber_id = ""
            current_line = None

        elif seg_id == "HI" and current_claim is not None:
            # Diagnosis codes: HI*ABK:J06.9*ABF:R05.9*...
            for el in elements[1:]:
                parts = el.split(":")
                if len(parts) >= 2 and parts[0] in ("ABK", "ABF"):
                    current_claim["diagnosis_codes"].append(parts[1])

        elif seg_id == "DTP" and len(elements) > 2:
            qualifier = elements[1]
            if qualifier == "472":
                # DTP*472*D8*20260115 — date is element 3 (index 3)
                # DTP*472*RD8*20260115-20260120 — date range, take start
                raw_date = elements[3] if len(elements) > 3 else elements[2]
                # Handle RD8 date ranges (take start date)
                if "-" in raw_date:
                    raw_date = raw_date.split("-")[0]
                date_val = _format_date(raw_date)
                # If we're inside a service line, it's line-level DOS
                if current_line is not None:
                    current_line["date_of_service"] = date_val
                elif current_claim is not None:
                    # Claim-level DOS
                    current_claim["date_of_service"] = date_val

        elif seg_id == "LX" and current_claim is not None:
            # New service line loop
            if current_line is not None:
                current_claim["service_lines"].append(current_line)
            current_line = {
                "line_number": int(elements[1]) if len(elements) > 1 and elements[1].isdigit() else 0,
                "procedure_code": "",
                "modifiers": [],
                "billed_amount": 0.0,
                "units": 1,
                "date_of_service": "",
                "diagnosis_pointers": "",
            }

        elif seg_id == "SV1" and current_claim is not None:
            # Professional service line: SV1*HC:code:mod1:mod2*amount*UN*units*...*diag_pointers
            composite = elements[1] if len(elements) > 1 else ""
            parts = composite.split(":")

            code = parts[1] if len(parts) > 1 else ""
            modifiers = [m for m in parts[2:] if m]

            if current_line is None:
                # SV1 without preceding LX — create a line
                current_line = {
                    "line_number": len(current_claim["service_lines"]) + 1,
                    "procedure_code": "",
                    "modifiers": [],
                    "billed_amount": 0.0,
                    "units": 1,
                    "date_of_service": "",
                    "diagnosis_pointers": "",
                }

            current_line["procedure_code"] = code
            current_line["modifiers"] = modifiers
            current_line["billed_amount"] = _safe_float(elements[2]) if len(elements) > 2 else 0.0
            current_line["units"] = _safe_int(elements[4]) if len(elements) > 4 else 1
            current_line["diagnosis_pointers"] = elements[7] if len(elements) > 7 else ""

    # Append final claim/line
    if current_claim is not None:
        if current_line is not None:
            current_claim["service_lines"].append(current_line)
        claims.append(current_claim)

    # Propagate claim-level DOS to lines that don't have their own
    for claim in claims:
        for line in claim.get("service_lines", []):
            if not line.get("date_of_service") and claim.get("date_of_service"):
                line["date_of_service"] = claim["date_of_service"]

    return {
        "submitter_name": submitter_name,
        "billing_provider_name": billing_provider_name,
        "billing_provider_npi": billing_provider_npi,
        "parser_version": 1,
        "claims": claims,
    }


def _detect_segment_delimiter(content: str) -> str:
    """Detect the segment delimiter (~ or newline)."""
    isa_pos = content.find("ISA")
    if isa_pos >= 0:
        tilde_pos = content.find("~", isa_pos)
        newline_pos = content.find("\n", isa_pos)
        if tilde_pos >= 0 and (newline_pos < 0 or tilde_pos < newline_pos):
            return "~"
    if "~" in content:
        return "~"
    return "\n"


def _detect_element_delimiter(segments: List[str]) -> str:
    """Detect element delimiter from ISA segment."""
    for seg in segments:
        if seg.startswith("ISA"):
            if len(seg) > 3:
                return seg[3]
    return "*"


def _format_date(date_str: str) -> str:
    """Format CCYYMMDD date string to YYYY-MM-DD."""
    date_str = date_str.strip()
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    elif len(date_str) == 6:
        year = int(date_str[:2])
        prefix = "20" if year < 50 else "19"
        return f"{prefix}{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
    return date_str


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value: str) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def _extract_npi(elements: list) -> str:
    """Extract NPI/ID from NM1 segment — handles both person (type 1) and org (type 2).

    For type 1 (person): NM1*qual*1*Last*First*Mid*Suffix*IDQual*ID — ID at index 9
    For type 2 (org):    NM1*qual*2*OrgName****IDQual*ID — ID at index 8
    We find the ID qualifier (XX, MI, etc.) and take the next element.
    """
    # Look for the ID qualifier and return the element after it
    for i in range(7, len(elements) - 1):
        if elements[i] in ("XX", "MI", "46", "FI", "SV", "II", "24"):
            return elements[i + 1] if i + 1 < len(elements) else ""
    # Fallback: try index 9, then 8
    if len(elements) > 9 and elements[9]:
        return elements[9]
    if len(elements) > 8 and elements[8]:
        return elements[8]
    return ""


def _build_name(elements: list) -> str:
    """Build a name from NM1 segment elements."""
    name_parts = []
    if len(elements) > 3 and elements[3]:
        name_parts.append(elements[3])  # last name
    if len(elements) > 4 and elements[4]:
        name_parts.append(elements[4])  # first name
    if name_parts:
        return " ".join(name_parts)
    return elements[2] if len(elements) > 2 else ""
