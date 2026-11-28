"""The advisor's rulings on WHU-OT1-04i (P222), 2026-11-28. Offline; the live tests read 04i's own records and skip
where the trial library is absent.

1. A relevant held assessment judgement whose stating sentence a later record removed becomes code's readers'-list
   line, as P155's headline units do (coverage_check.removed_judgements): 04i's SPM B.6.1.
2. A name inside the quotation of a code-written readers'-list line that quotes its held source is not a page
   attribution (lint_claims.code_quoted_lines): 04i's "Strefler et al" line; a model-written sentence naming an
   author is still flagged.
4. The orchestrator's commit step stages an allow-list, never the case folder (orch/commit_paths.py).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import coverage_check as C  # noqa: E402
import lint_claims as L  # noqa: E402

SPM = ("B.6 Pathways. Some context first. B.6.1 Global modelled pathways that limit warming to 1.5°C reach net "
       "zero CO2 in the early 2050s (high confidence). B.6.2 Another statement that stays on the page "
       "(medium confidence).")
B61 = [SPM.index("B.6.1"), SPM.index(" B.6.2")]
QUOTE = "Global modelled pathways that limit warming to 1.5°C reach net zero CO2 in the early 2050s"


@pytest.fixture
def case(tmp_path, monkeypatch):
    import ruling as R
    c = tmp_path / "WHU-OT1-99-whu-x"
    c.mkdir()
    (c / "issue.json").write_text(json.dumps({"slug": "whu-x"}))
    import premise as PM
    import lean
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S001": SPM})
    monkeypatch.setattr(PM, "load", lambda slug: {"what_the_sources_show": {"sources": ["S001"]}})
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S001", "type": "assessment"}])
    monkeypatch.setattr(lean, "enabled", lambda: False)
    (c / "judgements.json").write_text(json.dumps({"candidates": {
        "S001@%d-%d" % tuple(B61): {"source": "S001", "at": B61, "relevant": True},
        "S001@0-20": {"source": "S001", "at": [0, 20], "relevant": False}}}))
    return c


def _bind(c, on_page):
    row = {"sentence": "According to the IPCC (B.6.1), pathways reach net zero CO2 in the early 2050s (high "
                       "confidence) [1].", "source_id": "S001", "span": QUOTE, "on_page": on_page}
    if not on_page:
        row["off_page_by"] = "failsafe:overstatement:64627a69:e8eb7149d06b497f"
    (c / "bindings.json").write_text(json.dumps({"bindings": {"e8eb7149d06b497f": row}}))


def test_a_judgement_whose_sentence_was_removed_is_declared_by_code(case):
    _bind(case, on_page=False)
    k = "S001@%d-%d" % tuple(B61)
    got = C.removed_judgements(case)
    assert list(got) == [k] and got[k]["state"] == C.REMOVED
    assert got[k]["removed_by"] == ["failsafe:overstatement:64627a69:e8eb7149d06b497f"]
    assert C.load(case)["declarations"][k]["state"] == C.REMOVED
    assert not (case / C.RECORD).exists()                     # computed each time, never written
    assert C.load(case, raw=True)["declarations"] == {}       # writers read raw
    assert C.REMOVED not in C.COUNTED                         # not against the budget


def test_a_judgement_still_stated_is_not_declared(case):
    _bind(case, on_page=True)
    assert C.removed_judgements(case) == {}


def test_a_not_relevant_judgement_is_never_declared(case):
    _bind(case, on_page=False)
    assert all(k.startswith("S001@%d" % B61[0]) for k in C.removed_judgements(case))


def test_a_judgement_already_declared_as_a_unit_gets_one_line(case, monkeypatch):
    _bind(case, on_page=False)
    unit = "S001@%d-%d" % (B61[0] + 6, B61[1] - 1)          # an overlapping unit key, P155's
    monkeypatch.setattr(C, "removed_units", lambda c: {unit: {"state": C.REMOVED}})
    assert set(C.load(case)["declarations"]) == {unit}


def test_the_judgements_row_reads_the_line(case, monkeypatch):
    import judgements as J
    import omissions as O
    _bind(case, on_page=False)
    c = {"key": "S001@%d-%d" % tuple(B61), "source": "S001", "at": B61, "section": "SPM B.6.1"}
    rows = json.loads((case / "bindings.json").read_text())["bindings"]
    st, how = J.state_of(c, SPM, rows, {"S001": SPM}, C.load(case)["declarations"], {})
    assert (st, how) == ("declared", C.REMOVED)


# ---------------------------------------------------------------- ruling 2

LINE = ("Not added: “Exceptions such as in (Strefler et al 2018a) confirm that adding other NETs (in this case "
        "terrestrial enhanced weathering) to BECCS can substantially reduce side …” (Negative emissions—Part 2: "
        "Costs, potentials and side effects [5]) (over the additions budget).")
QUOTED = ("Exceptions such as in (Strefler et al 2018a) confirm that adding other NETs (in this case terrestrial "
          "enhanced weathering) to BECCS can substantially reduce side …")


def test_a_name_inside_a_code_written_quotation_is_not_an_attribution():
    assert L.attributions(LINE, {" ".join(LINE.split()): QUOTED}) == []


def test_the_same_line_without_its_record_is_still_checked():
    assert L.attributions(LINE, {}) and "Strefler et al" in L.attributions(LINE)[0]


def test_a_model_written_sentence_naming_an_author_is_still_flagged():
    model = "Strefler et al found that adding enhanced weathering to BECCS reduces side effects [5]."
    got = L.attributions(model + " " + LINE, {" ".join(LINE.split()): QUOTED})
    assert len(got) == 1 and got[0].startswith("Strefler et al — Strefler et al found")


def test_a_name_outside_the_quotation_of_an_exempt_line_is_still_checked():
    line = LINE.replace("(Negative emissions", "(Smith et al., Negative emissions")
    got = L.attributions(line, {" ".join(line.split()): QUOTED})
    assert len(got) == 1 and got[0].startswith("Smith et al")


def test_code_quoted_lines_requires_the_quotation_in_the_held_text(monkeypatch):
    import ruling as R
    d = {"sentence": LINE, "source": "S005"}
    monkeypatch.setattr(C, "declarations", lambda slug, held: [d])
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S005": "x " + QUOTED[:-2] + " effects, y"})
    assert L.code_quoted_lines("whu-x") == {" ".join(LINE.split()): QUOTED}
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S005": "nothing like it"})
    assert L.code_quoted_lines("whu-x") == {}


def test_code_quoted_lines_fails_closed(monkeypatch):
    def boom(slug, held):
        raise RuntimeError("no records")
    monkeypatch.setattr(C, "declarations", boom)
    assert L.code_quoted_lines("whu-x") == {}


# ---------------------------------------------------------------- ruling 4

def test_the_commit_step_stages_an_allow_list(tmp_path):
    from orch import commit_paths as CP
    c = tmp_path / "case"
    for rel in ("issue.json", "bindings.json", "audit/r1/verdicts.jsonl", "rulings/rulings.jsonl",
                "rulings/lean_editions.jsonl", "advocate/x-briefs.json", "draft/whu-x.html", "draft/page.json",
                "orchestrator/run_paid.json", "orchestrator/runs/01-run_paid.json", "orchestrator/applied.jsonl"):
        (c / rel).parent.mkdir(parents=True, exist_ok=True)
        (c / rel).write_text("{}")
    got = {p.relative_to(c).as_posix() for p in CP.paths(c, "whu-x")}
    assert got == {"issue.json", "rulings/lean_editions.jsonl", "draft/whu-x.html", "draft/page.json",
                   "orchestrator/run_paid.json", "orchestrator/runs/01-run_paid.json"}
    assert CP.refused("audit/r1/verdicts.jsonl") and CP.refused("bindings.json") and not CP.refused("issue.json")


def test_the_staged_scan_flags_source_text_beyond_the_page(tmp_path, monkeypatch):
    import ruling as R
    from orch import commit_paths as CP
    held = " ".join("w%d" % i for i in range(200))
    c = tmp_path / "case"
    (c / "draft").mkdir(parents=True)
    (c / "draft" / "whu-x.html").write_text("<p>%s</p>" % " ".join("w%d" % i for i in range(100, 140)))
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S001": held})
    long_run = json.dumps({"q": " ".join("w%d" % i for i in range(0, 40))})
    on_page = json.dumps({"q": " ".join("w%d" % i for i in range(100, 140))})
    short = json.dumps({"q": " ".join("w%d" % i for i in range(0, 20))})
    assert CP.staged_source_text("whu-x", [("a.json", long_run), ("b.json", on_page), ("c.json", short)], c) \
        == [("a.json", 40)]


def test_the_commit_step_uses_the_allow_list():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    body = src[src.index("def code_commit"):src.index("def code_belief")]
    assert "CP.paths(ctx.case, ctx.slug)" in body and "[ctx.rel(ctx.case)]" not in body
    assert "staged_source_text" in body


# ---------------------------------------------------------------- 04i's own records (local only)

def _live(code: str):
    if not (ROOT / "backend" / "data" / "whatholdsup" / "library_trial").exists():
        pytest.skip("trial library not present (local only)")
    py = str(ROOT / "backend" / "venv" / "bin" / "python3")
    if not Path(py).exists():
        py = sys.executable
    out = subprocess.run([py, str(W / "orch" / "run_env.py"), "whu-lean-orch-t1-q1-04i", "--", py, "-c",
                          "import sys; sys.path.insert(0, %r)\n%s" % (str(W), code)],
                         capture_output=True, text=True, cwd=str(W), timeout=900)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_04i_b61_is_declared_by_code():
    got = _live("import json, coverage_check as C, source_store as s\n"
                "print(json.dumps(C.removed_judgements(s.case_dir('whu-lean-orch-t1-q1-04i'))))")
    assert list(got) == ["S001@109077-110619"] and got["S001@109077-110619"]["removed_by"][0].endswith(
        ":e8eb7149d06b497f")


def test_04i_strefler_line_is_exempt():
    got = _live("import json, lint_claims as L\n"
                "q = L.code_quoted_lines('whu-lean-orch-t1-q1-04i')\n"
                "print(json.dumps([k for k in q if 'Strefler et al' in k]))")
    assert len(got) == 1 and got[0].startswith("Not added: “Exceptions such as in (Strefler et al 2018a)")


def test_an_overlapping_unit_line_declares_the_judgement(case, monkeypatch):
    import judgements as J
    _bind(case, on_page=False)
    unit = "S001@%d-%d" % (B61[0] + 6, B61[1] - 1)
    monkeypatch.setattr(C, "removed_units", lambda c: {unit: {"state": C.REMOVED}})
    c = {"key": "S001@%d-%d" % tuple(B61), "source": "S001", "at": B61, "section": "SPM B.6.1"}
    rows = json.loads((case / "bindings.json").read_text())["bindings"]
    decl = C.load(case)["declarations"]
    assert J.state_of(c, SPM, rows, {"S001": SPM}, decl, {}) == ("declared", C.REMOVED)
    # an overlapping declaration that is not code's "not stated" line does not declare it
    assert J.state_of(c, SPM, rows, {"S001": SPM}, {unit: {"state": "not_material"}}, {})[0] == "not stated"
