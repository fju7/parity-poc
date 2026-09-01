"""Ask the registry before asking a model, and prove the model was not asked.

The 2026-08-31 page gate cost $5.70. Its most expensive line:

    source:HARMONIA — ClinicalTrials.gov    $0.87   253,272 tok   9 searches

Nine web searches and eighty-seven cents to establish that HARMONIA opened in
March 2022, terminated, and enrolled 61 patients -- three structured fields the
ClinicalTrials.gov API returns in under a second, and which registry_facts.py
had already confirmed on the board BEFORE the run began. The deterministic tier
was overturning the model's verdict AFTER the spend.

registry_figures.py's docstring had said, since the day it was written, that it
"runs BEFORE the SOURCE role, settles what it can, and is both cheaper and more
accurate than the thing it short-circuits". It ran in the preflight, which is a
different program. The sentence described an intention.

These tests are about the two ways this could go wrong: the model being asked
anyway (no saving), and the claim disappearing (a report that says less than it
knows).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "fc_settle", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
fc = importlib.util.module_from_spec(spec)
sys.modules["fc_settle"] = fc
spec.loader.exec_module(fc)


class FakeSettler:
    """Settles exactly the claims whose figure contains a marked number."""
    error = None

    def __init__(self, settle_ids=()):
        self.settle_ids = set(settle_ids)

    def settles(self, figure="", quote="", attributed_to=""):
        for i in self.settle_ids:
            if i in (figure or "") or i in (quote or ""):
                return "every trial fact in this claim is a structured field"
        return None

    def summary(self):
        return "fake"


class BrokenSettler:
    error = "RuntimeError: the registry did not answer"

    def settles(self, figure="", quote="", attributed_to=""):  # pragma: no cover
        raise AssertionError("must not be consulted when it failed to load")

    def summary(self):
        return "broken"


@pytest.fixture
def no_model(monkeypatch):
    """Any model call is a test failure unless the test allows it."""
    calls = []

    def spy(*_a, **kw):
        calls.append(kw.get("label", "?"))
        return [{"id": c["id"], "verdict": "NOT_FOUND"} for c in []] or []
    monkeypatch.setattr(fc, "call", spy)
    return calls


CLAIMS = [
    {"id": "c1", "figure": "HARMONIA-FACT", "claim": "HARMONIA terminated",
     "attributed_to": "HARMONIA — ClinicalTrials.gov"},
    {"id": "c2", "figure": "HARMONIA-FACT", "claim": "61 patients enrolled",
     "attributed_to": "HARMONIA — ClinicalTrials.gov"},
    {"id": "c3", "figure": "category 1", "claim": "NCCN assigns category 1",
     "attributed_to": "NCCN guideline"},
]


def test_a_source_whose_every_claim_is_settled_is_never_asked(no_model):
    """The whole point. HARMONIA's group empties, so no API call is made for
    it -- that is the $0.87 and the nine searches, not spent."""
    v = fc.audit_sources(CLAIMS, "draft", FakeSettler({"HARMONIA-FACT"}))
    assert "source:HARMONIA — ClinicalTrials.gov"[:37] not in "".join(no_model)
    assert not any("HARMONIA" in label for label in no_model), no_model
    assert any("NCCN" in label for label in no_model), no_model


def test_a_settled_claim_still_gets_a_verdict_and_its_evidence(no_model):
    """A settled claim is not a skipped claim.

    If it vanished, the report would say less than it knows -- the failure mode
    of every optimisation in this pipeline.
    """
    v = fc.audit_sources(CLAIMS, "draft", FakeSettler({"HARMONIA-FACT"}))
    for cid in ("c1", "c2"):
        assert v[cid]["verdict"] == "VERIFIED"
        assert v[cid]["settled_by"] == "registry"
        assert "ClinicalTrials.gov" in v[cid]["actual_source"]
        assert "nothing was spent" in v[cid]["note"]


def test_a_claim_it_cannot_settle_goes_to_the_model_unchanged(no_model):
    v = fc.audit_sources(CLAIMS, "draft", FakeSettler({"HARMONIA-FACT"}))
    assert "c3" not in v or v["c3"].get("settled_by") != "registry"
    assert any("NCCN" in label for label in no_model)


def test_no_settler_behaves_exactly_as_before(no_model):
    fc.audit_sources(CLAIMS, "draft", None)
    assert len(no_model) == 2          # both groups asked, nothing settled


def test_a_settler_that_failed_to_load_is_loud_and_settles_nothing(no_model, capsys):
    """A pre-check that fails silently looks exactly like a registry with
    nothing to say, and the run buys what it could have had for free while
    reporting that it checked."""
    fc.audit_sources(CLAIMS, "draft", BrokenSettler())
    out = capsys.readouterr().out
    assert "registry pre-check did not run" in out
    assert len(no_model) == 2          # everything still checked, nothing skipped


def test_it_never_settles_a_claim_the_registry_is_silent_on(no_model):
    fc.audit_sources(CLAIMS, "draft", FakeSettler(set()))
    assert len(no_model) == 2


# ---------------------------------------------------------------------------
# settling against the record the claim itself names
# ---------------------------------------------------------------------------
#
# The first version of Settler only checked figures that registry_figures had
# found on the PAGE -- and registry_figures only reads figures out of SHORT
# blocks carrying exactly one NCT, a scope rule it needs because it is
# attributing numbers found loose in prose.
#
# So on the run this was built for it settled 5 claims and saved $0.00: not one
# source group emptied. A claim reading "MONALEESA-7's ClinicalTrials.gov
# results posting gives p = 0.00973" still went to a model with web search,
# which could not reach the posting, and came back NOT_FOUND -- about a number
# sitting in the record the claim names.
#
# There is nothing to guess here. The gate has already recorded what each claim
# is attributed to, and the attribution carries the NCT. Checking the claim
# against THAT record settled 12 claims, emptied three source groups, and would
# have removed $1.57 of a $5.70 run -- 28% -- including every group that
# produced a false NOT_FOUND.

import json

RS = importlib.util.spec_from_file_location(
    "registry_settle",
    ROOT / "backend" / "scripts" / "whatholdsup" / "registry_settle.py")
rs = importlib.util.module_from_spec(RS)
RS.loader.exec_module(rs)

RECORD = json.dumps({
    "protocolSection": {"identificationModule": {
        "briefTitle": "Ribociclib vs. Palbociclib ...",
        "officialTitle": "A Phase III ... - HARMONIA Trial", "acronym": "HARMONIA"}},
    "resultsSection": {"x": "Cox Proportional Hazard 0.712 CI 0.535 to 0.948 p 0.00973"},
})
ATTR = "HARMONIA — ClinicalTrials.gov record. NCT05207709"


@pytest.fixture
def settler(monkeypatch):
    s = rs.Settler.__new__(rs.Settler)
    s.slug, s.numbers, s.facts, s.error = "t", set(), {}, None
    s._rfac = None
    fake = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("registry_figures", loader=None))
    fake.registry_text = lambda nct: RECORD if nct == "NCT05207709" else None
    import re as _re
    fake.numbers_in = lambda text: {("%g" % float(x)) for x in _re.findall(r"\d+\.\d+", text)}
    s._rfig = fake
    return s


def test_a_figure_in_the_named_record_is_settled(settler):
    why = settler.settles("HR 0.712 (95% CI 0.535-0.948)", "the Cox HR is 0.712", ATTR)
    assert why and "NCT05207709" in why


def test_one_wrong_digit_is_not_settled(settler):
    """All, not any. The saving is worth nothing if it launders a wrong figure
    past the only check that would have caught it."""
    assert settler.settles("HR 0.712 (95% CI 0.535-0.949)", "", ATTR) is None
    assert settler.settles("p = 0.00974", "", ATTR) is None


def test_a_registration_claim_is_settled_by_the_record_naming_the_trial(settler):
    why = settler.settles("NCT05207709", "HARMONIA is registered as NCT05207709.", ATTR)
    assert why and "names HARMONIA" in why


def test_a_registration_claim_for_the_wrong_trial_is_not_settled(settler):
    """This is the check that catches the error the page actually made on
    31 August: MONALEESA-7 cited with PALOMA-2's registry number."""
    assert settler.settles("NCT05207709", "PALOMA-9 is registered as NCT05207709.",
                           ATTR) is None


