"""'Could not be opened' is pinned on the source it names, not on the clause.

Adopted 2026-10-18. Deskilling's sentence "The meta-analysis they audit is Deng
et al., Computers & Education 2025;227:105224, which this page has not read:
its scope and effect size are given here as Weidlich and colleagues report
them" was reported as contradicting the ledger for S006 (Weidlich, held). The
clause carried both aliases, the first source in ledger order won, and the
citation's own semicolon had split "Deng et al." into another clause.

Now each inaccessibility phrase is attached to the nearest alias before it, or
to one immediately after it (before any colon, within FOLLOW_MAX characters)
when nothing precedes; a name the ledger does not carry leaves the sentence
unattributed rather than pinned on another source.

Fixtures only. Nothing here reads an issue directory or loads publish.py.
"""
import importlib.util
import sys
from pathlib import Path

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


L = _load("source_ledger")


def src(sid, aliases, state):
    return {"id": sid, "title": sid, "also_called": aliases, "access": {"state": state}}


WEIDLICH = src("S006", ["Weidlich and colleagues", "the JCAL critique"], "full_text_held")
DENG = src("S011", ["Deng et al.", "Deng and colleagues"], "blocked")
DENG_SENTENCE = ("The meta-analysis they audit is Deng et al., Computers & Education "
                 "2025;227:105224, which this page has not read: its scope and effect size "
                 "are given here as Weidlich and colleagues report them.")


def check(sentence, srcs):
    blocks, unattributed = L._inaccessibility("<p>%s</p>" % sentence, srcs)
    return [s["id"] for _sent, s, _st in blocks], unattributed


def test_the_deskilling_sentence_does_not_blame_weidlich():
    blocks, unattributed = check(DENG_SENTENCE, [WEIDLICH, DENG])
    assert blocks == [] and unattributed == []
    clause = [c for c in L._clauses(DENG_SENTENCE) if L.INACCESSIBLE.search(c)][0]
    assert [s["id"] for s in L._named_unread(clause, [WEIDLICH, DENG])] == ["S011"]


def test_the_citation_semicolon_does_not_split_the_clause():
    assert any("Deng et al." in c and "has not read" in c for c in L._clauses(DENG_SENTENCE))


def test_a_held_source_said_to_be_unread_still_blocks():
    blocks, _ = check("We could not open the JCAL critique.", [WEIDLICH, DENG])
    assert blocks == ["S006"]


def test_the_unread_source_named_second_in_the_clause():
    held_deng = src("S011", ["Deng et al."], "full_text_held")
    blocks, _ = check("Weidlich and colleagues audit Deng et al., which this page has not read.",
                      [WEIDLICH, held_deng])
    assert blocks == ["S011"]


def test_the_unread_source_named_first_in_the_clause():
    held_deng = src("S011", ["Deng et al."], "full_text_held")
    blocks, _ = check("Deng et al., which we could not open, is the meta-analysis Weidlich "
                      "and colleagues audit.", [WEIDLICH, held_deng])
    assert blocks == ["S011"]


def test_an_unrecorded_name_is_unattributed_not_pinned_on_another_source():
    blocks, unattributed = check(
        "The meta-analysis they audit is Smith et al., which this page has not read: its "
        "effect is given here as Weidlich and colleagues report it.", [WEIDLICH])
    assert blocks == [] and len(unattributed) == 1


def test_a_name_right_after_the_phrase_is_still_its_subject():
    palmares = src("S011", ["PALMARES-2"], "full_text_held")
    blocks, _ = check("We could not open PALMARES-2's declaration of interests.", [palmares])
    assert blocks == ["S011"]


def test_a_name_after_a_colon_is_not_the_subject():
    blocks, unattributed = check("This could not be opened: the JCAL critique says otherwise.",
                                 [WEIDLICH])
    assert blocks == [] and len(unattributed) == 1
