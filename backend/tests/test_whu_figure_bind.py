"""One contiguous passage for a sentence's figures (advisor's ruling 3 on P171-P176). Rule 1 is unchanged. $0."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import figure_bind as FB  # noqa: E402

TEXT = ("Background sentence with no numbers. Exclusive breastfeeding was unchanged (RR 0.92, 95% CI 0.79 to 1.07). "
        "Maternal problems fell (RR 0.19). Another sentence follows here. A later place says 0.04 alone.\n"
        "Outcome | 200 participants | RR 0.61 | 0.28 to 1.33\n"
        "Last sentence with 10.92 and 0.925 in it.")


def test_one_sentence_holds_every_figure():
    a, b, kind = FB.find(["0.92", "0.79", "1.07"], TEXT)
    assert kind == "sentence" and TEXT[a:b].startswith("Exclusive breastfeeding")


def test_an_adjacent_pair_when_no_single_sentence_does():
    a, b, kind = FB.find(["0.92", "0.19"], TEXT)
    assert kind == "adjacent sentence pair" and "0.92" in TEXT[a:b] and "0.19" in TEXT[a:b]


def test_one_table_row():
    a, b, kind = FB.find(["200", "0.61", "0.28", "1.33"], TEXT)
    assert kind == "table row" and TEXT[a:b].startswith("Outcome | 200")


def test_figures_from_separate_places_are_never_combined():
    """0.92 and 0.04 are both in TEXT, two sentences apart: no single passage holds both."""
    assert FB.find(["0.92", "0.04"], TEXT) is None
    assert FB.find(["0.92", "200"], TEXT) is None


def test_a_figure_inside_another_number_does_not_count():
    assert not FB.has("0.92", "RR 10.92 here")
    assert not FB.has("0.92", "RR 0.925 here")
    assert FB.has("0.92", "RR 0.92, 95% CI")


def test_attach_binds_the_passage_with_its_offsets(monkeypatch):
    held = {"S001": TEXT}
    row = {"on_page": True, "source_id": "S001", "span": "Maternal problems fell (RR 0.19).",
           "sentence": "Breastfeeding was unchanged (RR 0.92, 95% CI 0.79 to 1.07) [1]."}
    p = FB.attach(row, held)
    x = row["also_rests_on"][-1]
    assert p and x["by"] == FB.BY and x["figure_passage"] == "sentence"
    assert TEXT[x["offsets"][0]:x["offsets"][1]] == x["span"]
    assert FB.attach(row, held) is None                        # nothing left missing: not added twice
    assert len(row["also_rests_on"]) == 1


def test_nothing_attached_when_no_single_passage_holds_all():
    row = {"on_page": True, "source_id": "S001", "span": "Background sentence with no numbers.",
           "sentence": "Breastfeeding was unchanged (RR 0.92) while 0.04 of mothers ... [1]."}
    assert FB.attach(row, {"S001": TEXT}) is None and not row.get("also_rests_on")


def test_the_binder_attaches_the_figure_passage():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    body = src[src.index("def code_bind"):src.index("def _open_units")]
    assert "FB.attach(row, held)" in body


def _live(slug):
    if not (ROOT / "backend" / "data" / "whatholdsup" / "library_trial").exists():
        pytest.skip("trial library not present (local only)")
    py = str(ROOT / "backend" / "venv" / "bin" / "python3")
    if not Path(py).exists():
        py = sys.executable
    out = subprocess.run([py, str(W / "orch" / "run_env.py"), slug, "--", py, str(W / "figure_bind.py"), slug],
                         capture_output=True, text=True, cwd=str(ROOT), timeout=600)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads([ln for ln in out.stdout.splitlines() if ln.startswith('{"slug"')][-1])


def test_01d_three_sentences_each_find_one_passage_and_pass_rule_1():
    got = _live("whu-lean-orch-t1-q1-01d")
    by = {x["row"]: x for x in got["detail"]}
    assert set(by) == {"1ff00044", "0ed7804d", "21e91962"} and all(x["bound"] for x in by.values())
    assert by["1ff00044"]["passage"]["kind"] == "adjacent sentence pair"
    assert by["1ff00044"]["passage"]["source_id"] == "S003"
    assert by["0ed7804d"]["passage"]["kind"] == "sentence" and "Britain" in by["0ed7804d"]["passage"]["span"]
    assert by["21e91962"]["passage"]["kind"] == "sentence"
    assert len(got["rule1_before"]) == 3 and got["rule1_after"] == []


def test_02z_row_stays_stopped():
    """93fd1341's seven figures are in no one passage of S001: it stays stopped by rule 1."""
    got = _live("whu-lean-orch-t1-q1-02z")
    assert [x["row"] for x in got["detail"]] == ["93fd1341"] and not got["detail"][0]["bound"]
    assert got["rule1_after"] == got["rule1_before"] == ["93fd1341: 4.86, 9.48 in no span it is bound to"]


def test_recorded_sweep_of_every_case_folder():
    rec = json.loads((ROOT / "study/whu-reliability/next_phase/results/figure_bind_p181.json").read_text())
    assert rec["cases_swept"] == 55 and rec["errors"] == 0 and rec["rule1_rows"] == 4 and rec["bound"] == 3
    assert {(r["slug"][-3:], r["row"], r["bound"]) for r in rec["rows"]} == {
        ("01d", "1ff00044", True), ("01d", "0ed7804d", True), ("01d", "21e91962", True), ("02z", "93fd1341", False)}
    assert '"span"' not in json.dumps(rec)                     # offsets only: no held text in the repository
