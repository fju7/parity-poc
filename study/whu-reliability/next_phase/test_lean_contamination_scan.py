"""lean_contamination_scan.py: the broad-command rule (advisor, 2026-11-05). Offline.

    backend/venv/bin/python -m pytest -q study/whu-reliability/next_phase/test_lean_contamination_scan.py
"""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lcs", HERE / "lean_contamination_scan.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
R = S.REPO

BROAD = [
    "cd %s && grep -rn 'carbon removal' ." % R,
    "cd %s && grep -R adenoma issues/" % R,
    "grep -rl melanoma %s" % R,
    "cd %s && rg 'net zero'" % R,
    "cd %s && find . -name '*.json'" % R,
    "find ~ -name key.json",
    "find ~/Projects -maxdepth 3 -type d",
    "cd %s && ls -R issues" % R,
    "cd %s && du -sh study" % R,
    "cd %s && tree backend/tests" % R,
    "cd %s && git grep -n 'Outside this question'" % R,
    "cd %s && git diff" % R,
    "cd %s && git log -p --since=yesterday" % R,
    "cd %s && ls **/issue.json" % R,
    "cd %s && python3 -c \"import glob; print(glob.glob('issues/*/sources.json'))\"" % R,
    "cd %s && python3 - <<'EOF'\nimport os\nfor d, _, fs in os.walk('.'): pass\nEOF" % R,
    "ls -R %s" % S.SCRATCH,
]

NARROW = [
    "cd %s && grep -rn adenoma backend/scripts/whatholdsup" % R,
    "cd %s && grep -n 'lean' docs/whatholdsup-process.md" % R,
    "cd %s && find issues/WHU-L1-01-whu-lean-q1-01 -name '*.json'" % R,
    "cd %s && ls issues/WHU-L1-01-whu-lean-q1-01/" % R,
    "cd %s && git status --short" % R,
    "cd %s && git diff -- issues/WHU-L1-01-whu-lean-q1-01/draft/whu-lean-q1-01.html" % R,
    "cd %s && git log --oneline -3" % R,
    "cd %s && rg -n BM25 backend/scripts/whatholdsup/passage_index.py" % R,
    "cd %s && python3 -c \"import glob; print(glob.glob('backend/scripts/whatholdsup/*.py'))\"" % R,
    # Q1-01's drafter, 2026-11-05T02:08:43 (the quoted \\| must not split the command):
    "cd %s && grep -n 'licence' backend/scripts/whatholdsup/acquire_sources.py | head; "
    "grep -rn 'publisher terms\\|PUBLISHER\\|BARRED' backend/scripts/whatholdsup/*.py | head" % R,
]


@pytest.mark.parametrize("cmd", BROAD)
def test_a_command_whose_scope_takes_in_a_forbidden_folder_is_flagged(cmd):
    assert S.broad(cmd), cmd


@pytest.mark.parametrize("cmd", NARROW)
def test_a_command_whose_scope_excludes_the_forbidden_folders_is_not_flagged(cmd):
    assert S.broad(cmd) == [], (cmd, S.broad(cmd))


def test_the_harness_reset_directory_counts_as_a_broad_root():
    assert S.broad("grep -rn net-zero", cwd=S.HOME)
    assert S.broad("find . -name x", cwd=S.HOME)


def test_former_scratchpad_files_and_an_early_scratchpad_listing_are_flagged():
    assert S.scratch("cat %s/leandry/log/sampling_log.json" % S.SCRATCH, "2026-11-05T03:00:00")
    assert S.scratch("ls %s" % S.SCRATCH, "2026-11-05T02:10:00")
    assert not S.scratch("ls %s" % S.SCRATCH, "2026-11-05T03:00:00")
    assert not S.scratch("cat %s/cov0.txt" % S.SCRATCH, "2026-11-05T02:10:00")


def test_scan_reports_broad_grep_and_glob_tools_from_a_transcript(tmp_path):
    t = tmp_path / "t.jsonl"
    lines = [
        {"timestamp": "2026-11-05T03:00:00Z", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "cd %s && grep -rn x ." % R}},
            {"type": "tool_use", "id": "b", "name": "Grep", "input": {"pattern": "x", "path": R}},
            {"type": "tool_use", "id": "c", "name": "Grep", "input": {"pattern": "x", "path": R + "/backend/scripts"}},
            {"type": "tool_use", "id": "d", "name": "Bash", "input": {"command": "ls issues/WHU-Q1-01-whu-quarterly-r1-01"}}]}},
    ]
    t.write_text("\n".join(json.dumps(x) for x in lines))
    rows = {r["text"][:20]: r for r in S.scan(str(t))}
    got = [bool(r["broad"]) for r in S.scan(str(t))]
    assert got == [True, True, False, False]
    assert [bool(r["named"]) for r in S.scan(str(t))] == [False, False, False, True]


def test_another_issues_case_folder_is_reported_but_the_own_folder_is_not(tmp_path):
    t = tmp_path / "t.jsonl"
    cmds = ["grep -l licence issues/WHU-S0*/sources.json", "cat issues/WHU-L1-01-whu-lean-q1-01/issue.json",
            "ls issues/ | grep -v 'WHU-Q1\\|WHU-L1' | head -3"]
    t.write_text(json.dumps({"timestamp": "2026-11-05T03:00:00Z", "message": {"content": [
        {"type": "tool_use", "id": str(i), "name": "Bash", "input": {"command": c}} for i, c in enumerate(cmds)]}}))
    assert [bool(r["other_issue"]) for r in S.scan(str(t))] == [True, False, False]


