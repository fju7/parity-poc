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


# -- Task 3, rewritten under APPEALS-3 (Fred's ruling 2026-09-17): the letter names appeal /
# external-review options ONLY as the denial states them, and carries NO reservation-of-rights
# sentence and NO "right to appeal" phrasing. The legal register is refused by the gate. --
def test_letter_prompt_rights_only_as_denial_states_them_no_reservation():
    p = APPEAL_SYSTEM_PROMPT
    assert "in the denial's own words, as facts about what the denial letter says" in p
    assert "Do NOT add options, statutes, programs, or agencies that are not listed there" in p
    assert "Do NOT add any reservation-of-rights sentence" in p
    assert "do NOT describe the appeal as the exercise of a right" in p
    # the old sentence and the old phrasing are gone from the prompt
    assert "reserves all other appeal and external-review rights" not in p
    assert "under applicable federal and state law" not in p
    assert "exercising their right to appeal" not in p
    # the sentence the letter is told to write when the denial names no options clears the register gate
    from verify.extract import extract_legal_register
    assert extract_legal_register("The patient is appealing this determination and asks for it to be reconsidered.") == []
    # and the old sentence does not
    assert extract_legal_register("The patient reserves all other appeal and external-review rights "
                                  "available under applicable federal and state law.") != []


# -- Task 3.2, rewritten: no attorney review is pending; the code says so --
def test_no_legal_review_pending():
    src = open(health_analyze.__file__, encoding="utf-8").read()
    assert "LEGAL REVIEW PENDING" not in src
    assert "No attorney review is pending" in src
