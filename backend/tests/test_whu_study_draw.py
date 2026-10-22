"""The study draw (protocol rev 38): seed from the freeze commit's hash; the
first eligible entry of the shuffled list is the draw; IPCC's second question
comes from a different AR6 report; a question WHU has published or tested is
ineligible at the draw, with the reason logged; every candidate is logged.
Synthetic hashes only; nothing is fetched."""
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "study" / "whu-reliability"
_spec = importlib.util.spec_from_file_location("frames_draw_t", STUDY / "scripts" / "frames.py")
FR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FR)

H1 = "0123456789abcdef0123456789abcdef01234567"
H2 = "fedcba9876543210fedcba9876543210fedcba98"


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def test_the_seed_is_the_full_commit_hash_as_an_integer():
    assert FR.seed_from_commit(H1) == int(H1, 16)
    for bad in ("", H1[:12], H1.upper(), H1 + "0", "g" * 40):
        with pytest.raises(ValueError):
            FR.seed_from_commit(bad)


def test_a_cochrane_draw_is_the_first_entry_of_the_shuffled_eligible_list():
    ff = STUDY / "frames" / "cochrane.json"
    frame = json.loads(ff.read_text())
    order = sorted(e["k"] for e in frame["eligible"])
    random.Random(int(H1, 16)).shuffle(order)
    res = FR.draw_study(ff, H1)
    assert res["seed"] == int(H1, 16) and res["commit"] == H1 and res["frame_sha256"] == sha(ff.read_text())
    assert res["log"][0]["k"] == order[0] and res["log"][0]["result"] == "drawn"
    n = {e["k"]: e["n"] for e in frame["eligible"]}[order[0]]
    assert res["drawn"][0]["n"] == n and len(res["drawn"]) == 1
    assert FR.draw_study(ff, H1)["drawn"] == res["drawn"]                   # reproducible
    assert FR.draw_study(ff, H2)["drawn"] != res["drawn"]


def _ipcc(tmp_path, statements):
    """A synthetic IPCC frame: [(id, report, text)], every one eligible."""
    rows = [{"id": i, "report": rep, "n": n, "statement_sha256": sha(t), "eligible": True}
            for n, (i, rep, t) in enumerate(statements, 1)]
    ff = tmp_path / "ipcc.json"
    ff.write_text(json.dumps({"rows": rows, "eligible": [{"k": r["n"], "n": r["n"], "id": r["id"]} for r in rows]}))
    return ff, {i: t for i, _r, t in statements}


P04_LIKE = "Total net anthropogenic GHG emissions have continued to rise during the period 2010-2019. More follows."
PATHWAYS = ("Modelled pathways are associated with higher peak warming. This is because GHG emissions have "
            "risen since 2017.")


def test_ipcc_second_draw_is_from_another_report_and_a_whu_question_is_logged_ineligible(tmp_path):
    sts = [("A-1", "WGI", "Warming is unequivocal (high confidence)."),
           ("A-2", "WGI", "Sea level rose (high confidence)."),
           ("B-1", "WGIII", P04_LIKE),
           ("B-2", "WGIII", "Mitigation options are available (high confidence)."),
           ("C-1", "SYR", PATHWAYS)]
    ff, texts = _ipcc(tmp_path, sts)
    res = FR.draw_study(ff, H1, texts, n_draws=2)
    order = [1, 2, 3, 4, 5]
    random.Random(int(H1, 16)).shuffle(order)
    assert [r["k"] for r in res["log"]] == order[:len(res["log"])]          # every candidate, in order
    by = {r["id"]: r for r in res["log"]}
    if "B-1" in by:
        assert by["B-1"]["result"] == "ineligible" and "WHU-P04" in by["B-1"]["why"]
    reports = [d["report"] for d in res["drawn"]]
    assert len(reports) == 2 and reports[0] != reports[1]
    assert "B-1" not in [d["id"] for d in res["drawn"]]
    passed = [r for r in res["log"] if r["result"] == "passed over"]
    assert all("same AR6 report" in r["why"] for r in passed)


@pytest.mark.parametrize("h", [H1, H2, "1" * 40, "a" * 40, "9" * 40])
def test_whatever_the_hash_a_duplicate_question_is_never_drawn(tmp_path, h):
    ff, texts = _ipcc(tmp_path, [("B-1", "WGIII", P04_LIKE), ("A-1", "WGI", "Warming is unequivocal."),
                                 ("C-1", "SYR", PATHWAYS)])
    res = FR.draw_study(ff, h, texts, n_draws=2)
    assert "B-1" not in [d["id"] for d in res["drawn"]]
    assert {r["id"]: r["result"] for r in res["log"]}.get("B-1", "ineligible") == "ineligible"


def test_a_statement_that_does_not_match_its_frame_hash_is_undetermined_and_never_drawn(tmp_path):
    ff, texts = _ipcc(tmp_path, [("A-1", "WGI", "Warming is unequivocal."), ("A-2", "WGII", "Risks rise.")])
    texts["A-1"] = "Warming is unequivocal, as re-fetched with a change."
    res = FR.draw_study(ff, H1, texts, n_draws=2)
    assert {r["id"]: r["result"] for r in res["log"]}["A-1"] == "undetermined"
    assert [d["id"] for d in res["drawn"]] == ["A-2"]


def test_what_counts_as_a_whu_question():
    assert any("WHU-P04" in d for d in FR.duplicates(P04_LIKE))
    assert FR.duplicates(PATHWAYS) == []                      # emissions in passing, not the claim
    assert any("T02" in d for d in FR.duplicates("Ultra-processed food consumption and mortality"))
    assert any("WHU-002" in d for d in FR.duplicates("Palbociclib for advanced breast cancer"))
    assert FR.duplicates("Arts interventions for children at risk of offending") == []


def test_the_draw_command_refuses_a_short_hash_and_a_frame_not_as_committed(tmp_path):
    py = sys.executable
    r = subprocess.run([py, str(STUDY / "scripts" / "frames.py"), "draw-cochrane", "--commit", H1[:12],
                        "--cache", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode != 0 and "40-character" in r.stderr
    r = subprocess.run([py, str(STUDY / "scripts" / "frames.py"), "draw-cochrane", "--commit", H1,
                        "--cache", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode != 0 and "not as committed" in r.stderr
    assert not (STUDY / "frames" / "draws" / ("cochrane-%s.json" % H1)).exists()   # nothing written
