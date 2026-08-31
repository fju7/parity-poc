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


def test_cost_estimate_uses_the_carry_rate_and_may_exceed_the_last_run():
    """Replaces an assertion that was wrong, and cost real money to disprove.

    The first estimator counted unjudged SENTENCES and predicted $2.18. The run
    cost $5.20. Two separate mistakes:

    1. --since carries a verdict forward only when a claim's (figure, source)
       key matches exactly, so rewording a sentence breaks the key even when
       the figure did not move. Far more claims are re-checked than "new
       sentences" suggests. The last run's own carry rate is the honest
       predictor: 45 of 74 carried, so 29 fresh at $0.16 plus $1.03 of
       document-level roles is $5.67 — within 9% of the actual.

    2. The estimate was then CLAMPED to the last full run's price, on the
       reasoning that re-checking part of a page cannot cost more than
       re-checking all of it. True only if the page has not grown. Issue two
       had gained 155 sentences and the run extracted 92 claims where the old
       one found 74, so the clamp would have reported "at most $2.83" about a
       run that cost nearly double. A comforting number, and false.

    The estimate is now allowed to exceed its reference point and says so.
    """
    by = {"extract": {"usd": 0.18}, "advocate": {"usd": 0.22}, "inference": {"usd": 0.63}}
    by.update({f"source:{i}": {"usd": 0.16} for i in range(11)})
    report = {"usage": {"total": {"usd": 2.83}, "by_role": by},
              "claims": [{"claim": "c"}] * 74,
              "carried": ["45 claim verdict(s) carried forward"]}
    page = Path("/tmp/estimator-probe.html")
    page.write_text("<p>x</p>", encoding="utf-8")

    note = u.regate_cost(page, report, 28)
    assert "$5.67" in note, note
    assert "at most" not in note, "the false ceiling is back"
    assert "45 of 74 carried" in note, "the estimate must show what it rests on"
    assert "likely HIGHER" in note, "a grown page must be flagged as under-estimated"


def test_cost_note_is_absent_when_the_last_run_recorded_no_usage(tmp_path):
    """melanoma's report predates usage accounting. Say nothing rather than guess."""
    page = tmp_path / "p.html"
    page.write_text("<p>x</p>", encoding="utf-8")
    assert u.regate_cost(page, {"claims": []}, 10) == ""
