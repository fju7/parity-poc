"""
Coding intelligence checks — NCCI edit violations and MUE unit limits.

Data is loaded from Supabase at startup. Falls back to empty dicts
(no alerts) if Supabase is unavailable.
"""

from collections import Counter
from itertools import combinations

# In-memory lookup dicts (populated by load_coding_data)
ncci_edits: dict = {}   # (code1, code2) -> {"modifier_indicator": 0|1}
mue_limits: dict = {}   # code -> {"practitioner_mue": int, "facility_mue": int}


def load_coding_data():
    """Fetch NCCI edits and MUE limits from Supabase into memory.

    Paginates in batches of 1000. Falls back gracefully if Supabase
    is unavailable or the tables don't exist yet.
    """
    global ncci_edits, mue_limits

    try:
        from supabase_client import supabase as sb
        if sb is None:
            print("Coding intelligence: No Supabase key — skipping data load")
            return
    except Exception as exc:
        print(f"Coding intelligence: Could not import Supabase client — {exc}")
        return

    # --- NCCI edits ---
    try:
        ncci_edits_tmp = {}
        offset = 0
        batch_size = 1000
        while True:
            resp = (
                sb.table("ncci_edits")
                .select("column1_code, column2_code, modifier_indicator")
                .range(offset, offset + batch_size - 1)
                .execute()
            )
            rows = resp.data or []
            for r in rows:
                c1 = r["column1_code"].strip()
                c2 = r["column2_code"].strip()
                mod = int(r["modifier_indicator"])
                # Store bidirectionally for O(1) pair lookup
                ncci_edits_tmp[(c1, c2)] = {"modifier_indicator": mod}
                ncci_edits_tmp[(c2, c1)] = {"modifier_indicator": mod}
            if len(rows) < batch_size:
                break
            offset += batch_size
        ncci_edits = ncci_edits_tmp
        print(f"Coding intelligence: Loaded {len(ncci_edits) // 2:,} NCCI edit pairs")
    except Exception as exc:
        print(f"Coding intelligence: Failed to load NCCI edits — {exc}")

    # --- MUE limits ---
    try:
        mue_limits_tmp = {}
        offset = 0
        batch_size = 1000
        while True:
            resp = (
                sb.table("mue_limits")
                .select("hcpcs_code, practitioner_mue, facility_mue")
                .range(offset, offset + batch_size - 1)
                .execute()
            )
            rows = resp.data or []
            for r in rows:
                code = r["hcpcs_code"].strip()
                mue_limits_tmp[code] = {
                    "practitioner_mue": int(r["practitioner_mue"]),
                    "facility_mue": int(r["facility_mue"]),
                }
            if len(rows) < batch_size:
                break
            offset += batch_size
        mue_limits = mue_limits_tmp
        print(f"Coding intelligence: Loaded {len(mue_limits):,} MUE limits")
    except Exception as exc:
        print(f"Coding intelligence: Failed to load MUE limits — {exc}")


def check_ncci_edits(codes: list[str]) -> list[dict]:
    """Check all unique code pairs for NCCI edit violations."""
    if not ncci_edits:
        return []

    alerts = []
    unique_codes = list(set(codes))
    for c1, c2 in combinations(unique_codes, 2):
        edit = ncci_edits.get((c1, c2))
        if edit is None:
            continue

        mod = edit["modifier_indicator"]
        if mod == 0:
            # Hard edit — codes cannot be billed together
            alerts.append({
                "checkType": "NCCI_EDIT",
                "codes": [c1, c2],
                "confidence": "high",
                "severity": "warning",
                "message": (
                    f"CPT {c1} and {c2} cannot be billed together per CMS "
                    f"National Correct Coding Initiative. This is a hard edit — "
                    f"no modifier override is permitted."
                ),
                "source": "CMS NCCI Edits 2026",
            })
        else:
            # Soft edit — modifier may allow separate billing
            alerts.append({
                "checkType": "NCCI_EDIT",
                "codes": [c1, c2],
                "confidence": "medium",
                "severity": "info",
                "message": (
                    f"CPT {c1} and {c2} are subject to an NCCI edit. "
                    f"A modifier may be required to bill these separately. "
                    f"Verify that an appropriate modifier was applied."
                ),
                "source": "CMS NCCI Edits 2026",
            })

    return alerts


def check_mue_limits(codes: list[str]) -> list[dict]:
    """Check code frequencies against MUE unit limits."""
    if not mue_limits:
        return []

    alerts = []
    counts = Counter(codes)
    for code, count in counts.items():
        limit = mue_limits.get(code)
        if limit is None:
            continue

        max_units = max(limit["practitioner_mue"], limit["facility_mue"])
        if count > max_units:
            alerts.append({
                "checkType": "MUE_LIMIT",
                "codes": [code],
                "confidence": "high",
                "severity": "warning",
                "message": (
                    f"CPT {code} appears {count} time(s) but the CMS Medically "
                    f"Unlikely Edit limit is {max_units} unit(s) per encounter. "
                    f"Units exceeding this limit are likely to be denied."
                ),
                "source": "CMS MUE Tables 2026",
            })

    return alerts


def run_coding_checks(codes: list[str]) -> list[dict]:
    """Run all backend coding intelligence checks.

    Returns a list of alert dicts, each with:
      checkType, codes[], confidence, severity, message, source
    """
    alerts = []
    alerts.extend(check_ncci_edits(codes))
    alerts.extend(check_mue_limits(codes))
    return alerts
