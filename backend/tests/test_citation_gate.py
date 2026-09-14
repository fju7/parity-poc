"""utils/citation_gate.py: every citation-shaped string is found; plain
statements of obligation are not.

The positive cases are the twelve wrong citations found in ten real letters
on 2026-09-14, in the exact forms the letters used. The negative cases are
the register the prompt now asks for.

Run: python3 -m pytest backend/tests/test_citation_gate.py -q
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.citation_gate import check_letter, find_citations, violations_note  # noqa: E402

WRONG_IN_REAL_LETTERS = [
    "Under Ohio Revised Code § 3901.38, clean claims must be paid within thirty days.",
    "Ohio Administrative Code § 3901-1-54 governs unfair claim settlement practices.",
    "pursuant to Ohio Revised Code § 3902.11(B), the insurer must disclose its criteria",
    "Ohio Revised Code § 3902.13 (Ohio Prompt Pay Act) mandates adjudication within 30 days",
    "consistent with applicable Ohio state prompt pay statutes (Ohio Revised Code § 3902.14)",
    "Ohio's prompt pay statutes (Ohio Revised Code § 3902.01 et seq.)",
    "Ohio Revised Code § 3923.021 — Ohio's prompt pay statute requires",
    "The applicable federal standard for medical necessity is codified at 42 CFR § 410.32(a)",
    "Under 42 CFR § 424.5(a)(6), a claim for payment must contain sufficient information",
    "45 CFR § 147.130 and ACA Cost-Sharing Provisions",
    "CMS Claims Processing Manual, Publication 100-04, Chapter 1, Section 80.3.1 — Defines the parameters",
    "CMS IOM Publication 100-04, Chapter 1, Section 80.3.2 establishes the standards",
    "the NCCI Policy Manual, Chapter 1, Section D, states that a separate E/M service",
    "in accordance with AMA CPT coding guidelines and CMS Claims Processing Manual, Chapter 12",
    "pursuant to R.C. 3901.381 and 29 U.S.C. § 1133",
    "Cal. Ins. Code 10123.13 and Tex. Ins. Code Ann. 843.338",
    "see LCD L33822 and NCD 190.22",
]

GENERIC_REGISTER = [
    "under the applicable state prompt-pay requirements, within 30 calendar days of receipt",
    "under the plan's own medical-necessity standard and the clinical record",
    "under standard correct-coding conventions for separately identifiable services",
    "the practice reserves its rights under the applicable external-review process",
    "RE: Formal Appeal of CO-97 — Claim L03; Date of Service: August 12, 2026; CPT Code: 99214",
    "Billed Amount: $185.00; Payer Reference Number: L03; NPI 1234567893; Suite 200",
    "Section 3 above; 42 patients; the 2021 AMA revisions to office visit coding",
    "escalation to the state Department of Insurance and/or the dispute resolution process",
    "We demand reprocessing and payment within 30 calendar days.",
]


@pytest.mark.parametrize("text", WRONG_IN_REAL_LETTERS)
def test_every_real_wrong_citation_is_found(text):
    assert find_citations(text), text


@pytest.mark.parametrize("text", GENERIC_REGISTER)
def test_the_generic_register_passes(text):
    assert find_citations(text) == [], [c.text for c in find_citations(text)]


def test_check_letter_is_the_gate():
    assert check_letter("no law here, only obligations in plain words") == []
    assert check_letter("Under 42 CFR § 424.5(a)(6) the claim is complete.")


def test_violations_note_lists_each_citation_once():
    cites = find_citations("42 CFR § 424.5(a)(6) ... and again 42 CFR § 424.5(a)(6) ... Ohio Revised Code § 3901.38")
    note = violations_note(cites)
    assert note.count("424.5(a)(6)") == 1 and "3901.38" in note and "NO statute" in note
