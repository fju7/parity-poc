"""applied_check: several ADD decisions naming the same sentence.

Post-study, mid-rerun tool fix (2026-10-28). WHU-S01r/S07r had more than one
omission ruled ADD after one page sentence; applied_check asked each ADD's first
sentence to be directly after that sentence, which at most one of them can be.

Now: together they sit immediately after it as one contiguous run, each ADD
whole and in its own order, the ADDs in any order among themselves. Anything
else is still a mismatch.

The ADD decisions and ruling records are made by the real omission ruling
(ruling.rule_omissions, a fake model answering from its prompt, as in
test_whatholdsup_fix2_applied.py); only the page is arranged here.

COUNTERFACTUAL. Route a group through the one-ADD branch (`if len(group) > 1`
-> `if False`) and t_both_orders goes red; let _tiles ignore the anchor
(`_fp(s) == anchor and` removed) and t_not_after_the_anchor goes red.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import test_whatholdsup_fix2_ruling as T  # noqa: E402

spec = importlib.util.spec_from_file_location("applied_check_multi_t", WHU / "applied_check.py")
AC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AC)

SECOND = "Some changes could lead to induced demand (medium confidence)."


def page(sentences):
    return "<html><body>%s</body></html>" % "".join("<p>%s</p>" % s for s in sentences)


def _two(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED), T._obj(SECOND)])
    ds = T._run(tmp_path, T.Fake(T.ADD))
    adds = [d for d in ds if d["outcome"] == "ADD"]
    assert len(adds) == 2 and {d["insert_after"] for d in adds} == {T.PAGE[1]}
    return [d["text"] for d in adds]


def test_both_orders_directly_after_the_anchor_are_applied(tmp_path, monkeypatch):
    a, b = _two(tmp_path, monkeypatch)
    for run in ([a, b], [b, a]):
        res = AC.check(tmp_path, page(T.PAGE[:2] + run + T.PAGE[2:]))
        assert res["mismatches"] == [] and len(res["inserted"]) == 2, res["mismatches"]


def test_a_gap_in_the_run_is_a_mismatch(tmp_path, monkeypatch):
    a, b = _two(tmp_path, monkeypatch)
    res = AC.check(tmp_path, page(T.PAGE[:2] + [a, T.PAGE[2], b] + T.PAGE[3:]))
    assert len(res["mismatches"]) == 2 and all(m.get("misplaced") for m in res["mismatches"])


def test_not_after_the_anchor_is_a_mismatch(tmp_path, monkeypatch):
    a, b = _two(tmp_path, monkeypatch)
    res = AC.check(tmp_path, page(T.PAGE[:3] + [a, b] + T.PAGE[3:]))
    assert len(res["mismatches"]) == 2 and all(m.get("misplaced") for m in res["mismatches"])


def test_one_missing_is_still_missing(tmp_path, monkeypatch):
    a, _b = _two(tmp_path, monkeypatch)
    res = AC.check(tmp_path, page(T.PAGE[:2] + [a] + T.PAGE[2:]))
    assert [m for m in res["mismatches"] if m.get("missing")]


def test_tiles_unit():
    fp = AC._fp
    pg = ["x", "anchor", "a1", "a2", "b1", "y"]
    assert AC._tiles(pg, fp("anchor"), [["b1"], ["a1", "a2"]])
    assert not AC._tiles(pg, fp("anchor"), [["a2", "a1"], ["b1"]])   # an ADD's own order kept
    assert not AC._tiles(pg, fp("x"), [["a1", "a2"], ["b1"]])        # not immediately after
    assert not AC._tiles(["anchor", "a1"], fp("anchor"), [["a1"], ["b1"]])
