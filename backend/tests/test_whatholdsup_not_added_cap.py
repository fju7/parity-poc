"""not_added_cap: an omission not added because the page's budget was full.

Post-study, mid-rerun tool fix (2026-10-28). The re-runs reached the ADD and
declaration budgets, and there was no outcome that said so. not_added_cap is now
a recognised OMISSION outcome; it closes an advocate item only when its reason
names WHICH cap ("additions" or "declarations"), and the readers' list shows it
as "Not added: ... the page's limit for additions (or declarations) was reached".

The adjudication file is written by the real source_advocate.write_template and
read by the real _closed; the readers' list by the real coverage_check.declarations.

COUNTERFACTUAL. Drop the cap check in _closed (return True for every OMISSION
word) and t_needs_a_cap goes red; drop "not_added_cap" from OMISSION_WORDS and
t_closes goes red; drop the CAP_REASON substitution and t_readers_list goes red.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import bindings as B                         # noqa: E402
import coverage_check as C                   # noqa: E402
import judgements as J                       # noqa: E402
import omissions as O                        # noqa: E402
import source_advocate as SA                 # noqa: E402
import test_whatholdsup_fix2_ruling as T     # noqa: E402


def _item(tmp_path, monkeypatch, omission, did):
    adj = T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    text = adj.read_text()
    text = text.replace("OMISSION: \n", "OMISSION: %s\n" % omission, 1).replace("DID:      \n", "DID:      %s\n" % did, 1)
    adj.write_text(text)
    return "### " + T._chunk(adj, "S003-01")


@pytest.mark.parametrize("omission,did", [
    ("not_added_cap", "not added; the additions cap for this page was reached"),
    ("not_added_cap — declarations", "nothing added"),
])
def test_not_added_cap_naming_a_cap_closes_the_item(tmp_path, monkeypatch, omission, did):
    assert SA._closed(_item(tmp_path, monkeypatch, omission, did), "objections")


@pytest.mark.parametrize("did", ["not added; a budget was full",
                                 "not added; the additions and declarations caps were both full"])
def test_not_added_cap_needs_a_reason_naming_which_cap(tmp_path, monkeypatch, did):
    assert not SA._closed(_item(tmp_path, monkeypatch, "not_added_cap", did), "objections")


def test_other_outcomes_close_as_before(tmp_path, monkeypatch):
    assert SA._closed(_item(tmp_path, monkeypatch, "not_material", "listed for readers"), "objections")


def test_record_refuses_not_added_cap_without_a_cap():
    f = {"source": "S003", "at": [1, 2], "held_quote": "x"}
    with pytest.raises(ValueError):
        O.record(Path("/nonexistent"), f, outcome=O.NOT_ADDED_CAP, reason="a budget was full", by="p")


def test_readers_list_shows_which_limit_was_reached(tmp_path, monkeypatch):
    import source_store
    monkeypatch.setattr(source_store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S003", "title": "WGII Chapter 6"}])
    a = T.TEXT.index(T.OMITTED)
    f = {"source": "S003", "at": [a, a + len(T.OMITTED)], "held_quote": T.OMITTED, "origin": "S003-01"}
    O.record(tmp_path, f, outcome=O.NOT_ADDED_CAP, reason="Over the additions budget (3).", by="a person",
             held_text=T.TEXT)
    [d] = C.declarations("x", T.HELD, tmp_path)
    assert d["sentence"].startswith("Not added: “Investment in public transport")
    assert d["sentence"].endswith("; the page's limit for additions was reached.")
    # the line is protected as a scope statement, as the other readers' lines are
    assert B.protected_kind(d["sentence"], None) == "scope"
    # and it accounts for the unit and the judgement, as a declaration does
    unit = {"source": "S003", "at": f["at"], "section": "SPM A.1", "text": T.OMITTED}
    [u] = C.account([unit], {}, T.HELD, O.load(tmp_path), {})
    assert u["state"] == "not_added_cap"
    c = {"key": J.key("S003", f["at"]), "source": "S003", "at": f["at"]}
    assert J.state_of(c, T.TEXT, {}, T.HELD, {}, O.load(tmp_path), bound=[])[0] == "declared"


def test_declare_needs_a_cap_too(tmp_path):
    with pytest.raises(SystemExit):
        C.declare("x", "S003@1-2", "not_added_cap", "a budget was full", "a person", case=tmp_path)
    d = C.declare("x", "S003@1-2", "not_added_cap", "the declarations limit", "a person", case=tmp_path)
    assert d["state"] == "not_added_cap"
