"""The two RUN.md checking scripts (study rulings 1 and 5, 2026-10-20).

applied_check (5a): every accepted ruling is on the page word for word,
normalised only as changecheck normalises. changecheck_coverage (9a): every
body sentence changed since the first full draft is in changecheck's read set.
Synthetic issues only.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_sc_t", WHU / ("%s.py" % name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AC = _load("applied_check")
CV = _load("changecheck_coverage")
import changecheck as C  # noqa: E402

OLD = "The trial proved that the diet cut weight by 2 kg."
NEW = "The trial found that the diet cut weight by 2 kg in 12 weeks."


def page(*sentences):
    return ("<html><body><p>An opening sentence stands here.</p><p>%s</p>"
            "<p>Diets differ in many ways.</p></body></html>" % " ".join(sentences))


def ruling(case, text, ruled_on=OLD, kind="conclusion", at="2026-10-21T10:00:00+00:00", log="rulings/rulings.jsonl",
           **extra):
    p = case / log
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"at": at, "by": "ruling model claude-opus-5-5", "ruling_kind": kind, "ruling": "amend",
           "text": text, "inputs": {"sentence": ruled_on}, **extra}
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


# --- 5a: the ruling-application check ----------------------------------------

def test_an_exact_match_passes(tmp_path):
    ruling(tmp_path, NEW)
    res = AC.check(tmp_path, page("Intro sentence here.", NEW))
    assert res["mismatches"] == [] and len(res["checked"]) == 1


def test_whitespace_is_normalised_as_changecheck_normalises_and_nothing_else(tmp_path):
    ruling(tmp_path, NEW)
    spaced = NEW.replace(" found ", "\n   found ")
    assert AC.check(tmp_path, page(spaced))["mismatches"] == []
    # a changed word is not normalised away
    ruling(tmp_path / "b", NEW)
    assert len(AC.check(tmp_path / "b", page(NEW.replace("found", "showed")))["mismatches"]) == 1


def test_a_mismatch_fails(tmp_path):
    ruling(tmp_path, NEW)
    res = AC.check(tmp_path, page(OLD))                       # not applied
    assert len(res["mismatches"]) == 1 and res["mismatches"][0]["missing"] == [NEW]


def test_a_cut_is_applied_only_when_the_sentence_is_gone(tmp_path):
    ruling(tmp_path, "")
    assert len(AC.check(tmp_path, page(OLD))["mismatches"]) == 1
    assert AC.check(tmp_path, page("Something else."))["mismatches"] == []


def test_a_superseded_ruling_is_not_expected_only_the_last_text_is(tmp_path):
    ruling(tmp_path, NEW, kind="gate", at="2026-10-21T10:00:00+00:00")
    final = "The trial found a 2 kg loss in 12 weeks."
    ruling(tmp_path, final, ruled_on=NEW, at="2026-10-22T10:00:00+00:00",
           log="audit/20261022T100000Z/rulings.jsonl")
    res = AC.check(tmp_path, page(final))
    assert res["mismatches"] == [] and len(res["superseded"]) == 1 and len(res["checked"]) == 1


def test_a_rejection_expects_nothing_and_a_left_for_person_wording_is_skipped(tmp_path):
    ruling(tmp_path, None, ruling="reject")
    ruling(tmp_path, "A card wording.", apply=False, log="audit/r1/rulings.jsonl")
    res = AC.check(tmp_path, page(OLD))
    assert res["mismatches"] == [] and len(res["skipped"]) == 1 and res["checked"] == []


# --- 9a: the changecheck coverage check ---------------------------------------

def reviews(*runs):
    return {"reviews": [dict(r) for r in runs]}


def test_every_changed_sentence_read_passes():
    first, now = page(OLD), page(NEW)
    sent, _ = C.changed(first, now)
    res = CV.check(first, now, reviews({"read": [C.fingerprint(s) for s in sent], "model_read": True}))
    assert res["missed"] == [] and res["changed"] == 1


def test_an_unread_changed_sentence_fails():
    first = page(OLD)
    now = page(NEW, "A second new sentence was added.")
    res = CV.check(first, now, reviews({"read": [C.fingerprint(NEW)], "model_read": True}))
    assert res["missed"] == ["A second new sentence was added."]


def test_the_read_set_is_the_union_across_runs_and_a_blind_run_counts_for_nothing():
    first = page(OLD)
    now = page(NEW, "A second new sentence was added.")
    runs = reviews({"read": [C.fingerprint(NEW)], "model_read": True},
                   {"read": [C.fingerprint("A second new sentence was added.")], "model_read": False},
                   {"changed": 3})                                    # before `read` existed
    res = CV.check(first, now, runs)
    assert res["missed"] == ["A second new sentence was added."] and res["runs_without_a_read_set"] == 2
    runs["reviews"].append({"read": [C.fingerprint("A second new sentence was added.")], "model_read": True})
    assert CV.check(first, now, runs)["missed"] == []


def test_changecheck_records_what_it_read(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "record_path", lambda slug: tmp_path / "change-reviews.json")
    C.save_review("x", page(NEW), "abc", 1, [], [], read=[NEW], model_read=True)
    r = json.loads((tmp_path / "change-reviews.json").read_text())["reviews"][0]
    assert r["read"] == [C.fingerprint(NEW)] and r["model_read"] is True and NEW not in json.dumps(r)


# --- withdrawn audit runs (2026-10-20) --------------------------------------------

def _manifest(case, run, **extra):
    d = case / "audit" / run
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps({"status": "complete", **extra}))
    return d


def test_rulings_from_a_withdrawn_run_are_not_expected_on_the_page(tmp_path):
    A = _load("audit_stage")
    ruling(tmp_path, NEW, log="audit/20261020T173234Z/rulings.jsonl")
    d = _manifest(tmp_path, "20261020T173234Z")
    assert len(AC.check(tmp_path, page(OLD))["mismatches"]) == 1        # expected, and not applied
    w = A.withdraw(d, "documents delivered empty (GAP-015)", on="2026-10-20")
    assert w["reason"] == "documents delivered empty (GAP-015)" and w["on"] == "2026-10-20"
    assert w["reasons"] == [{"reason": "documents delivered empty (GAP-015)", "on": "2026-10-20"}]
    res = AC.check(tmp_path, page(OLD))
    assert res["mismatches"] == [] and res["checked"] == []             # the withdrawn run is not read


def test_a_withdrawal_needs_a_reason_and_a_withdrawn_run_is_never_the_latest(tmp_path, monkeypatch):
    A = _load("audit_stage")
    old = _manifest(tmp_path, "20261020T100000Z")
    new = _manifest(tmp_path, "20261020T173234Z")
    monkeypatch.setattr(A, "audit_root", lambda slug: tmp_path / "audit")
    assert A.latest_run("x") == new
    with pytest.raises(ValueError):
        A.withdraw(new, "  ")
    A.withdraw(new, "documents delivered empty (GAP-015)")
    assert A.latest_run("x") == old


def test_a_second_withdrawal_appends_its_reason_and_keeps_the_first(tmp_path):
    A = _load("audit_stage")
    d = _manifest(tmp_path, "20261020T173234Z")
    A.withdraw(d, "documents delivered empty (GAP-015)", on="2026-10-20")
    w = A.withdraw(d, "made before ruling payloads carried context (0b39fb3)", on="2026-10-21")
    assert w["reasons"] == [{"reason": "documents delivered empty (GAP-015)", "on": "2026-10-20"},
                            {"reason": "made before ruling payloads carried context (0b39fb3)",
                             "on": "2026-10-21"}]
    assert w["reason"].startswith("made before") and A.is_withdrawn(d) == w


def test_a_withdrawal_written_before_the_list_keeps_its_reason(tmp_path):
    A = _load("audit_stage")
    d = _manifest(tmp_path, "r", withdrawn={"reason": "first", "on": "2026-10-20"})
    w = A.withdraw(d, "second", on="2026-10-20")
    assert [r["reason"] for r in w["reasons"]] == ["first", "second"]


# --- GAP-016: a ruling that removes a term a later sentence relies on ------------

INTRO_OLD = "In the UPDATE trial, 20 adults ate both diets for two weeks."
INTRO_NEW = "In the trial, 20 adults ate both diets for two weeks."
LATER = "The UPDATE authors report that energy intake rose."


def test_the_update_case_is_found(tmp_path):
    ruling(tmp_path, INTRO_NEW, ruled_on=INTRO_OLD)
    found = AC.dangling(tmp_path, page(INTRO_NEW, LATER))
    assert [(f["term"], f["later_sentence"]) for f in found] == [("UPDATE", LATER)]
    assert found[0]["applied_sentence"] == INTRO_NEW


def test_a_term_still_introduced_earlier_is_not_dangling(tmp_path):
    ruling(tmp_path, INTRO_NEW, ruled_on=INTRO_OLD)
    assert AC.dangling(tmp_path, page("The UPDATE trial was a crossover study.", INTRO_NEW, LATER)) == []


def test_a_term_used_nowhere_later_is_not_dangling_and_a_cut_counts(tmp_path):
    ruling(tmp_path, INTRO_NEW, ruled_on=INTRO_OLD)
    assert AC.dangling(tmp_path, page(INTRO_NEW, "The authors report that energy intake rose.")) == []
    ruling(tmp_path / "cut", "", ruled_on=INTRO_OLD)
    found = AC.dangling(tmp_path / "cut", page(LATER))
    assert [f["term"] for f in found] == ["UPDATE"] and found[0]["applied_sentence"] == "(cut)"


def test_terms_are_acronyms_short_forms_and_names_not_sentence_starts():
    assert AC.terms("The UPDATE trial (UPF) was run by Hall and Monteiro in NOVA group 4.") == \
        {"UPDATE", "UPF", "NOVA", "Hall", "Monteiro"}


# --- a sentence the audit cut after its final round (WHU-S04, 2026-10-23) ------

LAST = "The trial found a 2 kg loss in 12 weeks."
FINAL = "The trial found a 2 kg loss in 12 weeks, in one clinic."
RUN = "audit/20261023T022615Z"


def audit_cut(case, run=RUN, unit="u28", last_text=NEW, final=FINAL, **extra):
    """The audit's three rounds on one unit, the last accepted and then cut."""
    for n, (on, text) in enumerate([(OLD, NEW), (NEW, final)], 1):
        ruling(case, text, ruled_on=on, kind="audit", at="2026-10-23T02:2%d:00+00:00" % n,
               log=run + "/rulings.jsonl", unit=unit, round=n, ruling="amend" if n == 1 else "accept")
    rec = {"unit": unit, "part": "page", "original_sha": "x", "last_text": last_text,
           "rounds": [{"round": 1, "ruling": "amend", "text": NEW}, {"round": 2, "ruling": "accept", "text": final}],
           "why": "still failing after 2 read-and-correct rounds", **extra}
    p = case / run / "cuts.jsonl"
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


