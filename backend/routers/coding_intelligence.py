"""
Coding intelligence checks — NCCI edit violations and MUE unit limits.

MUE limits (~15K rows) are loaded into memory at startup.
NCCI edits (~2.2M rows) are queried from Supabase on demand per request
to avoid OOM on memory-constrained hosts.
"""

from collections import Counter
from itertools import combinations

# In-memory lookup dicts
mue_limits: dict = {}   # code -> {"practitioner_mue": int, "facility_mue": int}

# Supabase client reference (set during load)
_sb = None


def load_coding_data():
    """Fetch MUE limits from Supabase into memory.

    NCCI edits are too large (~2.2M rows) to hold in memory on
    free-tier hosting, so they are queried per-request instead.
    """
    global mue_limits, _sb

    try:
        from supabase_client import supabase as sb
        if sb is None:
            print("Coding intelligence: No Supabase key — skipping data load")
            return
        _sb = sb
    except Exception as exc:
        print(f"Coding intelligence: Could not import Supabase client — {exc}")
        return

    # --- MUE limits (small table, safe to hold in memory) ---
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

    print("Coding intelligence: NCCI edits will be queried per-request from Supabase")


def check_ncci_edits(codes: list[str]) -> list[dict]:
    """Check all unique code pairs for NCCI edit violations.

    Queries Supabase for only the relevant codes on this bill,
    rather than holding the full 2.2M edit table in memory.
    """
    if _sb is None:
        return []

    unique_codes = list(set(codes))
    if len(unique_codes) < 2:
        return []

    # Query NCCI edits where column1_code is in our code list
    try:
        resp = (
            _sb.table("ncci_edits")
            .select("column1_code, column2_code, modifier_indicator")
            .in_("column1_code", unique_codes)
            .in_("column2_code", unique_codes)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        print(f"Coding intelligence: NCCI query failed — {exc}")
        return []

    # Build lookup from results
    edit_map = {}
    for r in rows:
        c1 = r["column1_code"].strip()
        c2 = r["column2_code"].strip()
        mod = int(r["modifier_indicator"])
        edit_map[(c1, c2)] = mod
        edit_map[(c2, c1)] = mod

    alerts = []
    for c1, c2 in combinations(unique_codes, 2):
        mod = edit_map.get((c1, c2))
        if mod is None:
            continue

        if mod == 0:
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
