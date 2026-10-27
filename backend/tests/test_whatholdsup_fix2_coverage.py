"""Fix 2, step 7: the coverage check and the readers' list (post-study, 2026-10-27).

docs/whu-fix2-omission-rulings-design.md section 3, as ruled on 27 October
(option 3: abstract conclusions whole; an assessment's statements and Executive
Summary paragraphs only where the page binds them, each in full; detected by
structure, never by title). Synthetic texts here; the study's held documents
in the replays, skipped where they are absent.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import bindings as B          # noqa: E402
import coverage_check as C    # noqa: E402
import omissions as O         # noqa: E402

# S08's layout, synthetic: a table of contents naming the Executive Summary,
# then the summary itself, paragraphs ending in their {section references},
# then the first numbered section. The title says nothing about a chapter.
CHAPTER = (
    "Cities, Settlements and Key Infrastructure Table of Contents Executive Summary \x08.......... 909 "
    "6.1 Introduction and Points of Departure \x08.......... 912 "
    "Cities, Settlements and Key Infrastructure \x08 Executive Summary "
    "In all cities and urban areas the risk from climate hazards has increased (high confidence1). "
    "Urban areas are now home to most of the world's people and most economic activity. {6.1; 6.2} "
    "Many more cities have developed adaptation plans, but only a limited number have been implemented "
    "(medium confidence). Many of these plans focus narrowly on climate risk reduction and miss co-benefits. "
    "Implementation is constrained by finance, capacity and competing priorities in many places. {6.3; 6.4} "
    "Zoning combined with other planning measures is more effective (high confidence). "
    "Land use rules alone rarely protect green cover where development pressure is high. {6.3.3.1} "
    "Some trailing text after the last reference that is not a paragraph at all and should be ignored. "
    "6.1 Introduction and Points of Departure The chapter assesses ...")
PARA2 = "Many more cities have developed adaptation plans, but only a limited number have been implemented"

SPM = " ".join(
    ["%s.%d Statement %s.%d says something about mitigation (high confidence). It adds a second point without a term. "
     "{1.1}" % (l, n, l, n) for l in "AB" for n in (1, 2, 3)] +
    ["C.8.2 \x07Changes in urban form could reduce emissions in developed countries (high confidence). "
     "Investments in public transport can further support the shift to less intensive modes (high confidence). "
     "Combinations of systemic changes may reduce demand for passenger and freight services (high confidence). "
     "Some of these changes could lead to induced demand (medium confidence). {5.3, 10.2}",
     "C.8.3 Electric vehicles offer the largest decarbonisation potential for land transport (high confidence). {10.4}"])
ABSTRACT = (
    "Background Some text about the question here for the reader to see. "
    "Synthesis of results The test made little to no difference to deaths at six months (high-certainty evidence). "
    "Time to treatment was shorter in one trial of the new test, by several days on average. "
    "Authors' conclusions The test makes little to no difference to all-cause mortality at six months. "
    "The test probably decreases the time taken to diagnose the disease and to start treatment. "
    "The test increases the risk of loss to follow-up compared with microscopy in adults. "
    "Plain language summary What is this review about and why does it matter for readers here?")


def _at(text, s):
    i = text.index(s)
    return [i, i + len(s)]


# ----------------------------------------------------------------- what is a unit

def test_an_assessment_chapter_is_found_by_its_structure_not_its_title():
    kind, groups = C.groups_of(CHAPTER)
    assert kind == "chapter" and len(groups) == 3                 # the trailing text is no paragraph
    assert not any("trailing text" in CHAPTER[g0:g1] for g0, g1, _ in groups)
    units = C.units_of({"id": "S003", "title": "Cities, Settlements and Key Infrastructure"}, CHAPTER,
                       [_at(CHAPTER, PARA2)])
    assert {u["section"] for u in units} == {"Executive Summary ¶2"}
    assert len(units) == 3                                        # the bound paragraph, IN FULL
    assert C.units_of({"id": "S003"}, CHAPTER, []) == []          # nothing bound, no units


def test_an_assessment_summary_gives_the_bound_statement_in_full():
    bound = [_at(SPM, "Changes in urban form could reduce emissions in developed countries")]
    units = C.units_of({"id": "S003", "title": "anything"}, SPM, bound)
    assert {u["section"] for u in units} == {"SPM C.8.2"}
    assert len(units) == 4                                        # every sentence, termed or not
    assert C.groups_of(SPM)[0] == "summary"


def test_too_few_numbered_statements_is_not_a_summary():
    assert C.groups_of("A.1 Something happened (high confidence). B.2 Another thing (low confidence).") == ("", [])


def test_an_abstract_gives_its_conclusions_whole_and_its_graded_results():
    units = C.units_of({"id": "S001"}, ABSTRACT, [])
    secs = [(u["section"], u["text"][:30]) for u in units]
    assert [s for s in secs if s[0] == "abstract conclusions"] == [
        ("abstract conclusions", "The test makes little to no di"),
        ("abstract conclusions", "The test probably decreases th"),
        ("abstract conclusions", "The test increases the risk of")]
    assert [s for s in secs if s[0] == "abstract results"] == [("abstract results", "Synthesis of results The test ")]


# ----------------------------------------------------------------- accounting

def test_used_added_declared_and_none():
    units = C.units_of({"id": "S001"}, ABSTRACT, [])
    rows = {"r1": {"on_page": True, "source_id": "S001",
                   "span": "makes little to no difference to all-cause mortality"}}
    held = {"S001": ABSTRACT}
    k_diag = C.unit_key([u for u in units if "diagnose" in u["text"]][0])
    loss = [u for u in units if "loss to follow-up" in u["text"]][0]
    om = {"omissions": [{"source": "S001", "at": loss["at"], "outcome": "ADD", "key": "x"}]}
    acc = {u["text"][:20]: u["state"] for u in C.account(units, rows, held, om,
                                                          {k_diag: {"state": "out_of_scope"}})}
    assert list(acc.values()) == ["none", "used", "out_of_scope", "added"]


# ----------------------------------------------------------------- the readers' list

def test_a_declaration_line_is_one_protected_sentence_even_when_it_quotes_a_finding():
    s = C.declaration_sentence("out_of_scope", C.short_span("We found, e.g. in three trials, that X rose. More."),
                               "S001", "about design, not effect. Extra")
    import source_ledger as L
    assert len(L.sentences(s)) == 1 and s.startswith("Outside this question: “")
    assert B.protected_kind(s) == "scope" and B.protected_kind(C.HEADING) == "scope"
    assert B.protected_kind("We found that X rose.") is None


@pytest.fixture
def case(tmp_path, monkeypatch):
    import premise as PM
    import source_store as store
    monkeypatch.setattr(store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(PM, "case_dir", lambda slug: tmp_path)
    (tmp_path / "issue.json").write_text(json.dumps({"question": "Does the test reduce deaths among adults tested?"}))
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [{"id": "S001", "title": "A review — 2025",
                                                                   "also_called": ["the 2025 review"]}]}))
    (tmp_path / "premise.json").write_text(json.dumps({"what_the_sources_show": {"sources": ["S001"]}}))
    return tmp_path


ROWS = {"r1": {"on_page": True, "source_id": "S001", "span": "makes little to no difference to all-cause mortality"}}
HELD = {"S001": ABSTRACT}
PAGE = ["The test makes little to no difference to all-cause mortality at six months, the review found."] + \
       ["Filler %d." % i for i in range(49)]


def _rows(case, page, **kw):
    return dict((r[0], r) for r in C.preflight_rows("x", rows=ROWS, held=HELD, page_sentences=page,
                                                    case=case, **kw))


def _declare_all(case, by="Claude Code"):
    units = C.units_of({"id": "S001"}, ABSTRACT, [])
    for u in units:
        if "makes little" not in u["text"]:
            C.declare("x", C.unit_key(u), "out_of_scope", "about speed, not deaths", by,
                      element="reduce deaths among adults", case=case)


def test_unaccounted_units_stop_and_the_row_states_its_limit(case):
    r = _rows(case, PAGE)[C.ROW_UNITS]
    assert r[1] == C.BAD and "with no state" in r[2] and "Known limit" in r[2]


def test_declared_units_pass_only_when_the_readers_list_is_on_the_page(case):
    _declare_all(case)
    rows = _rows(case, PAGE)
    assert rows[C.ROW_UNITS][1] == C.OK
    assert rows[C.ROW_LIST][1] == C.BAD and "not on the page word for word" in rows[C.ROW_LIST][2]
    decls = C.declarations("x", HELD, case)
    assert len(decls) == 3 and all("(the 2025 review)" in d["sentence"] for d in decls)
    page = PAGE + [C.HEADING] + [d["sentence"] for d in decls]
    assert _rows(case, page)[C.ROW_LIST][1] == C.OK
    # a line in the list with no declaration behind it
    stray = page + ["Outside this question: “Something nobody declared” (S001); because."]
    assert "no declaration behind it" in _rows(case, stray)[C.ROW_LIST][2]
    # the rendered HTML carries the heading and one paragraph per declaration
    html = C.render(decls)
    assert C.HEADING in html and html.count("<p>") == 4


def test_an_out_of_scope_declaration_must_name_the_question(case):
    u = [u for u in C.units_of({"id": "S001"}, ABSTRACT, []) if "diagnose" in u["text"]][0]
    C.declare("x", C.unit_key(u), "out_of_scope", "r", "Claude Code", element="the economics of testing", case=case)
    assert "name no words of the question" in _rows(case, PAGE)[C.ROW_UNITS][2]


def test_declarations_past_the_budget_need_a_person(case, tmp_path):
    _declare_all(case)
    decls = C.declarations("x", HELD, case)
    small = ["The test makes little to no difference to all-cause mortality at six months, the review found."] + \
            ["Filler %d." % i for i in range(9)]                    # 10 sentences: budget min(10, 2) = 2
    page = small + [C.HEADING] + [d["sentence"] for d in decls]
    r = _rows(case, page)[C.ROW_LIST]
    assert r[1] == C.BAD and "past the budget" in r[2]
    # signed by a person, with a committed acceptance line: it passes
    repo = tmp_path / "repo"
    repo.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
    git("init", "-q"); git("config", "user.email", "t@e.com"); git("config", "user.name", "t")
    (repo / "a.md").write_text("# a\nAccepted by Fred Ugast, 27 October 2026, stated in session\n")
    git("add", "a.md"); git("commit", "-q", "-m", "acceptance")
    doc = json.loads((case / C.RECORD).read_text())
    for k in list(doc["declarations"])[2:]:
        doc["declarations"][k].update(by="Fred Ugast", signature={"statement": "ok", "source": "a.md:2"})
    (case / C.RECORD).write_text(json.dumps(doc))
    assert _rows(case, page, root=repo)[C.ROW_LIST][1] == C.OK


def test_the_committed_record_holds_no_source_text(case):
    _declare_all(case)
    text = (case / C.RECORD).read_text()
    for s in ("probably decreases the time taken", "increases the risk of loss"):
        assert s not in text


# ----------------------------------------------------------------- replays on the study's documents

def _held(slug):
    import ruling as R
    rows_p = sorted((ROOT / "issues").glob("WHU-S0*-%s/bindings.json" % slug))
    if not rows_p:
        pytest.skip("the study's bindings are private and not here")
    held = R.held_texts(slug)
    if not held:
        pytest.skip("the held texts are not here")
    return held, B.load(slug)["bindings"]


def test_replay_s08_chapter_is_found_without_chapter_in_its_title():
    held, rows = _held("settlement-planning-climate-resilience")
    src = [s for s in C._sources("settlement-planning-climate-resilience") if s["id"] == "S003"][0]
    assert "chapter" not in (src.get("title") or "").lower()
    kind, groups = C.groups_of(held["S003"])
    assert kind == "chapter" and len(groups) >= 5
    units = C.units_of(src, held["S003"], C.bound_ranges(rows, held).get("S003"))
    assert units and all(u["section"].startswith("Executive Summary") for u in units)


def test_replay_s07_keeps_the_c82_catch():
    held, rows = _held("urban-form-transport-emissions")
    src = [s for s in C._sources("urban-form-transport-emissions") if s["id"] == "S003"][0]
    units = C.units_of(src, held["S003"], C.bound_ranges(rows, held).get("S003"))
    acc = C.account(units, rows, held, {"omissions": []}, {})
    c82 = [u for u in acc if u["section"] == "SPM C.8.2"]
    assert len([u for u in c82 if u["state"] == "used"]) >= 1
    assert len([u for u in c82 if u["state"] == "none"]) == 3     # the three sentences the page left out


def test_replay_s01_abstract_units_include_unaccounted_conclusions():
    held, rows = _held("tb-dna-testing")
    src = [s for s in C._sources("tb-dna-testing") if s["id"] == "S001"][0]
    acc = C.account(C.units_of(src, held["S001"], []), rows, held, {"omissions": []}, {})
    assert len([u for u in acc if u["section"] == "abstract conclusions" and u["state"] == "none"]) >= 2