def test_an_attribution_with_no_registry_number_settles_nothing(settler):
    assert settler.settles("HR 0.712", "", "NCCN guideline v6.2026") is None


def test_an_attribution_naming_two_trials_is_ambiguous(settler):
    assert settler.settles("HR 0.712", "", "NCT05207709 and NCT02278120") is None


def test_a_record_that_cannot_be_fetched_settles_nothing(settler):
    """An unreachable record is not a record that disagrees, and it is not a
    record that agrees either."""
    assert settler.settles("HR 0.712", "", "X — NCT09999999") is None


# ---------------------------------------------------------------------------
# a guard that promises never to break a run has to mean every exit path
# ---------------------------------------------------------------------------

def test_the_settler_survives_a_systemexit_from_the_case_lookup():
    """SystemExit does not inherit from Exception.

    registry_figures.case_dir() raises SystemExit for an unknown slug. The
    first version of Settler caught `Exception`, so it did not catch that --
    and on 2026-09-01 a COST-SAVING pre-check killed the email gate outright,
    after that run had already paid for claim extraction. The saving cost more
    than it saved, in the most literal way available.
    """
    s = rs.Settler("no-such-issue-anywhere", "<p>nothing</p>")
    assert s.error and "SystemExit" in s.error
    assert s.settles("HR 0.712", "x", "y — NCT05207709") is None
    assert "did not run" in s.summary()


