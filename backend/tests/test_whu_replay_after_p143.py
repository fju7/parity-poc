"""Three defects the replay gate found after P141-P143 (2026-11-26), each fixed:

  * 02zc stopped at the belief step, "record changed outside the step that owns it": P142's re-render (the page says
    "We could not verify where this belief is published.") writes the page, which the belief step did not own;
  * 02za: the readers'-list line for declaration S003@6097-6230, quoting the unit as "K …", was bound to the first
    "K" of the document (offset 433), outside its unit -- so "sentences rest on received text" stopped on a span no
    stage received. A line's quotation is now located inside its own unit only; not there, it stays unbound;
  * 02za: "unread corrections noted on the page" demanded the correction note on readers'-list lines bound to S003 /
    S004. A declaration line says the page does NOT rely on the finding it quotes, and the note cannot be placed in
    that list: such lines are not claims bound to the source.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import bindings as B  # noqa: E402
import correction_notes as CN  # noqa: E402
from orch import writes as WR  # noqa: E402

HELD = "Author K. wrote. " + "x" * 80 + " K. , Jeffries , D. the junk unit. More text after."
A = HELD.index("K. , Jeffries")
KEY = "S003@%d-%d" % (A, A + len("K. , Jeffries , D. the junk unit."))
LINE = "Judged not material to this question: “K …” (Teacher professional development)."


def _bind(monkeypatch, key=KEY, line=LINE):
    import coverage_check as C
    import lean
    monkeypatch.setattr(lean, "enabled", lambda: True)
    monkeypatch.setattr(C, "declarations", lambda slug, held: [{"source": "S003", "key": key, "state": "not_material",
                                                               "sentence": line}])
    monkeypatch.setattr(B.store, "sources", lambda slug: [{"id": "S003", "access": {"held": {"sha256": "s"}}}])
    rows = {}
    done = B.bind_declaration_lines("x", rows, sentences=[line], held={"S003": HELD})
    return rows, done


def test_a_readers_line_is_bound_inside_its_own_unit_not_at_the_first_match(monkeypatch):
    assert HELD.index("K") < A                                      # the first "K" is outside the unit
    rows, done = _bind(monkeypatch)
    [row] = rows.values()
    assert done and row["offsets"][0] == A and row["declaration_key"] == KEY


def test_a_quotation_not_in_its_unit_is_left_unbound(monkeypatch):
    rows2, done2 = _bind(monkeypatch, key="S003@20-60")              # a unit of x's: "K" is not in it
    assert done2 == [] and rows2 == {}


def test_a_readers_line_carries_no_correction_note(tmp_path):
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S003", "access": {"state": "full_text_held"}, "correction_unreadable": {"line": "correction_unread"}}]}))
    (tmp_path / "bindings.json").write_text(json.dumps({"bindings": {
        "a": {"sentence": LINE, "source_id": "S003", "on_page": True, "origin": B.DECLARATION_LINE},
        "b": {"sentence": "The map finds most studies measured attendance.", "source_id": "S003", "on_page": True}}}))
    assert CN.noted_sentences(tmp_path) == {CN.norm("The map finds most studies measured attendance."): CN.NOTE}


def test_the_belief_step_owns_the_page_it_re_renders():
    allowed = WR.CODE_WRITES["belief"]
    for f in WR.PAGE + ("premise.json", "rulings/premise_checks.jsonl", "bindings.json"):
        assert f in allowed


def test_the_received_text_check_uses_the_bindings_own_offsets():
    import lean_reading as LR
    held = {"S003": HELD}
    mask = bytearray(len(HELD))
    for i in range(A, A + 30):
        mask[i] = 1                                                   # only the unit was received
    rows = {"r": {"on_page": True, "sentence": LINE, "source_id": "S003", "span": "K", "offsets": [A, A + 1]}}
    import lean_received as LRC
    assert LRC.FULL <= 1.0
    row = LR.rests_row(rows, held, {"S003": mask})
    assert row[1] != "BLOCKED", row
    rows["r"]["offsets"] = [0, 1]                                     # offsets that do not hold the span: search
    assert LR.rests_row(rows, held, {"S003": mask})[1] == "BLOCKED"


def test_only_the_ruled_unverified_sentence_is_exempt_from_the_unknowability_lint():
    import belief_claims as BC
    import lint_claims as LC
    assert LC.unknowability(BC.UNVERIFIED) == []
    assert LC.unknowability("We could not verify where this claim is published.") != []
    assert BC.UNVERIFIED in LC.RULED_SENTENCES