@pytest.mark.parametrize("cmd,kind", [
    ("grep -l '\"licence\"' issues/WHU-S0*/sources.json | head -2", "names-only"),
    ("ls issues/WHU-S01-tb-dna-testing/", "names-only"),
    ("find issues/WHU-S01-tb-dna-testing -name '*.json'", "names-only"),
    ("grep -n licence issues/WHU-S0*/sources.json", "CONTENT"),
    ("cat issues/WHU-S08-settlement-planning-climate-resilience/sources.json", "CONTENT"),
    ("head -20 issues/WHU-P02-ultra-processed-foods/draft/x.html", "CONTENT"),
    ("find issues/WHU-S01-tb-dna-testing -name '*.json' -exec cat {} +", "CONTENT"),
    ("python3 -c \"print(open('issues/WHU-S01-tb-dna-testing/issue.json').read())\"", "CONTENT"),
])
def test_another_issues_folder_is_marked_names_only_or_content(cmd, kind):
    assert S.other_issue_kind(cmd) == kind, (cmd, S.other_issue_kind(cmd))


def test_a_rerun_drafter_may_not_read_the_earlier_attempt(tmp_path):
    import importlib
    spec2 = importlib.util.spec_from_file_location("lcs2", HERE / "lean_contamination_scan.py")
    S2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(S2)
    # before --rerun: either folder is its own drafter's
    assert not S2.OTHER_ISSUE.search("cat issues/WHU-L1-02r-whu-lean-q1-02r/issue.json")
    assert not S2.OTHER_ISSUE.search("cat issues/WHU-L1-02-whu-lean-q1-02/issue.json")
    S2.rerun("02")
    assert not S2.OTHER_ISSUE.search("cat issues/WHU-L1-02r-whu-lean-q1-02r/issue.json")
    assert S2.OTHER_ISSUE.search("cat issues/WHU-L1-02-whu-lean-q1-02/issue.json")
    assert S2.FORBID.search("cat issues/WHU-L1-02-whu-lean-q1-02/draft/x.html")
    assert S2.FORBID.search("cat backend/data/whatholdsup/library/issues/whu-lean-q1-02.json")
    assert not S2.FORBID.search("cat backend/data/whatholdsup/library/issues/whu-lean-q1-02r.json")
    assert not S2.FORBID.search("cat issues/WHU-L1-02r-whu-lean-q1-02r/issue.json")
    assert S2.OWN.search("ls ~/Projects/whu-study-private/WHU-L1-02r-whu-lean-q1-02r/")
    assert not S2.OWN.search("ls ~/Projects/whu-study-private/WHU-L1-02-whu-lean-q1-02/")


def test_second_freeze_rerun_forbids_every_earlier_attempt_and_takes_this_sessions_scratchpad():
    spec3 = importlib.util.spec_from_file_location("lcs3", HERE / "lean_contamination_scan.py")
    S3 = importlib.util.module_from_spec(spec3)
    spec3.loader.exec_module(S3)
    S3.rerun_b("02")
    for old in ("WHU-L1-02-whu-lean-q1-02", "WHU-L1-02r-whu-lean-q1-02r"):
        assert S3.FORBID.search("cat issues/%s/draft/x.html" % old)
        assert S3.OTHER_ISSUE.search("cat issues/%s/issue.json" % old)
    assert S3.FORBID.search("cat backend/data/whatholdsup/library/issues/whu-lean-q1-02r.json")
    assert not S3.FORBID.search("cat issues/WHU-L1-02b-whu-lean-q1-02b/issue.json")
    assert not S3.OTHER_ISSUE.search("cat issues/WHU-L1-02b-whu-lean-q1-02b/issue.json")
    assert S3.OWN.search("ls ~/Projects/whu-study-private/WHU-L1-02b-whu-lean-q1-02b/")
    S3.set_scratch("/tmp/new-session/scratchpad", "2026-11-05T21:00:00")
    assert S3.broad("grep -r x /tmp/new-session/scratchpad")
    assert S3.scratch("ls /tmp/new-session/scratchpad", "2026-11-05T20:00:00")
    assert not S3.scratch("ls /tmp/new-session/scratchpad", "2026-11-05T22:00:00")


def test_q1_01c_rerun_forbids_both_earlier_attempts():
    spec4 = importlib.util.spec_from_file_location("lcs4", HERE / "lean_contamination_scan.py")
    S4 = importlib.util.module_from_spec(spec4)
    spec4.loader.exec_module(S4)
    S4.rerun_b("01", "c")
    assert S4.FORBID.search("cat issues/WHU-L1-01b-whu-lean-q1-01b/draft/x.html")
    assert S4.FORBID.search("cat issues/WHU-L1-01-whu-lean-q1-01/draft/x.html")
    assert not S4.FORBID.search("cat issues/WHU-L1-01c-whu-lean-q1-01c/issue.json")
    assert S4.OWN.search("ls ~/Projects/whu-study-private/WHU-L1-01c-whu-lean-q1-01c/")