def test_a_sentence_the_audit_cut_and_the_page_left_out_is_cut_as_ruled(tmp_path):
    audit_cut(tmp_path)
    res = AC.check(tmp_path, page("Something else."))
    assert res["mismatches"] == [] and res["checked"] == []
    assert [(c["unit"], c["expected"], c["cut"]) for c in res["cut"]] == [("u28", "cut as ruled", RUN + "/cuts.jsonl:1")]
    assert len(res["superseded"]) == 1                          # round 1, by round 2


@pytest.mark.parametrize("on_page", [FINAL, NEW, OLD], ids=["last-ruled-text", "text-ruled-on", "original"])
def test_a_sentence_the_audit_cut_still_on_the_page_is_a_mismatch(tmp_path, on_page):
    audit_cut(tmp_path)
    res = AC.check(tmp_path, page(on_page))
    assert res["cut"] == [] and len(res["mismatches"]) == 1
    m = res["mismatches"][0]
    assert m["expected"] == "cut as ruled" and m["still_on_page"] == [on_page]


def test_an_accepted_text_with_no_cut_still_requires_that_text_on_the_page(tmp_path):
    audit_cut(tmp_path)
    (tmp_path / RUN / "cuts.jsonl").write_text("")              # the same rulings, and no cut
    res = AC.check(tmp_path, page("Something else."))
    assert res["cut"] == [] and len(res["mismatches"]) == 1 and res["mismatches"][0]["missing"] == [FINAL]
    assert AC.check(tmp_path, page(FINAL))["mismatches"] == []


