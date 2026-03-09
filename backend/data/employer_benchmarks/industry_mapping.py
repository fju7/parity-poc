"""Mapping between user-friendly display names and MEPS-IC data keys."""

INDUSTRY_DISPLAY_TO_MEPS = {
    "Agriculture / Forestry / Fishing": "Ag/forestry/fishing",
    "Construction": "Construction",
    "Finance / Real Estate / Insurance": "Fin. svs. and real est.",
    "Manufacturing": "Mining and manufacturing",
    "Other Services": "Other services",
    "Professional Services": "Professional services",
    "Retail Trade": "Retail trade",
    "Transportation / Utilities": "Utilities and transportation",
    "Wholesale Trade": "Wholesale trade",
}

# Ordered list for frontend dropdowns
INDUSTRY_DISPLAY_NAMES = sorted(INDUSTRY_DISPLAY_TO_MEPS.keys())


def resolve_industry(display_name: str) -> str:
    """Convert a display name to a MEPS-IC key. Falls back to the input if no match."""
    # Direct match
    if display_name in INDUSTRY_DISPLAY_TO_MEPS:
        return INDUSTRY_DISPLAY_TO_MEPS[display_name]
    # Already a MEPS key
    meps_values = set(INDUSTRY_DISPLAY_TO_MEPS.values())
    if display_name in meps_values:
        return display_name
    # Case-insensitive fuzzy match
    lower = display_name.lower()
    for disp, meps in INDUSTRY_DISPLAY_TO_MEPS.items():
        if lower in disp.lower() or lower in meps.lower():
            return meps
    return display_name
