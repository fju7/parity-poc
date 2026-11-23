"""Advisor's rulings after orchestrator trial 1 attempt 18 (2026-11-23), at $0.

(0) lean / orchestrated splitter: a single capital + full stop is an initial only before a word that is not a
    common sentence opener;
(1) the consistency audit samples every audit round with rulings not yet sampled, and records "no rulings to
    sample" when there are none;
(2) its argv, exit code, stdout and stderr are kept in the run record, on a stop too;
(3) source-list entries come from each source's own registry record, with a check."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
import lean  # noqa: E402
import orchestrator as O  # noqa: E402
import source_entries as SE  # noqa: E402
import source_ledger as L  # noqa: E402
from orch import resolve as RV  # noqa: E402

A18 = ROOT / "issues" / "WHU-OT1-02r-whu-lean-orch-t1-q1-02r"
FIX = ROOT / "backend" / "tests" / "fixtures" / "whu_orch_epmc"


@pytest.fixture
def lean_on(monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    lean.enable(True)
    yield
    lean.enable(False)
    lean._forced = None


@pytest.fixture
def lean_off(monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    lean._forced = False
    yield
    lean._forced = None


# ----------------------------------------------------------------- (0) initials and sentence openers

def test_vitamin_d_then_the_splits(lean_on):
    assert L.sentences("Levels of vitamin D. The next trial was larger.") == \
        ["Levels of vitamin D.", "The next trial was larger."]


@pytest.mark.parametrize("opener", sorted(L.SENTENCE_OPENERS))
def test_every_listed_opener_ends_the_sentence(opener, lean_on):
    assert len(L.sentences("It was type B. %s next one followed." % opener)) == 2


@pytest.mark.xfail(strict=True, reason="'Patients' is not on the ruled opener list, so 'B. Patients' still reads "
                                       "as an initial; reported to the advisor")
def test_hepatitis_b_then_patients_splits(lean_on):
    assert L.sentences("Infected with hepatitis B. Patients were followed for a year.") == \
        ["Infected with hepatitis B.", "Patients were followed for a year."]


@pytest.mark.parametrize("s", ["The review by J. Smith was cited.", "The review by J. R. Smith was cited."])
def test_initials_before_a_name_stay_one_sentence(s, lean_on):
    assert L.sentences(s + " Then another.") == [s, "Then another."]


def test_off_initials_split_as_before(lean_off):
    assert L.sentences("By J. Smith. The end.") == ["By J.", "Smith.", "The end."]


# ----------------------------------------------------------------- (1)-(2) the consistency audit

def _case(tmp_path, rounds: dict[str, int], sampled=()):
    case = tmp_path / "case"
    for run, n in rounds.items():
        d = case / "audit" / run
        d.mkdir(parents=True)
        (d / "rulings.jsonl").write_text("".join(json.dumps({"unit": "u%d" % i}) + "\n" for i in range(n)))
    (case / "rulings").mkdir(parents=True)
    (case / "rulings" / "consistency.jsonl").write_text(
        "".join(json.dumps({"step": "audit-%s" % r}) + "\n" for r in sampled))
    return case


def _ctx(case):
    return SimpleNamespace(case=case, slug="demo", root=ROOT, env=lambda step: {})


class FakeRun:
    def __init__(self, rc=0):
        self.rc, self.argv = rc, []

    def __call__(self, argv, **kw):
        self.argv.append(argv)
        return subprocess.CompletedProcess(argv, self.rc, "sampled 1 of 1\n", "" if self.rc == 0 else "refused: why\n")


ATTEMPT18 = {"20261123T221443Z": 1, "20261123T221614Z": 0}      # round 1: one ruling; round 2: none


def test_attempt_18s_two_rounds_sample_the_round_with_rulings(tmp_path, monkeypatch):
    case = _case(tmp_path, ATTEMPT18)
    fake = FakeRun()
    monkeypatch.setattr(O.subprocess, "run", fake)
    got = O.consistency_audit(_ctx(case), SimpleNamespace(cap_usd=4.0))
    assert got["rounds"] == ["20261123T221443Z"] and [a[3:5] for a in fake.argv] == [["demo", "20261123T221443Z"]]
    assert got["calls"][0]["rc"] == 0 and got["calls"][0]["stdout"] == "sampled 1 of 1\n" and "stderr" in got["calls"][0]


def test_every_unsampled_round_with_rulings_is_sampled(tmp_path, monkeypatch):
    case = _case(tmp_path, {"r1": 2, "r2": 0, "r3": 1, "r4": 1}, sampled=("r4",))
    monkeypatch.setattr(O.subprocess, "run", FakeRun())
    assert O.consistency_audit(_ctx(case), SimpleNamespace(cap_usd=4.0))["rounds"] == ["r1", "r3"]


def test_no_rulings_in_any_round_is_recorded_not_skipped(tmp_path, monkeypatch):
    case = _case(tmp_path, {"r1": 0, "r2": 0})
    fake = FakeRun()
    monkeypatch.setattr(O.subprocess, "run", fake)
    got = O.consistency_audit(_ctx(case), SimpleNamespace(cap_usd=4.0))
    assert got == {"outcome": O.NO_RULINGS, "rounds": [], "calls": []} and fake.argv == []


def test_a_refusal_stops_the_run_with_its_output_kept(tmp_path, monkeypatch):
    case = _case(tmp_path, {"r1": 1})
    monkeypatch.setattr(O.subprocess, "run", FakeRun(rc=1))
    with pytest.raises(O.RunStop) as e:
        O.consistency_audit(_ctx(case), SimpleNamespace(cap_usd=4.0))
    assert e.value.consistency["calls"][0]["stderr"] == "refused: why\n" and e.value.consistency["calls"][0]["rc"] == 1
    ctx = SimpleNamespace(log=[], replies=[], case=case, slug="demo")
    result = {"step": "audit"}
    O._log_failed(ctx, SimpleNamespace(name="audit"), result, e.value)
    assert result["consistency"]["calls"][0]["stderr"] == "refused: why\n"


# ----------------------------------------------------------------- (3) source-list entries

S003_RECORD = {"registry": "europepmc", "authors": ["Saran A", "White H", "Kuper H"], "year": 2020,
               "title": "Evidence and gap map of studies assessing the effectiveness of interventions for people "
                        "with disabilities in low-and middle-income countries.",
               "container": "Campbell Systematic Reviews"}
S003 = {"id": "S003", "authors": "Saran", "year": 2020, "container": "Campbell Systematic Reviews",
        "title": S003_RECORD["title"], "registry_record": S003_RECORD}
ATTEMPT18_ENTRY = ("Saran. Evidence and gap map of studies assessing the effectiveness of interventions for people "
                   "with disabilities in low-and middle-income countries.. Campbell Systematic Reviews. 2020.")


def test_the_entry_is_the_registry_record_and_passes(lean_on):
    t = SE.entry_text(S003)
    assert t == ("Saran A, White H, Kuper H. Evidence and gap map of studies assessing the effectiveness of "
                 "interventions for people with disabilities in low-and middle-income countries. Campbell Systematic "
                 "Reviews. 2020.")
    assert SE.problems(S003, t) == []


def test_attempt_18s_entry_fails_the_check():
    p = SE.problems(S003, ATTEMPT18_ENTRY)
    assert "doubled punctuation" in p and any("initials" in x for x in p)


def test_more_than_one_year_fails_but_a_year_in_the_title_does_not():
    src = dict(S003, registry_record=dict(S003_RECORD, title="Global Education Monitoring Report 2020"))
    assert SE.problems(src, "Saran A. Global Education Monitoring Report 2020. UNESCO. 2020.") == []
    assert any("more than one year" in x for x in SE.problems(S003, "Saran A. A title. A journal. 2018. 2020."))


def test_a_source_with_no_registry_record_keeps_its_fields_and_is_not_held_to_initials():
    src = {"authors": "Kuper", "title": "Rapid Evidence Assessment (REA) of What Works.", "year": 2018,
           "container": "Campbell Collaboration"}
    t = SE.entry_text(src)
    assert t == "Kuper. Rapid Evidence Assessment (REA) of What Works. Campbell Collaboration. 2018."
    assert SE.problems(src, t) == []


def test_a_question_mark_title_is_not_doubled():
    src = {"registry_record": dict(S003_RECORD, title="Do programmes work?", authors=["Hunt X"])}
    t = SE.entry_text(src)
    assert t == "Hunt X. Do programmes work? Campbell Systematic Reviews. 2020." and SE.problems(src, t) == []


def test_four_authors_or_more_are_three_then_et_al():
    src = {"registry_record": dict(S003_RECORD, authors=["Hunt X", "Saran A", "White H", "Kuper H"])}
    assert SE.entry_text(src).startswith("Hunt X, Saran A, White H, et al. Evidence and gap map")


def test_the_europe_pmc_record_carries_the_entry_fields():
    rec = json.loads((FIX / "search_core_PMC8988635.json").read_text())["resultList"]["result"][0]
    got = RV.search_pmcid("PMC8988635", rec["title"], "Hunt", 2021, lookup=lambda i, f: rec)
    r = got.extra["record"]
    assert r["authors"] == ["Hunt X", "Saran A", "White H", "Kuper H"] and r["year"] == 2021
    assert r["container"] and r["title"] == rec["title"]


def test_discover_stores_the_registry_record_on_the_source():
    found = RV.Found(RV.Ident("doi", "10.1002/cl2.1070"), S003_RECORD["title"], "europepmc",
                     {"pmcid": "PMC8356326", "record": S003_RECORD})
    srcs, _ = O.resolve_proposals([{"type": "synthesis", "title": S003_RECORD["title"], "first_author": "Saran",
                                    "year": 2020, "url": ""}], lambda *a: found)
    assert srcs[0]["registry_record"] == S003_RECORD


def test_attempt_18s_committed_page_fails_the_check():
    sources = json.loads((A18 / "sources.json").read_text())["sources"]
    bad = SE.page_problems(sources, (A18 / "draft" / "whu-lean-orch-t1-q1-02r.html").read_text())
    assert "[3] doubled punctuation" in bad and "[1] doubled punctuation" in bad


def test_the_lean_preflight_row_blocks_attempt_18s_page():
    rows = SE.preflight_rows("whu-lean-orch-t1-q1-02r", A18 / "draft" / "whu-lean-orch-t1-q1-02r.html", "ok",
                             "BLOCKED")
    assert rows[0][0] == SE.ROW and rows[0][1] == "BLOCKED"


def test_the_standing_check_reports_with_its_prefix():
    ctx = SimpleNamespace(case=A18)
    bad = O.entry_problems(ctx, (A18 / "draft" / "whu-lean-orch-t1-q1-02r.html").read_text())
    assert bad and all(b.startswith(O.ENTRY_PREFIX) for b in bad)


# ----------------------------------------------------------------- attempt 19: the google package is not shadowed

def test_orch_folder_is_never_on_sys_path_so_google_resolves_to_the_sdk():
    """Attempt 19: orch/apply.py put backend/scripts/whatholdsup/orch on sys.path, so `from google import genai` in
    orch/google.py found orch/google.py itself. Run in a fresh interpreter, after importing every orch module the
    orchestrator loads."""
    code = ("import sys; sys.path.insert(0, %r)\n"
            "import orchestrator, orch.apply, orch.google, orch.overstatement, orch.preflight\n"
            "import os; orch_dir = os.path.join(%r, 'orch')\n"
            "assert all(os.path.abspath(p) != orch_dir for p in sys.path), 'orch/ is on sys.path'\n"
            "from google import genai\n"
            "assert 'site-packages' in genai.__file__, genai.__file__\n" % (str(WHU), str(WHU)))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-2000:]
