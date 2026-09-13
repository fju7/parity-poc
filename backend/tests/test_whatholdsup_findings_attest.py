"""findings.attestation_for -- an operator's recorded answer is the durable
state for a licence-barred source, and it never reaches across sources.

12 September 2026: c82 (cdk46) had been answered as S001-07 on 29 August, two
days before the gate that raised it; the gate is forbidden to read S001 and
had nowhere to look. The resolver reads the advocate adjudication files as the
record they are. The safety property tested here is the one that matters: an
answer read in S001 closes nothing about S015.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"))
import findings as F  # noqa: E402

ADJ = """# adjudication

## S001 — The Guideline, version 6.2026

### S001-01 — SERIOUS / SERIOUS

**Question.** What does the guideline print for TRIAL-A's hazard ratio?

ANSWERED BY: A Person
ON:          2026-08-29
ANSWER:      The guideline lists TRIAL-A at HR 0.56 (0.45-0.70).
LOCATOR:     trial-summary table
EFFECT:      none

### S001-02 — withdrawn, not answered

**Question.** Never answered.
"""


def _issue(tmp_path, monkeypatch):
    (tmp_path / "advocate").mkdir()
    (tmp_path / "advocate" / "2026-08-29-adjudication.md").write_text(ADJ, encoding="utf-8")
    srcs = [{"id": "S001", "title": "The Guideline, version 6.2026", "also_called": ["the guideline"],
             "licence_forbids_machine_reading": True, "access": {"state": "human_read"}},
            {"id": "S015", "title": "A network meta-analysis. Sci Rep 2024", "also_called": ["the NMA"],
             "access": {"state": "full_text_held"}}]
    (tmp_path / "sources.json").write_text(json.dumps({"sources": srcs}), encoding="utf-8")
    monkeypatch.setattr(F.store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(F.store, "sources", lambda slug: srcs)
    monkeypatch.setattr(F.store, "ROOT", tmp_path)


def test_an_answer_for_the_barred_source_closes_a_finding_about_it(tmp_path, monkeypatch):
    _issue(tmp_path, monkeypatch)
    a = F.attestation_for("x", {"attributed_to": "The Guideline, version 6.2026",
                                "figure": "HR 0.56 (0.45–0.70)"})
    assert a and a["qid"] == "S001-01" and a["on"] == "2026-08-29"


def test_a_finding_about_the_barred_source_that_no_answer_covers_goes_to_the_operator(tmp_path, monkeypatch):
    _issue(tmp_path, monkeypatch)
    assert F.attestation_for("x", {"attributed_to": "The Guideline, version 6.2026",
                                   "figure": "HR 0.61 (0.47–0.80)"}) is None


def test_an_answer_never_closes_a_finding_about_a_different_source(tmp_path, monkeypatch):
    """The safety property: S001-01 happens to carry 0.56 (0.45-0.70); a finding
    attributed to the NMA that disputes the same figure must NOT close."""
    _issue(tmp_path, monkeypatch)
    assert F.attestation_for("x", {"attributed_to": "A network meta-analysis. Sci Rep 2024",
                                   "figure": "HR 0.56 (0.45–0.70)"}) is None


def test_a_withdrawn_question_is_not_an_attestation(tmp_path, monkeypatch):
    _issue(tmp_path, monkeypatch)
    assert [a["qid"] for a in F.attestations("x")] == ["S001-01"]


def test_a_source_that_is_held_is_not_barred_even_if_licence_flagged(tmp_path, monkeypatch):
    _issue(tmp_path, monkeypatch)
    srcs = F.store.sources("x")
    srcs[0]["access"]["state"] = "full_text_held"
    assert F.barred_sources("x") == {}
