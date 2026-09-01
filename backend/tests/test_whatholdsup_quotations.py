"""The quotation matcher must catch an altered quotation.

A control nobody has seen fail is a control nobody knows works. The
counterexample hunter was built, wired in, and never once run against the page
it was built for -- it passed every gate by having no input. So this file does
not test that the matcher runs; it tests that it BLOCKS, on each of the four
ways a quotation goes wrong, and that it stays quiet on the one case that looks
like a defect and is not.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "backend" / "scripts" / "whatholdsup" / "quotations.py"

spec = importlib.util.spec_from_file_location("quotations", MOD)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

BLOCKED = "BLOCKED"

PAGE = """<html><body>
<p>The trial report says the
&ldquo;statistical comparison was made by 1-sided stratified log-rank test&rdquo;
and the authors note that
&ldquo;the final analysis was planned after at least 390 events&rdquo;.</p>
<p>Nobody serious argues that &ldquo;palbociclib does not work&rdquo; here.</p>
</body></html>"""


def _case(tmp_path, monkeypatch, quotations, sources=None):
    """Stand a fake issue directory up and point the module at it."""
    case = tmp_path / "WHU-999-testissue"
    case.mkdir()
    (case / "quotations.json").write_text(
        json.dumps({"quotations": quotations}), encoding="utf-8")
    (case / "sources.json").write_text(json.dumps({"sources": sources or [
        # full_text_held, not the old machine_read: on 2026-09-01 that state was
        # removed, because its only evidence was that a URL had appeared in a
        # gate report's citation list, and it licensed quotation.
        {"id": "S001", "title": "Trial report", "access": {"state": "full_text_held"}},
    ]}), encoding="utf-8")
    monkeypatch.setattr(q, "CASES", tmp_path)
    return case


def states(rows):
    return {name: state for name, state, _detail in rows}


def test_extracts_only_real_quotations():
    got = q.extract(PAGE)
    assert "statistical comparison was made by 1-sided stratified log-rank test" in got
    assert "palbociclib does not work" in got
    # "and the authors note that" is not quoted; nothing outside the marks.
    assert not any("authors note" in g for g in got)


def test_missing_file_blocks(tmp_path, monkeypatch):
    case = tmp_path / "WHU-999-testissue"
    case.mkdir()
    monkeypatch.setattr(q, "CASES", tmp_path)
    rows = q.preflight_rows("testissue", PAGE)
    assert rows[0][1] == BLOCKED
    assert "no quotations.json" in rows[0][2]


def test_unrecorded_quotation_blocks(tmp_path, monkeypatch):
    """The page quotes something the record does not mention at all."""
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "In this analysis the statistical comparison was made by 1-sided stratified log-rank test."},
    ])
    rows = q.preflight_rows("testissue", PAGE)
    assert states(rows)["every quotation is recorded"] == BLOCKED


def test_altered_quotation_blocks(tmp_path, monkeypatch):
    """THE CASE THIS FILE EXISTS FOR.

    The page says '1-sided'. The source says '2-sided'. Every other word
    matches, the source is real, it was opened, and the quotation is recorded.
    One digit is wrong and it reverses what the trial reported.
    """
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "The statistical comparison was made by 2-sided stratified log-rank test."},
        {"id": "Q-02", "quote": "the final analysis was planned after at least 390 events",
         "source_id": "S001",
         "verbatim": "the final analysis was planned after at least 390 events had occurred"},
        {"id": "Q-03", "quote": "palbociclib does not work",
         "kind": "rhetorical", "why": "our own framing of a position we then reject"},
    ])
    rows = q.preflight_rows("testissue", PAGE)
    st = states(rows)
    assert st["every quotation is recorded"] == "ok"
    assert st["quotations match the source"] == BLOCKED
    detail = [d for n, _s, d in rows if n == "quotations match the source"][0]
    assert "Q-01" in detail


def test_quotation_from_an_unopened_source_blocks(tmp_path, monkeypatch):
    """An accurate quotation from a source nobody opened is still not checked.

    source_ledger's rule, one level down: an unread source is not a source that
    agrees with us. If nobody opened it, the 'verbatim' field is somebody's
    recollection, and comparing a quotation against a recollection is not
    verification.
    """
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "The statistical comparison was made by 1-sided stratified log-rank test."},
        {"id": "Q-02", "quote": "the final analysis was planned after at least 390 events",
         "source_id": "S001",
         "verbatim": "the final analysis was planned after at least 390 events had occurred"},
        {"id": "Q-03", "quote": "palbociclib does not work",
         "kind": "rhetorical", "why": "our own framing"},
    ], sources=[{"id": "S001", "title": "Trial report", "access": {"state": "not_opened"}}])
    rows = q.preflight_rows("testissue", PAGE)
    assert states(rows)["quotation sources were opened"] == BLOCKED


def test_accurate_page_passes(tmp_path, monkeypatch):
    """The one case that must stay quiet.

    A check that fires on a correct page gets switched off, and then it protects
    nothing. Two accurate quotations from an opened source, one declared as the
    page's own voice.
    """
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "statistical comparison was made by 1-sided stratified log-rank test",
         "source_id": "S001",
         "verbatim": "In this analysis, the statistical comparison was made by 1-sided "
                     "stratified log-rank test, with the stratification factors as randomised."},
        {"id": "Q-02", "quote": "the final analysis was planned after at least 390 events",
         "source_id": "S001",
         "verbatim": "the final analysis was planned after at least 390 events had occurred"},
        {"id": "Q-03", "quote": "palbociclib does not work",
         "kind": "rhetorical", "why": "our own framing of a position the piece then rejects"},
    ])
    rows = q.preflight_rows("testissue", PAGE)
    assert BLOCKED not in states(rows).values(), rows


def test_curly_and_straight_quotes_are_the_same_quotation(tmp_path, monkeypatch):
    """Punctuation is not identity — the lesson counterexample._key was built on.

    The page renders a curly apostrophe; a passage pasted from a PDF carries a
    straight one. Two of nine claims on issue three were once unmatchable for
    exactly this, so it is asserted here rather than assumed.
    """
    page = "<p>&ldquo;the trial’s final analysis was planned after 390 events&rdquo;</p>"
    _case(tmp_path, monkeypatch, [
        {"id": "Q-01", "quote": "the trial's final analysis was planned after 390 events",
         "source_id": "S001",
         "verbatim": "the trial's final analysis was planned after 390 events had occurred"},
    ])
    rows = q.preflight_rows("testissue", page)
    assert BLOCKED not in states(rows).values(), rows


# ---------------------------------------------------------------------------
# the check must read its own repository before spending a person's afternoon
# ---------------------------------------------------------------------------
#
# On 2026-08-31 this check reported six quotations resting on a source nobody
# had opened, four of them from NCCN v6.2026 -- a document whose licence
# forbids putting it through any AI tool, so clearing them meant asking the
# operator to read a guideline again. He had already read it, on 29 August, and
# the wording of all four was in the repository: two in inherited.json, two in
# the advocate adjudication he had answered by name. The other two had been
# read by the gate and were in the gate's own report, VERIFIED.
#
# Seven attestations in three files, and a check written in a fourth asked for
# all of them again, because it was built from the page and never looked at the
# record. The cost of that falls on the one participant whose time cannot be
# bought back with a faster model.

def _repo_case(tmp_path, monkeypatch):
    case = tmp_path / "WHU-999-testissue"
    (case / "advocate").mkdir(parents=True)
    (case / "inherited.json").write_text(json.dumps({"claims": [
        {"id": "IC-002",
         "their_wording": "The NCCN Panel has included CDK4/6 inhibitors ... "
                          "Due to the clear OS benefit seen with ribociclib in "
                          "combination with AI, it is a category 1 recommendation.",
         "checked_by": "fred", "checked_on": "2026-08-29"},
    ]}), encoding="utf-8")
    (case / "advocate" / "2026-08-29-adjudication.md").write_text(
        "### S001-04 — SERIOUS\n"
        "ANSWERED BY: Fred Ugast\n"
        "ON:          2026-08-29\n"
        "ANSWER:      However, the CDK4/6 inhibitors have not been directly "
        "compared in clinical trials.\n", encoding="utf-8")
    (case / "advocate" / "2026-08-29-TEST-adjudication.md").write_text(
        "### FAKE\nANSWER:      a test fixture nobody answered\n", encoding="utf-8")
    monkeypatch.setattr(q, "CASES", tmp_path)
    return case


def test_an_answer_the_operator_already_gave_is_found_not_asked_for_again(
        tmp_path, monkeypatch):
    case = _repo_case(tmp_path, monkeypatch)
    on_file = q.attestations_on_file("testissue")
    hit = q.already_recorded(
        "Due to the clear OS benefit seen with ribociclib in combination with AI, "
        "it is a category 1 recommendation.", on_file)
    assert hit and hit["by"] == "fred", on_file
    assert "inherited.json" in hit["where"]

    hit2 = q.already_recorded("the CDK4/6 inhibitors have not been directly "
                              "compared in clinical trials", on_file)
    assert hit2 and hit2["by"] == "Fred Ugast", on_file
    assert "S001-04" in hit2["where"] and "2026-08-29" == hit2["on"]


def test_a_verified_gate_verdict_counts_as_an_attestation(tmp_path, monkeypatch):
    """The gate reaches routes this environment does not.

    ascopubs.org returns 403 to a direct fetch here; the gate's search route
    read the abstract on 29 August and recorded the Methods sentence verbatim.
    Recording that source as "nobody opened it" was the SOURCE role's own error
    -- one retrieval route failing is not the document being unreachable --
    committed by the checker, about its own pipeline's report.
    """
    _repo_case(tmp_path, monkeypatch)
    page = tmp_path / "p.html"
    page.write_text("<p>x</p>", encoding="utf-8")
    page.with_suffix(".html.gate.json").write_text(json.dumps({"verdicts": {
        "c73": {"verdict": "VERIFIED",
                "found_value": "OS was evaluated by Kaplan-Meier methods, and "
                               "statistical comparison was made by 1-sided stratified "
                               "log-rank test"},
        "c29": {"verdict": "NOT_FOUND", "found_value": "the structured page was not retrievable"},
    }}), encoding="utf-8")
    on_file = q.attestations_on_file("testissue", page)
    assert q.already_recorded("1-sided stratified log-rank test", on_file)
    # A NOT_FOUND verdict is not an attestation of anything.
    assert not q.already_recorded("the structured page was not retrievable", on_file)


def test_a_test_fixture_adjudication_is_not_an_attestation(tmp_path, monkeypatch):
    _repo_case(tmp_path, monkeypatch)
    on_file = q.attestations_on_file("testissue")
    assert not q.already_recorded("a test fixture nobody answered", on_file)


def test_it_still_blocks_and_does_not_fill_the_record_itself(tmp_path, monkeypatch):
    """A check that satisfies itself from its own fuzzy match is worth nothing.

    The value of `verbatim` is that a person or a named run put it there. So the
    finding still BLOCKS -- it just says where the answer already is, instead of
    sending someone back to a licensed document for a sentence transcribed two
    days ago.
    """
    case = _repo_case(tmp_path, monkeypatch)
    (case / "quotations.json").write_text(json.dumps({"quotations": [
        {"id": "Q-01",
         "quote": "the CDK4/6 inhibitors have not been directly compared in clinical trials",
         "source_id": "S001", "verbatim": "", "kind": ""},
    ]}), encoding="utf-8")
    (case / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "access": {"state": "human_read"}},
    ]}), encoding="utf-8")
    page_text = ("<p>The guideline records that &ldquo;the CDK4/6 inhibitors have not "
                 "been directly compared in clinical trials&rdquo;.</p>")
    rows = {n: (s, d) for n, s, d in q.preflight_rows("testissue", page_text)}

    assert rows["quotation sources were opened"][0] == BLOCKED
    state, detail = rows["wording already in the record"]
    assert state == BLOCKED
    assert "ALREADY ON FILE" in detail and "S001-04" in detail
    # and it did not write anything
    rec = json.loads((case / "quotations.json").read_text())
    assert rec["quotations"][0]["verbatim"] == ""
