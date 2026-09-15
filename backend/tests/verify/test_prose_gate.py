"""The four Signal prose surfaces, gated at their store boundary.

Cases are taken from the frozen mmr-vaccine-autism record as measured on
2026-09-15 (docs/shared-assertion-policy-phase-a-inventory.md). Offline: the
Supabase client is a stub that returns the sources the real run would fetch.
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "scripts", "signal"))

import prose_gate as pg  # noqa: E402


class _Q:
    def __init__(self, data): self.data = data
    def select(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def execute(self): return self


class _SB:
    """claim c1 -> source s1; c2 -> s2."""
    def table(self, name):
        if name == "signal_claim_sources":
            return _Q([{"claim_id": "c1", "source_id": "s1"}, {"claim_id": "c2", "source_id": "s2"}, {"claim_id": "c3", "source_id": "s1"}])
        return _Q([{"id": "s1", "title": "Hviid 2019 Annals of Internal Medicine", "content_text": "657 461 children ... aHR 0.93 (95% CI 0.85 to 1.02) ... preterm birth or low birth weight"},
                   {"id": "s2", "title": "Madsen 2002 NEJM", "content_text": "relative risk 0.92 (95% CI 0.68 to 1.24) ... Denmark"}])


BATCH = [
    {"id": "c1", "claim_text": "The Hviid 2019 Danish cohort study found no increased autism risk in high-risk subgroups including children with preterm birth or low birth weight who received the MMR vaccine."},
    {"id": "c2", "claim_text": "The relative risk of autism in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.26), indicating no increased risk."},
    {"id": "c3", "claim_text": "Wakefield received £435,643 plus expenses from lawyers seeking to build a case against MMR vaccine manufacturers prior to publication of the 1998 Lancet study."},
]


def test_plain_summary_with_an_added_fact_is_refused_and_a_faithful_one_kept():
    summaries = [
        {"claim_id": "c1", "plain_summary": "The 2019 Danish cohort study examined whether children born preterm (before 37 weeks of pregnancy) or with low birth weight faced any higher autism risk from the MMR vaccine, and found they did not."},
        {"claim_id": "c2", "plain_summary": "A large Danish study calculated that MMR-vaccinated children had essentially the same risk of autism as unvaccinated children, a relative risk of 0.92."},
        {"claim_id": "c3", "plain_summary": "Before his 1998 study was published, Wakefield received £435,643 plus expenses from lawyers building a case against MMR vaccine manufacturers, one of two conflicts he never disclosed."},
    ]
    kept, verdicts = pg.gate_plain_summaries(_SB(), BATCH, summaries)
    kept_ids = [k["claim_id"] for k in kept]
    assert kept_ids == ["c2", "c3"], kept_ids
    v1 = next(v for v in verdicts if v["claim_id"] == "c1")
    assert any(f["text"] == "37" for f in v1["refused"])
    v3 = next(v for v in verdicts if v["claim_id"] == "c3")
    # "£435,643" binds (the json-escaping bug of 2026-09-15 is fixed); "two" is a paraphrase count -> flag
    assert v3["ok"] and any(f["kind"] == "words" for f in v3["flags"])


def test_plain_summary_with_a_currency_conversion_is_refused():
    summaries = [{"claim_id": "c3", "plain_summary": "Wakefield received £435,643 (roughly over half a million US dollars today) plus expenses from lawyers."}]
    kept, verdicts = pg.gate_plain_summaries(_SB(), BATCH, summaries)
    assert kept == [] and any(f["text"] in ("1000000", "half a million") or "1000000" in f["text"] for f in verdicts[0]["refused"])


def test_plain_summary_with_a_regulatory_status_word_not_in_the_claim_is_refused():
    batch = [{"id": "c9", "claim_text": "FDA product labeling for M-M-R II lists known adverse reactions but does not list autism."}]
    summaries = [{"claim_id": "c9", "plain_summary": "The FDA-approved label for M-M-R II lists side effects but has never listed autism."}]
    kept, verdicts = pg.gate_plain_summaries(_SB(), batch, summaries)
    assert kept == [] and any(f["kind"] == "fda_status" for f in verdicts[0]["refused"])


def test_consensus_prose_binds_to_its_claims_and_refuses_a_stray_body():
    claims = [{"claim_text": "Ten of the thirteen co-authors withdrew their names from the paper's interpretation in 2004."},
              {"claim_text": "The GMC found Wakefield guilty of serious professional misconduct in 2010."}]
    ok = pg.gate_consensus({"summary_text": "The co-authors' withdrawal in 2004 and the GMC finding in 2010 leave no live dispute.",
                            "arguments_for": "", "arguments_against": ""}, "retraction", claims)
    assert ok["ok"], ok
    bad = pg.gate_consensus({"summary_text": "The NCCN and the CDC have both weighed in; 41 of 50 states concur.",
                             "arguments_for": "", "arguments_against": ""}, "retraction", claims)
    assert not bad["ok"]
    kinds = {f["kind"] for f in bad["refused"]}
    assert "nccn" in kinds and "cdc" in kinds and any(f["text"] in ("41", "50") for f in bad["refused"])


def test_narrative_binds_to_the_handed_stats_and_refuses_an_identifier():
    user_text = "Overall stats:\n  32 sources analyzed\n  128 claims extracted, 128 scored\n--- LARGE_SCALE ---\nTop claims:\n  [4.40 strong] A study of 95,727 children found no association."
    good = pg.gate_narrative({"overall_summary": "After analyzing 32 sources and 128 claims, including a study of nearly 96,000 children, the picture is clear.",
                              "category_takeaways": {"large_scale": "Bottom line: the 95,727-child study found no association."}}, user_text)
    assert good["ok"], good
    bad = pg.gate_narrative({"overall_summary": "See doi:10.1001/jama.2015.3077 and PMID 25898051 for the sibling study.",
                             "category_takeaways": {}}, user_text)
    assert not bad["ok"] and {f["kind"] for f in bad["refused"]} >= {"doi", "pmid"}


def test_glossary_definition_may_not_add_a_figure():
    text = "The relative risk was 0.92. Case-control studies compare groups."
    ok = pg.gate_glossary({"relative risk": "how much more or less likely an outcome is in one group than another; here 0.92"}, text)
    assert ok["ok"]
    bad = pg.gate_glossary({"case-control study": "a design used in about 40% of vaccine safety research"}, text)
    assert not bad["ok"] and any("40" in f["text"] for f in bad["refused"])


def test_a_word_form_interval_the_model_computed_is_refused_not_flagged():
    """Migration 089 (2026-09-15): "six years before" was 2010 - 2004, and the
    2010 was never handed to the summariser. A counting word is a flag; a
    word-form figure followed by a unit is a figure, and must be in the held
    material."""
    batch = [{"id": "c4", "claim_text": "The Lancet issued a partial retraction of the interpretation in 2004."}]
    summaries = [{"claim_id": "c4", "plain_summary": "The journal partly withdrew the paper's interpretation in 2004, six years before it retracted the paper entirely."}]
    kept, verdicts = pg.gate_plain_summaries(_SB(), batch, summaries)
    assert kept == [] and any(f["text"] in ("six", "6") for f in verdicts[0]["refused"]), verdicts[0]
    # the bare counting word is still only a flag
    kept2, verdicts2 = pg.gate_plain_summaries(_SB(), batch, [{"claim_id": "c4", "plain_summary": "The journal partly withdrew the interpretation in 2004; six of the authors' claims were affected."}])
    assert kept2 and any(f["kind"] == "words" for f in verdicts2[0]["flags"])
