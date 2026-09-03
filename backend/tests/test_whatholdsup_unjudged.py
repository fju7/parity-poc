"""Text added after the gate ran must not pass as judged.

Issue two's board read "state ok, every one of its 7 finding(s) is resolved"
while the live page carried 28 sentences of figures, trial names and registry
ids added two days after the gate report was written. An absence of findings
about a sentence is not a verdict about that sentence.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "unjudged", ROOT / "backend" / "scripts" / "whatholdsup" / "unjudged.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

BLOCKED, WARN, OK = "BLOCKED", "warn", "ok"

JUDGED = ("<p>The guideline lists all three drugs as preferred options for use.</p>"
          "<p>It grades the evidence behind one of them higher than the others.</p>")
CORRECTED = JUDGED + (
    "<p>Shaaban and colleagues randomised 116 patients to palbociclib or ribociclib.</p>"
    "<p>Clinical benefit at six months was 58.6% in both arms of that trial.</p>")
REWORDED = ("<p>The guideline lists all three drugs as preferred options for use.</p>"
            "<p>We have rewritten this sentence entirely and it says something else now.</p>")


def write(tmp_path, page_html, report_extra=None):
    page = tmp_path / "issue.html"
    page.write_text(page_html, encoding="utf-8")
    report = {"draft": str(page), "sha256": "0" * 64, "passed": True}
    report.update(report_extra or {})
    (tmp_path / "issue.html.gate.json").write_text(json.dumps(report), encoding="utf-8")
    return page


def states(rows):
    return {n: s for n, s, _d in rows}


def test_new_empirical_sentences_block(tmp_path):
    """THE CASE THIS FILE EXISTS FOR."""
    page = write(tmp_path, CORRECTED,
                 {"sentence_fingerprints": sorted(u.fingerprints(JUDGED))})
    rows = u.preflight_rows("x", page)
    assert states(rows)["empirical sentences never judged"] == BLOCKED
    detail = [d for n, _s, d in rows if n == "empirical sentences never judged"][0]
    assert "58.6%" in detail or "116 patients" in detail


def test_matching_sha_needs_no_comparison(tmp_path):
    page = tmp_path / "issue.html"
    page.write_text(CORRECTED, encoding="utf-8")
    (tmp_path / "issue.html.gate.json").write_text(json.dumps(
        {"sha256": hashlib.sha256(page.read_bytes()).hexdigest()}), encoding="utf-8")
    rows = u.preflight_rows("x", page)
    assert states(rows) == {"sentences the gate has seen": OK}


def test_new_prose_warns_but_does_not_block(tmp_path):
    """A check that blocks on a rewritten adjective gets bypassed."""
    page = write(tmp_path, JUDGED + "<p>This paragraph explains why that matters to a reader.</p>",
                 {"sentence_fingerprints": sorted(u.fingerprints(JUDGED))})
    rows = u.preflight_rows("x", page)
    assert states(rows)["sentences the gate has seen"] == WARN
    assert states(rows)["empirical sentences never judged"] == OK


def test_reworded_sentence_counts_as_unjudged(tmp_path):
    """A sentence whose words changed is a sentence no role read."""
    page = write(tmp_path, REWORDED,
                 {"sentence_fingerprints": sorted(u.fingerprints(JUDGED))})
    rows = u.preflight_rows("x", page)
    assert states(rows)["sentences the gate has seen"] == WARN


def test_punctuation_change_is_not_a_new_sentence(tmp_path):
    """Fixing a comma is not rewriting a claim."""
    tweaked = JUDGED.replace("preferred options for use.", "preferred options, for use.")
    page = write(tmp_path, tweaked,
                 {"sentence_fingerprints": sorted(u.fingerprints(JUDGED))})
    rows = u.preflight_rows("x", page)
    assert states(rows)["sentences the gate has seen"] == OK


def test_missing_report_blocks(tmp_path):
    page = tmp_path / "issue.html"
    page.write_text(CORRECTED, encoding="utf-8")
    rows = u.preflight_rows("x", page)
    assert states(rows)["sentences the gate has seen"] == BLOCKED


def test_vacuous_recovery_blocks(tmp_path, monkeypatch):
    """If the recovered draft is identical to the page, the comparison proves
    nothing — and unknown is not a pass. Issue three passed this way."""
    page = write(tmp_path, CORRECTED)          # no fingerprints -> git recovery
    monkeypatch.setattr(u, "judged_text", lambda _p, _r: (CORRECTED, "recovered from git at deadbeef"))
    rows = u.preflight_rows("x", page)
    assert states(rows)["sentences the gate has seen"] == BLOCKED
    assert "proves nothing" in rows[0][2]


BY = {"extract": {"usd": 0.20}, "advocate": {"usd": 0.38}, "inference": {"usd": 0.42}}
BY.update({"source:%d" % i: {"usd": 0.28} for i in range(15)})


def _report(claims, verdicts):
    return {"usage": {"total": {"usd": 5.20}, "by_role": BY},
            "claims": claims, "verdicts": verdicts}


def test_cost_counts_the_claims_that_can_carry(tmp_path):
    """Fourth version. Each earlier one estimated from a proxy for the carry.

      v1 counted changed SENTENCES: predicted $2.18, the run cost $5.20.
         Rewording breaks a claim's key even when its figure never moved.
      v2 used the last run's CARRY RATE: predicted $13.86 to re-check three
         corrected sentences. A carry rate is a property of how much changed,
         not of the page.
      v3 counted the claims whose FIGURE HAD GONE from the page, believing
         --since carries on a (figure, source) key. It does not: it carries a
         claim only when the prior verdict was VERIFIED. So every unverified
         claim re-ran and was priced at zero. On 3 September that produced
         "$2.90" for a run that cost $6.59.

    So count what CAN carry — VERIFIED, and its figure still present — and
    charge for the rest.
    """
    claims = [{"id": "c1", "figure": "HR 0.804 (0.637-1.015)"},   # verified, present
              {"id": "c2", "figure": "HR 0.92 (0.76-1.12)"},      # verified, gone
              {"id": "c3", "figure": "73.3 months"},              # NOT_FOUND
              {"id": "c4", "figure": ""}]                         # verified, no figure
    verdicts = {"c1": {"verdict": "VERIFIED"}, "c2": {"verdict": "VERIFIED"},
                "c3": {"verdict": "NOT_FOUND"}, "c4": {"verdict": "VERIFIED"}}
    page = tmp_path / "p.html"
    page.write_text("<p>The final analysis gives HR 0.804 (0.637-1.015).</p>",
                    encoding="utf-8")
    note = u.regate_cost(page, _report(claims, verdicts), 3)
    assert "2 claim(s) that cannot carry forward" in note, note
    assert "$1.56" in note, note                     # $1.00 of doc roles + 2 x $0.28
    assert "carry rate" not in note, "v2's rate-based reasoning is back"


def test_an_unverified_claim_is_priced_even_though_the_page_did_not_change(tmp_path):
    """The population v3 charged nothing for.

    Issue one's last report held 54 claims and 42 VERIFIED verdicts. Twelve
    were going to re-run before anybody touched a word of the page, and the
    estimate said the re-run was free.
    """
    claims = [{"id": "c%d" % i, "figure": "HR 0.804 (0.637-1.015)"} for i in range(10)]
    verdicts = {"c%d" % i: {"verdict": "VERIFIED" if i < 6 else "NOT_FOUND"}
                for i in range(10)}
    page = tmp_path / "p.html"
    page.write_text("<p>HR 0.804 (0.637-1.015)</p>", encoding="utf-8")
    note = u.regate_cost(page, _report(claims, verdicts), 0)
    assert "4 claim(s) that cannot carry forward" in note, note
    assert "4 of those were not VERIFIED" in note, note


def test_the_estimate_says_it_is_a_floor(tmp_path):
    """Extraction is a model call. It returned 54 claims one run and 59 the
    next on the same page, and the five it invented are not in the report to
    be counted. A number offered without that caveat gets budgeted against."""
    claims = [{"id": "c1", "figure": "HR 0.804 (0.637-1.015)"}]
    page = tmp_path / "p.html"
    page.write_text("<p>HR 0.804 (0.637-1.015)</p>", encoding="utf-8")
    note = u.regate_cost(page, _report(claims, {"c1": {"verdict": "VERIFIED"}}), 0)
    assert "AT LEAST" in note and "floor, not an estimate" in note, note


def test_cost_does_not_scale_with_unrelated_prose_changes(tmp_path):
    """Three corrected sentences must not be priced like a rewrite."""
    claims = [{"id": "c%d" % i, "figure": "HR 0.804 (0.637-1.015)"} for i in range(90)]
    verdicts = {"c%d" % i: {"verdict": "VERIFIED"} for i in range(90)}
    page = tmp_path / "p.html"
    page.write_text("<p>HR 0.804 (0.637-1.015) and a great deal of new prose.</p>",
                    encoding="utf-8")
    note = u.regate_cost(page, _report(claims, verdicts), 200)
    assert "1 claim(s)" in note, note


def test_cost_note_is_absent_when_the_last_run_recorded_no_usage(tmp_path):
    """melanoma's report predates usage accounting. Say nothing rather than guess."""
    page = tmp_path / "p.html"
    page.write_text("<p>x</p>", encoding="utf-8")
    assert u.regate_cost(page, {"claims": []}, 10) == ""
