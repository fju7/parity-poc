"""PH: appeal rights and deadlines faithful to the denial.

The extraction prompt must capture appeal rights and deadlines ONLY as the denial
literally states them (no added statutes/agencies/labels, no unit conversion), and
the appeal letter must add a single general reservation-of-rights clause instead of
enumerating unstated rights.

These are deterministic prompt-content assertions (plus a source-level check that the
reservation wording is flagged for attorney review). No live model, network, or DB.
Note: no code-level handling of the deadline fields changed in this brief — the
behavior is governed entirely by the prompt text, so the "72 hours, not 3 days"
guarantee is asserted as a prompt rule (Task 4.2).
"""

import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers import health_analyze  # noqa: E402
from routers.health_analyze import DENIAL_SYSTEM_PROMPT, APPEAL_SYSTEM_PROMPT  # noqa: E402


# -- Task 1: appeal_rights extraction is literal-to-the-denial, no additive seed list --
def test_appeal_rights_extraction_literal_no_additive_examples():
    p = DENIAL_SYSTEM_PROMPT
    # the old additive seed examples are gone (they seeded fabricated labels)
    assert "ERISA §502(a)" not in p
    assert "'ACA external review'" not in p
    assert "Florida Dept. of Financial Services" not in p
    # the new literal-capture rule and its explicit example are present
    assert "ONLY as the denial LITERALLY states them" in p
    assert "Independent external reviews" in p
    assert "do NOT relabel it 'ACA independent external review' or add 'ACA'" in p
    assert "Return [] if the denial states no appeal rights" in p


# -- Task 2: deadline extraction forbids unit conversion (hours stay hours) --
def test_deadline_extraction_no_unit_conversion():
    p = DENIAL_SYSTEM_PROMPT
    assert "NEVER convert to days" in p
    assert "'72 hours', store '72 hours'" in p
    # non-day units route to the literal hint, numeric field stays null
    assert p.count("leave this null and capture the literal phrase in appeal_deadline_hint instead (do NOT convert)") == 2
    assert "in its OWN literal words and units, verbatim" in p


# -- Task 2.2 (also Task 4.2): letter states deadlines with the denial's literal wording --
def test_letter_prompt_deadline_literal_wording_no_conversion():
    p = APPEAL_SYSTEM_PROMPT
    assert 'use the denial\'s LITERAL timeframe wording exactly as given' in p
    assert 'never turn "72 hours" into "3 days"' in p          # explicit 72h != 3d guarantee
    assert "do NOT invent a timeframe the denial did not state" in p


# -- Task 3: letter states only denial-named rights + ONE general reservation clause --
def test_letter_prompt_rights_and_single_reservation_clause():
    p = APPEAL_SYSTEM_PROMPT
    assert "in the denial's own words, adding nothing" in p
    assert "Do NOT add appeal rights, statutes, programs, or agencies that are not listed there" in p
    reservation = ("The patient reserves all other appeal and external-review rights "
                   "available under applicable federal and state law.")
    assert reservation in p
    assert "exactly ONE general reservation sentence" in p
    # empty appeal_rights -> generic appeal + the SAME single reservation sentence, no invented rights
    assert "do not invent rights (no specific statutes, programs, or agencies)" in p
    assert "followed by that same single general reservation sentence" in p


# -- Task 3.2: reservation wording flagged in a code comment for attorney review --
def test_reservation_clause_flagged_for_legal_review():
    src = open(health_analyze.__file__, encoding="utf-8").read()
    assert "LEGAL REVIEW PENDING" in src
    # the flag names the reservation clause and marks the wording as a pending placeholder
    assert "reservation-of-rights clause" in src
    assert "pending attorney review" in src
