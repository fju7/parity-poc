"""A job nobody started is not a job in progress.

On 2026-08-31 two gate runs were queued for the launchd runner, whose
StartInterval is 30 seconds. Ninety seconds later the queue was untouched and
backend/data/jobs/logs/ was EMPTY -- no runner.out, no runner.err, which launchd
creates on any invocation. The runner had never executed a job.

Nothing anywhere would have said so. A job sitting in the queue forever looks
exactly like a job about to start, and the board that blocks on "the gate has
not read these sentences" would have gone on saying so while the run meant to
fix it sat unread on disk.
"""
import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend" / "scripts" / "whatholdsup"))
spec = importlib.util.spec_from_file_location(
    "whu_publish", ROOT / "backend" / "scripts" / "whatholdsup" / "publish.py")
p = importlib.util.module_from_spec(spec)
sys.modules["whu_publish"] = p
spec.loader.exec_module(p)

BLOCKED, OK = "BLOCKED", "ok"


@pytest.fixture
def jobs(tmp_path, monkeypatch):
    (tmp_path / "queue").mkdir()
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(p, "JOBS", tmp_path)
    return tmp_path


def _queue(jobs, name, age_minutes=0):
    f = jobs / "queue" / (name + ".json")
    f.write_text('{"script": "scripts/x.py"}', encoding="utf-8")
    if age_minutes:
        old = time.time() - age_minutes * 60
        os.utime(f, (old, old))
    return f


def test_an_empty_queue_says_nothing(jobs):
    assert p.queued_jobs_rows() == []


def test_a_job_just_queued_is_not_a_problem(jobs):
    _queue(jobs, "003-regate")
    rows = p.queued_jobs_rows()
    assert [s for _n, s, _d in rows] == [OK]
    assert "003-regate" in rows[0][2]


def test_a_job_nobody_started_blocks(jobs):
    _queue(jobs, "003-regate", age_minutes=45)
    rows = p.queued_jobs_rows()
    assert rows[0][1] == BLOCKED
    assert "45 minutes" in rows[0][2]


def test_it_distinguishes_never_ran_from_a_new_failure(jobs):
    """And must not overclaim from an empty directory.

    The first version of this check said an empty logs/ meant "the runner has
    never executed anything". Nine minutes later the runner claimed both jobs
    and ran them: logs/ holds one file PER CLAIMED JOB, and it was empty
    because nothing had ever been queued. An empty directory was read as
    evidence of failure when it was evidence of nothing having happened -- the
    error registry_facts.py exists to outrank, committed inside a check written
    to catch it.
    """
    _queue(jobs, "003-regate", age_minutes=45)
    detail = p.queued_jobs_rows()[0][2]
    assert "no job has ever been CLAIMED" in detail
    assert "different problems and this cannot tell them apart" in detail
    assert "never executed" not in detail          # the overclaim, gone

    (jobs / "logs" / "runner.out").write_text("", encoding="utf-8")
    assert "not the install" in p.queued_jobs_rows()[0][2]


def test_the_age_is_the_oldest_job_not_the_newest(jobs):
    _queue(jobs, "003-old", age_minutes=90)
    _queue(jobs, "004-new", age_minutes=1)
    rows = p.queued_jobs_rows()
    assert rows[0][1] == BLOCKED and "90 minutes" in rows[0][2]


def test_a_missing_queue_directory_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "JOBS", tmp_path / "nope")
    assert p.queued_jobs_rows() == []
