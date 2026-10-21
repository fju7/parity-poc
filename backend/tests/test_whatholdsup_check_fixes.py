"""2026-10-18: three check fixes found by deskilling batch 5. Fixtures only,
except the last test, which reads this repository's own git history.

  B22  the comparison is quotations.py's (quote marks fold silently, accents
       fold with an INFO note); a sentence with a <q> claims only the <q> words.
  B5   a span ending a sentence, before a new sentence, is not truncated.
  B24  record files are compared with HTML tags stripped; a commit message in
       main's history is a record ({commit, quote})."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


B = _load("bindings")
sys.path.insert(0, str(WHU))
import spancheck as SC  # noqa: E402

S043 = ('However, there is a distinct difference in study design between our study and the Budzyn study. '
        'We evaluated the effect of exposure to CADe "after" CADe was removed, whereas Budzyn et al. '
        'investigated how endoscopists perform non-CADe-assisted colonoscopy "while" they were exposed to CADe.')
S025 = ('This Perspective identifies a risk: that trainees who rely on AI during the early formative years of '
        'clinical education may fail to develop the foundational reasoning skills that safe, independent '
        'practice requires.')


@pytest.fixture
def held(monkeypatch):
    docs = {"S043": S043, "S025": S025}
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("f", docs[sid])] if sid in docs else [])
    monkeypatch.setattr(SC, "defective_renditions", lambda slug, sid: ([], None))
    return docs


def page(monkeypatch, html):
    # _marked_page caches by (slug, id(_page_html)); a freed lambda's id can be
    # reused by the next test's, which then read the previous test's page.
    monkeypatch.setattr(B, "_MARKED_CACHE", {})
    monkeypatch.setattr(B, "_page_html", lambda slug: html)


# --- B22 -------------------------------------------------------------------

def test_34dbcad2_shape_passes_with_the_accent_info(held, monkeypatch):
    page(monkeypatch, "<p>In their words: <q>We evaluated the effect of exposure to CADe &lsquo;after&rsquo; "
                      "CADe was removed, whereas Budzy&#324; et al. investigated how endoscopists perform</q></p>")
    row = {"sentence": "In their words: We evaluated the effect of exposure to CADe ‘after’ CADe was removed, "
                       "whereas Budzyń et al.", "source_id": "S043", "span": None}
    fl = B.b22_wording_claim(row, "t")
    assert [f["verdict"] for f in fl] == [B.ACCENT_INFO]
    assert B.CALIBRATION_SEVERITY[B.ACCENT_INFO] == B.INFO
    assert "Budzyń / Budzyn" in fl[0]["why"]


def test_quote_marks_alone_fold_silently(held, monkeypatch):
    page(monkeypatch, "<p>In their words: <q>We evaluated the effect of exposure to CADe &lsquo;after&rsquo; "
                      "CADe was removed</q></p>")
    row = {"sentence": "In their words: We evaluated the effect of exposure to CADe ‘after’ CADe was removed.",
           "source_id": "S043"}
    assert B.b22_wording_claim(row, "t") == []


def test_24bdc717_shape_the_lead_in_outside_the_q_is_not_claimed(held, monkeypatch):
    page(monkeypatch, "<p>In their words, trainees who rely on AI during the early formative years <q>may fail "
                      "to develop the foundational reasoning skills that safe, independent practice requires</q>.</p>")
    row = {"sentence": "In their words, trainees who rely on AI during the early formative years may fail to develop "
                       "the foundational reasoning skills that safe, independent practice requires .",
           "source_id": "S025"}
    assert B.b22_wording_claim(row, "t") == []


def test_a_real_misquote_inside_the_q_still_stops(held, monkeypatch):
    page(monkeypatch, "<p>In their words, trainees <q>will fail to develop the reasoning skills that practice "
                      "requires</q>.</p>")
    row = {"sentence": "In their words, trainees will fail to develop the reasoning skills that practice requires .",
           "source_id": "S025"}
    fl = B.b22_wording_claim(row, "t")
    assert [f["verdict"] for f in fl] == ["wording claim not in its source"]
    assert B.CALIBRATION_SEVERITY[fl[0]["verdict"]] == B.BAD


def test_without_a_q_the_old_clause_rule_still_applies(held, monkeypatch):
    page(monkeypatch, "<p>No quotation here.</p>")
    row = {"sentence": "In their words: trainees will certainly fail to develop anything.", "source_id": "S025"}
    assert [f["verdict"] for f in B.b22_wording_claim(row, "t")] == ["wording claim not in its source"]


# --- B5 --------------------------------------------------------------------

S031 = ("Effort decreased, and gaze remained more focused. This might be efficient but risks missing a polyp "
        "that is not captured by the system. To further analyze the changes in VGP, we generated a heatmap. "
        "Grade 3 diarrhea occurred in 8% to 20% of patients.")


@pytest.fixture
def s031(monkeypatch):
    monkeypatch.setattr(SC, "_text", lambda slug, sid: S031)
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("f", S031)])


def test_2a091110_shape_a_span_ending_a_sentence_is_complete(s031):
    ok, why = SC.b5_complete("This might be efficient but risks missing a polyp that is not captured by the system.",
                             "t", "S031")
    assert ok, why


def test_a_span_cut_mid_sentence_still_flags(s031):
    ok, why = SC.b5_complete("Grade 3 diarrhea occurred in 8%", "t", "S031")
    assert not ok and "to" in why


def test_a_span_that_ends_mid_sentence_after_earlier_full_stops_still_flags(s031):
    ok2, _ = SC.b5_complete("Effort decreased, and gaze remained more focused. This might be efficient but risks "
                            "missing a polyp that is not captured by the system. To further analyze the changes in "
                            "VGP, we generated a heatmap. Grade 3 diarrhea occurred in 8%", "t", "S031")
    assert not ok2


# --- B24 -------------------------------------------------------------------

CASE = "issues/WHU-099-test"
CORR = CASE + "/corrections.md"


@pytest.fixture
def repo(monkeypatch):
    files = {CORR: ("a" * 40, "The watch section says the date is when the evidence was read, "
                              "<q>not a guarantee that anyone has looked since</q>.")}
    commits = {"0ee52b8": ("0ee52b8" + "0" * 33, "Then lint_claims blocked it: nine names with no record\n"
                                                 "that anyone had opened the author list.\n")}
    monkeypatch.setattr(B, "_committed", lambda p: files.get(p))
    monkeypatch.setattr(B, "_commit_message", lambda c: commits.get(c))
    monkeypatch.setattr(B.store, "case_dir", lambda slug: B._repo_root() / CASE)
    return files, commits


def verdicts(entries):
    return [f["verdict"] for f in B.b24_records({"rests_on_record": entries}, "t")]


@pytest.mark.parametrize("quote", ["the date is when the evidence was read, not a guarantee that anyone has looked since",
                                   "the evidence was read, <q>not a guarantee that anyone has looked since</q>"])
def test_record_quotes_match_with_tags_stripped_on_either_side(repo, quote):
    assert verdicts([{"path": CORR, "quote": quote, "sha": "a" * 40}]) == []
    assert B.record_entry(CORR, quote, "t")["sha"] == "a" * 40


def test_a_commit_message_quote_binds_across_its_line_break(repo):
    q = "lint_claims blocked it: nine names with no record that anyone had opened the author list."
    assert verdicts([{"commit": "0ee52b8", "quote": q}]) == []
    assert B.commit_entry("0ee52b8", q)["commit"].startswith("0ee52b8")


def test_a_commit_quote_not_in_the_message_blocks(repo):
    assert verdicts([{"commit": "0ee52b8", "quote": "the papers were opened because we wanted to"}]) == [B.RECORD_GONE]
    with pytest.raises(ValueError):
        B.commit_entry("0ee52b8", "the papers were opened because we wanted to")


def test_a_commit_not_in_mains_history_blocks(repo):
    assert verdicts([{"commit": "deadbee", "quote": "anything at all here"}]) == [B.RECORD_GONE]
    with pytest.raises(ValueError):
        B.commit_entry("deadbee", "anything at all here")


def test_a_commit_binding_settles_rule_one_through_record_bound(repo):
    r = {"rests_on_record": [{"commit": "0ee52b8", "quote": "nine names with no record"}]}
    assert B.record_bound(r, "t")


def test_commit_message_reads_this_repository(tmp_path):
    """Real git: a commit on main resolves; a sha that is no commit does not."""
    if not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    B._COMMIT_CACHE.clear()
    got = B._commit_message("0ee52b8")
    assert got and "lint_claims blocked it" in got[1]
    assert B._commit_message("0000000000000000000000000000000000000001") is None


def test_a_less_than_sign_in_a_record_is_not_a_tag(repo):
    """'p<0.001' must not delete text up to the next '>' (CLAUDE.md's normalise hazard)."""
    files, _ = repo
    files[CORR] = ("b" * 40, "Significant at p<0.001 in the main analysis, and Age >60 years in the subgroup.")
    q = "Significant at p<0.001 in the main analysis, and Age >60 years in the subgroup."
    assert verdicts([{"path": CORR, "quote": q, "sha": "b" * 40}]) == []
    assert B._untagged("a <q>b</q> <em class=\"x\">c</em>") == "a b c"
