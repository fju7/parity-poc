"""The anchor deletion cascade (advisor's ruling 1 on P152, 2026-11-26).

The fresh Q1-01 run (WHU-OT1-01b) stopped at `overstatement`: "applied_check found 1 mismatch(es)". An omission ADD
(S002@84643-84859, the HbA1c / LDL-cholesterol finding) had been inserted directly after "For decision-support tools
alone, it is not known whether ..."; the overstatement step's lean fail-safe then removed that sentence, and the
ADD was left "not directly after the sentence the decision named". Now, when any record removes a sentence, every
sentence an earlier ADD inserted after it is removed in the same step (no re-anchoring), and the finding becomes
code's own "Not added" line on the readers' list: found in our sources, not stated on this page.

The fixture is the run's own records (backend/tests/fixtures/whu_orch_01b/): the page, applied log, omissions.json
and rulings as they stood after the audit step (checkpoint 018-audit), and the fail-safe log the overstatement step
wrote.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
FIX = ROOT / "backend" / "tests" / "fixtures" / "whu_orch_01b"

import applied_check as AC          # noqa: E402
import coverage_check as C          # noqa: E402
import omissions as O               # noqa: E402
from orch import apply as AP        # noqa: E402
from orch.page import Page, fingerprint, norm  # noqa: E402

ANCHOR = ("For decision-support tools alone, it is not known whether they improve health workers' practice, and "
          "there is no clear pattern of effects on patients' health [2].")
KEY = "S002@84643-84859"
INSERTED = "For decision-support tools alone, the review also found that the intervention"


def _case(tmp_path: Path) -> tuple[Path, Page]:
    c = tmp_path / "case"
    (c / "rulings").mkdir(parents=True)
    (c / "orchestrator").mkdir()
    (c / "draft").mkdir()
    shutil.copy(FIX / "page.json", c / "draft" / "page.json")
    shutil.copy(FIX / "applied_before_overstatement.jsonl", c / "orchestrator" / "applied.jsonl")
    shutil.copy(FIX / "omissions.json", c / "omissions.json")
    shutil.copy(FIX / "rulings.jsonl", c / "rulings" / "rulings.jsonl")
    shutil.copy(FIX / "lean_removed.jsonl", c / "rulings" / "lean_removed.jsonl")
    return c, Page.load(c / "draft" / "page.json")


def _on(page: Page, start: str) -> bool:
    return any(norm(s).startswith(start) for s in page.sentences())


def test_the_fixture_is_what_01b_met():
    c_ins = [json.loads(l) for l in (FIX / "applied_before_overstatement.jsonl").read_text().splitlines() if l.strip()]
    ins = [r for r in c_ins if r.get("op") == "insert" and r["key"].startswith("add:%s:" % KEY)]
    assert len(ins) == 1 and ins[0]["anchor"] == fingerprint(ANCHOR) and ins[0]["new"].startswith(INSERTED)
    rows = [json.loads(l) for l in (FIX / "lean_removed.jsonl").read_text().splitlines() if l.strip()]
    assert any(norm(r.get("sentence") or "") == norm(ANCHOR) for r in rows)


def test_removing_the_anchor_removes_the_sentence_inserted_after_it(tmp_path):
    c, page = _case(tmp_path)
    assert _on(page, norm(ANCHOR)[:60]) and _on(page, INSERTED)
    ops = AP.apply_all(c, page)
    assert not _on(page, norm(ANCHOR)[:60]) and not _on(page, INSERTED)
    casc = [o for o in ops if o.get("cascade_of")]
    assert len(casc) == 1 and casc[0]["omission_key"] == KEY and casc[0]["op"] == "delete"
    assert casc[0]["anchor"] == fingerprint(ANCHOR) and casc[0]["source"] == "S002"
    logged = [json.loads(l) for l in (c / "orchestrator" / "applied.jsonl").read_text().splitlines() if l.strip()]
    assert any(r.get("cascade_of") and r["key"] == "cascade:" + casc[0]["cascade_of"] for r in logged)


def test_no_re_anchoring_and_the_rest_of_the_page_is_untouched(tmp_path):
    c, page = _case(tmp_path)
    before = list(page.sentences())
    ops = AP.apply_all(c, page)
    gone = {norm(o["old"]) for o in ops if o["op"] == "delete"}
    assert [s for s in before if norm(s) not in gone] == list(page.sentences())


def test_the_finding_becomes_a_not_added_line_and_applied_check_agrees(tmp_path):
    c, page = _case(tmp_path)
    AP.apply_all(c, page)
    raw = {e["key"]: e for e in O.load(c, raw=True)["omissions"]}
    view = {e["key"]: e for e in O.load(c)["omissions"]}
    assert raw[KEY]["outcome"] == O.ADD                     # omissions.json itself is not rewritten
    assert view[KEY]["outcome"] == O.NOT_ADDED_ANCHOR and O.NOT_ADDED_ANCHOR in O.CODE_NOT_ADDED
    assert KEY not in {e.get("key") for e in AC.load_inserts(c, AC.load_rulings(c))}
    line = C.declaration_sentence(C.ANCHOR, "may make little or no difference to HbA1c levels", "Source 2", None)
    assert line.startswith("Not added: “may make") and "found in our sources, not stated on this page" in line
    page.save(c / "draft" / "page.json")
    html = "".join("<p>%s</p>" % s for s in page.sentences())
    misplaced = [m for m in AC.check_inserts(c, html, AC.load_rulings(c), [])["mismatches"] if m.get("key") == KEY]
    assert misplaced == []


def test_a_chain_of_inserts_goes_with_its_first_anchor(tmp_path):
    c = tmp_path / "c"
    (c / "orchestrator").mkdir(parents=True)
    (c / "draft").mkdir()
    page = Page({"blocks": [{"tag": "p", "sentences": ["A is so.", "B follows A.", "C follows B.", "D stays."]}]})
    log = [{"key": "add:S1@1-2:r1", "op": "insert", "anchor": fingerprint("A is so."), "new": "B follows A."},
           {"key": "add:S1@3-4:r2", "op": "insert", "anchor": fingerprint("B follows A."), "new": "C follows B."}]
    (c / "orchestrator" / "applied.jsonl").write_text("".join(json.dumps(r) + "\n" for r in log))
    made = AP._cascade(c, page, "A is so.", "failsafe:x", AP._inserted(c), set())
    page.delete("A is so.")
    assert list(page.sentences()) == ["D stays."]
    assert [m["omission_key"] for m in made] == ["S1@1-2", "S1@3-4"]


def test_the_finding_is_on_the_readers_list_bound_to_its_passage(tmp_path, monkeypatch):
    import lean
    c, page = _case(tmp_path)
    AP.apply_all(c, page)
    monkeypatch.setattr(lean, "enabled", lambda: False)
    monkeypatch.setattr(C, "_sources", lambda slug: [])
    held = {"S002": "x" * 84643 + "the HbA1c finding" + "y" * 400}
    rows = [d for d in C.declarations("whu-x", held, case=c) if d["key"] == KEY]
    assert len(rows) == 1 and rows[0]["state"] == C.ANCHOR and rows[0]["source"] == "S002"
    assert rows[0]["text"].startswith("the HbA1c finding")          # the line's span is the finding's own passage
