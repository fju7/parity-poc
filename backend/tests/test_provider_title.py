"""Provider-title fix: use the provider's title only if the denial states it;
otherwise refer to them neutrally as "the ordering provider, <Name>" and never
invent "Dr." (or any credential).

The letter body is model-generated, so the title/neutral-fallback behavior is
verified end-to-end in the UI/live check. These deterministic offline tests guard
the pieces we CAN assert: the extraction now captures a stated provider_title
(and must not default to "Dr."), the appeal prompt carries the neutral-fallback /
never-assume-physician rule, and the code-level name resolver never injects a
title of its own.
"""

import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import (  # noqa: E402
    _resolve_placeholder,
    APPEAL_SYSTEM_PROMPT,
    DENIAL_SYSTEM_PROMPT,
)


def test_extraction_captures_provider_title_without_defaulting_to_dr():
    assert '"provider_title"' in DENIAL_SYSTEM_PROMPT              # the field exists
    low = DENIAL_SYSTEM_PROMPT.lower()
    assert "do not guess, assume, or default to" in low          # no auto-"Dr."
    assert "name only" in low                                    # provider_name is name-only


def test_appeal_prompt_has_neutral_fallback_and_never_assume_physician():
    p = APPEAL_SYSTEM_PROMPT
    assert "provider_title" in p                                 # rule references the field
    assert "the ordering provider, <Name>" in p                  # neutral fallback form
    assert "Never assume the provider is a physician." in p
    assert "do NOT use \"Dr.\"" in p                             # explicit no-invented-Dr rule


def test_resolve_placeholder_returns_bare_name_no_invented_title():
    # The code resolver returns the stored name verbatim; it never prepends "Dr.".
    assert _resolve_placeholder("Provider Name", {"provider_name": "Sam Jones"}) == "Sam Jones"
    assert _resolve_placeholder("ordering provider", {"provider_name": "Sam Jones, NP"}) == "Sam Jones, NP"
    # No provider name known -> None (no fabricated value, no "Dr.").
    assert _resolve_placeholder("provider name", {}) is None