def test_the_gate_survives_a_settler_that_exits(monkeypatch, capsys):
    """And the caller must survive it too, loudly.

    This is a cost optimisation sitting in the middle of the only check that
    protects a reader. If it throws, the claim goes to the model and the run
    continues. It must never be the reason a gate run dies -- which is what it
    was, once, after the run had already been paid for.
    """
    class Exiter:
        error = None
        def settles(self, *_a, **_kw):
            raise SystemExit("no case directory")
        def summary(self):
            return "x"
    calls = []
    monkeypatch.setattr(fc, "call",
                        lambda *a, **kw: calls.append(kw.get("label")) or [])
    fc.audit_sources(CLAIMS, "draft", Exiter())          # must not raise
    assert len(calls) == 2, calls                        # everything still checked
    assert "registry pre-check failed" in capsys.readouterr().out


def test_an_email_draft_resolves_to_its_issue_slug():
    """site/whatholdsup/email/issue2-cdk46.html belongs to issues/WHU-002-cdk46.

    Every email gate run this project has done was recorded against an issue
    called "issue2-cdk46", so email spend never counted toward the $40
    per-issue cap. The cap was measuring less than it was believed to measure
    -- the exact failure the ledger exists to prevent.
    """
    assert fc.issue_slug_for("site/whatholdsup/email/issue2-cdk46.html") == "cdk46"
    assert fc.issue_slug_for("site/whatholdsup/cdk46.html") == "cdk46"
    assert fc.issue_slug_for("site/whatholdsup/email/issue1-melanoma.html") == "melanoma"
    assert fc.issue_slug_for("site/whatholdsup/deskilling.html") == "deskilling"


def test_an_unknown_draft_falls_back_to_its_stem_rather_than_guessing():
    assert fc.issue_slug_for("/tmp/something-else.html") == "something-else"
