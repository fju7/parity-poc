"""
Rate versioning utilities — resolve a service date to the correct
CMS rate schedule version.

Uses Supabase to query rate_schedule_versions.  Falls back to the
current in-memory rates when no historical data is available.
"""

from datetime import date, datetime
from typing import Optional

import os
from supabase import create_client

# ---------------------------------------------------------------------------
# Supabase client (shared lazy singleton)
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not set")
        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_version_for_date(
    schedule_type: str,
    service_date: date,
) -> Optional[str]:
    """Return the version_id (UUID string) for the rate schedule that was
    in effect on *service_date*.

    Lookup logic:
      1. Find rows where type matches, effective_date <= service_date,
         and expiry_date is NULL or > service_date.
      2. If no match, fall back to the row marked is_current.
      3. If service_date is before the earliest available, return the earliest.

    Returns None only if the table is empty for that schedule type.
    """
    schedule_type = schedule_type.upper()
    date_str = service_date.isoformat()

    sb = _get_supabase()

    # Try exact range match
    result = (
        sb.table("rate_schedule_versions")
        .select("id")
        .eq("schedule_type", schedule_type)
        .lte("effective_date", date_str)
        .or_(f"expiry_date.is.null,expiry_date.gt.{date_str}")
        .order("effective_date", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]["id"]

    # No range match — service_date may be before earliest available.
    # Return the earliest version for this schedule type.
    earliest = (
        sb.table("rate_schedule_versions")
        .select("id")
        .eq("schedule_type", schedule_type)
        .order("effective_date", desc=False)
        .limit(1)
        .execute()
    )

    if earliest.data:
        return earliest.data[0]["id"]

    # Fall back to current
    current = (
        sb.table("rate_schedule_versions")
        .select("id")
        .eq("schedule_type", schedule_type)
        .eq("is_current", True)
        .limit(1)
        .execute()
    )

    return current.data[0]["id"] if current.data else None


def get_vintage_label(
    schedule_type: str,
    service_date: date,
) -> str:
    """Return a human-readable label like 'CMS PFS 2024' for the rate
    schedule version that covers *service_date*.
    """
    schedule_type = schedule_type.upper()
    version_id = get_version_for_date(schedule_type, service_date)

    if version_id is None:
        return f"CMS {schedule_type} (unknown)"

    sb = _get_supabase()
    result = (
        sb.table("rate_schedule_versions")
        .select("vintage_year, vintage_quarter")
        .eq("id", version_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return f"CMS {schedule_type} (unknown)"

    row = result.data[0]
    year = row["vintage_year"]
    quarter = row.get("vintage_quarter")

    if quarter:
        return f"CMS {schedule_type} {year} Q{quarter}"
    return f"CMS {schedule_type} {year}"


def is_using_current_rates(service_date: date) -> bool:
    """Return True if *service_date* falls within the current rate period
    (i.e. no historical lookup would be needed).

    Checks against the PFS current version's effective_date as the
    canonical reference.
    """
    sb = _get_supabase()
    result = (
        sb.table("rate_schedule_versions")
        .select("effective_date")
        .eq("schedule_type", "PFS")
        .eq("is_current", True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return True  # No version data — assume current

    effective = date.fromisoformat(result.data[0]["effective_date"])
    return service_date >= effective


# ---------------------------------------------------------------------------
# Date parsing helper
# ---------------------------------------------------------------------------


def parse_service_date(raw: str) -> Optional[date]:
    """Parse a service date string in MM/DD/YYYY or YYYY-MM-DD format.

    Returns None if parsing fails.
    """
    if not raw:
        return None

    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue

    return None