@pytest.mark.parametrize("cut", [{"unit": "u29"}, {"last_text": OLD}, {"rounds": [{"text": "Another wording."}]},
                                 {"rounds": [{"text": ""}]}], ids=["unit", "ruled-on", "last-text", "ruled-cut"])
def test_a_cut_covers_only_its_own_unit_and_wording(tmp_path, cut):
    audit_cut(tmp_path)
    rec = dict({"unit": "u28", "last_text": NEW, "rounds": [{"text": FINAL}]}, **cut)
    (tmp_path / RUN / "cuts.jsonl").write_text(json.dumps(rec) + "\n")
    res = AC.check(tmp_path, page("Something else."))
    assert res["cut"] == [] and res["mismatches"][0]["missing"] == [FINAL]


def test_a_cut_covers_only_its_own_run(tmp_path):
    audit_cut(tmp_path)
    other = tmp_path / "audit" / "20261024T000000Z"
    other.mkdir()
    (tmp_path / RUN / "cuts.jsonl").rename(other / "cuts.jsonl")
    assert AC.check(tmp_path, page("Something else."))["cut"] == []


def test_a_left_for_person_cut_and_a_withdrawn_runs_cut_change_nothing(tmp_path):
    audit_cut(tmp_path / "a", left_for_person=True)
    assert AC.check(tmp_path / "a", page("Something else."))["mismatches"][0]["missing"] == [FINAL]
    audit_cut(tmp_path / "b")
    (tmp_path / "b" / RUN / "manifest.json").write_text(json.dumps({"withdrawn": {"reason": "test"}}))
    res = AC.check(tmp_path / "b", page("Something else."))
    assert res["cut"] == [] and res["mismatches"] == [] and res["checked"] == []
