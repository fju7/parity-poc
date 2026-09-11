"""A SERIOUS finding about a figure we hold arrives as a LEAD.

THE RUN THIS IS BUILT FROM
--------------------------
2026-09-11. Two paid runs of the fact-check gate, $6.40, five SERIOUS findings.
Four were false and were refuted by two documents held since 1 September --
S004 (the OS HR is 0.471, 95% CI 0.165 to 1.345) and S007 (the 0.425 row, under
the heading OS, on nine deaths). The gate reads the web and cannot open either.

THE FIFTH FINDING IS THE CONTROL AND IT MATTERS MORE THAN THE FOUR
-------------------------------------------------------------------
One of the five was GOOD: the two intervals the reader compared really were
from different analyses. A labeller that downgrades everything would "pass"
this file on the four and destroy the one finding worth having. So the good
finding is in the fixture, and the test asserts it is NOT downgraded.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"))
import reachability as R                                    # noqa: E402

FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "gate_findings_2026-09-11.json"
CASES = json.loads(FIX.read_text(encoding="utf-8"))["findings"]

# S004 and S007, the two documents that settle every false finding.
SETTLING = {
    "S004": "the OS HR (95% CI) was 0.471 (0.165 to 1.345). "
            "RFS HR 0.510 (95% CI, 0.294 to 0.887).",
    "S007": "OS Events 3.7 (4/107) 10.0 (5/50) HR 0.425 80% CI 0.179 to 1.004 "
            "95% CI 0.114 to 1.584. RFS HR 0.510 80% CI 0.351 to 0.743 "
            "95% CI 0.288 to 0.906.",
}


def _blob(c):
    return c["quote"] + " " + c["problem"]


def test_every_false_finding_is_downgraded_to_a_lead():
    for c in CASES:
        if c["truth"] != "false":
            continue
        hits = R.check("melanoma", _blob(c), SETTLING)
        assert hits, "no held figure matched: %s" % c["quote"][:70]
        assert R.label(hits, c["severity"]) == "LEAD", c["quote"][:70]


def test_the_good_finding_is_left_alone():
    """The control. Downgrading this one would be the real failure."""
    good = [c for c in CASES if c["truth"] == "good"]
    assert good, "the fixture must carry a finding that is NOT to be downgraded"
    for c in good:
        hits = R.check("melanoma", _blob(c), SETTLING)
        assert R.label(hits, c["severity"]) == "SERIOUS", (
            "a valid finding was downgraded: %s" % c["quote"][:70])


def test_a_lead_carries_the_quotation_that_settles_it():
    """A label is worth little; the settling sentence is the point."""
    c = CASES[0]
    hits = R.check("melanoma", _blob(c), SETTLING)
    assert any("0.471" in h["quote"] or "0.425" in h["quote"] for h in hits)
    assert all(h["source"] in SETTLING for h in hits)


def test_severities_below_serious_are_never_touched():
    c = CASES[0]
    hits = R.check("melanoma", _blob(c), SETTLING)
    assert R.label(hits, "MINOR") == "MINOR"


def test_no_held_figure_means_no_change():
    assert R.check("melanoma", "a sentence carrying no figures at all", SETTLING) == []
    assert R.label([], "SERIOUS") == "SERIOUS"
