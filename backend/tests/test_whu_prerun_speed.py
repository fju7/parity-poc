"""The pre-run check in under 15 minutes (advisor's ruling 2 on the replay gate, 2026-11-26), with no assertion dropped.

Where the time went (measured on 2026-11-26 from the step timings and HTTP events of the run records): a planned
registry fault or a recorded error waited the LIVE backoff (2, 4, 8 s per failing request: europepmc_down's 148
planned 503s were ~520 s of its 640 s), NCBI pacing and the Crossref pause ran for replies served from the
rehearsal's cache, a live 503 met in a replay was recorded and then replayed (with the backoff) on every later replay,
and the checks ran one after another. Now:
  * a failure the rehearsal made itself (planned fault, offline miss, an error replayed from its cache) is marked, and
    a backoff after it waits 1/50 (as provider_retry's rehearsal waits); a live failure waits in full;
  * a request answered from the rehearsal's cache, or offline, is not paced; a live one is paced by the cache;
  * a live 5xx / 429 is not recorded (a transient failure is not an answer);
  * the replays run in parallel; orch/prerun_check.py runs the suite once, each rehearsal test in its own process and
    the gate, all at once.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
import orchestrator as O  # noqa: E402
import registries as RG  # noqa: E402
from orch import registry_http as REG  # noqa: E402

RH = O.rehearsal_module()


@pytest.fixture
def rehearse(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_MODE", "rehearse")
    monkeypatch.setenv("WHU_REHEARSE_STATE", str(tmp_path / "state"))
    monkeypatch.setenv("WHU_REHEARSE_HTTP", str(tmp_path / "http"))
    monkeypatch.delenv("WHU_REHEARSE_OFFLINE", raising=False)
    monkeypatch.setenv("WHU_NCBI_PACE_FILE", str(tmp_path / "pace"))
    return tmp_path


def _err(code=503, ours=True):
    e = urllib.error.HTTPError("https://www.ebi.ac.uk/x", code, "x", Message(), io.BytesIO(b""))
    if ours:
        e._whu_rehearsal = True
    return e


@pytest.mark.parametrize("ours,waits", [(True, [0.04, 0.08, 0.16]), (False, [2, 4, 8])])
def test_the_registry_retry_waits_a_fiftieth_only_after_the_rehearsals_own_failure(monkeypatch, ours, waits):
    slept = []
    monkeypatch.setattr(REG, "_sleep", slept.append)

    def orig(*a, **k):
        raise _err(ours=ours)
    monkeypatch.setattr(REG, "_orig", orig)
    monkeypatch.setattr(REG, "_log", None)
    with pytest.raises(urllib.error.HTTPError):
        REG._wrapped("https://www.ebi.ac.uk/x")
    assert slept == pytest.approx(waits) and len(slept) == REG.ATTEMPTS - 1        # the same number of tries


@pytest.mark.parametrize("ours,waits", [(True, [0.04, 0.08, 0.16]), (False, [2, 4, 8])])
def test_the_acquire_fetch_retry_likewise(monkeypatch, ours, waits):
    import acquire_sources as A
    slept = []
    monkeypatch.setattr(A, "_sleep", slept.append)
    monkeypatch.setenv("WHU_ORCH_STEP", "acquire")
    monkeypatch.delenv("WHU_ORCH_UNAVAILABLE_LOG", raising=False)

    def fetch(url):
        try:
            raise _err(ours=ours)
        except urllib.error.HTTPError as e:
            raise urllib.error.URLError("wrapped") from e          # the mark is found through the cause
    monkeypatch.setattr(A, "fetch", fetch)
    with pytest.raises(urllib.error.URLError):
        A.fetch_retrying("https://www.ebi.ac.uk/x")
    assert slept == pytest.approx(waits[:A.FETCH_ATTEMPTS - 1])


def test_served_locally_uses_the_rehearsal_caches_own_key(rehearse):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=x"
    assert RH._key(url) == hashlib.sha256((url + "\n").encode()).hexdigest()
    assert not RG.served_locally(url)
    (rehearse / "http").mkdir(parents=True, exist_ok=True)
    (rehearse / "http" / (RH._key(url) + ".json")).write_text("{}")
    assert RG.served_locally(url)


def test_served_locally_is_never_true_outside_a_rehearsal(rehearse, monkeypatch):
    url = "https://api.crossref.org/works/x"
    (rehearse / "http").mkdir(parents=True, exist_ok=True)
    (rehearse / "http" / (RH._key(url) + ".json")).write_text("{}")
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    assert not RG.served_locally(url)
    monkeypatch.setenv("WHU_ORCH_MODE", "rehearse")
    monkeypatch.setenv("WHU_REHEARSE_OFFLINE", "1")
    assert RG.served_locally("https://api.crossref.org/works/never-recorded")


def test_a_cached_reply_is_not_paced_and_a_live_one_is(rehearse, monkeypatch):
    paced = []
    monkeypatch.setattr(RG, "ncbi_pace", lambda *a, **k: paced.append(1) or 0.0)
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=1"

    def live(req, *a, **k):
        return RH._Resp(b"{}", 200, {}, url)
    RH.cached_urlopen(live, url)                                    # live: paced by the cache
    assert paced == [1]
    RH.cached_urlopen(live, url)                                    # from the cache: no pacing
    assert paced == [1]
    import tls
    monkeypatch.setattr(tls, "urlopen", lambda req, timeout=0: RH.cached_urlopen(live, req.full_url))
    RG._get(url)                                                     # _get skips its own pacing for a cached url
    assert paced == [1]


def test_a_paid_runs_pacing_is_unchanged(rehearse, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    paced = []
    monkeypatch.setattr(RG, "ncbi_pace", lambda *a, **k: paced.append(1) or 0.0)
    import tls

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(tls, "urlopen", lambda req, timeout=0: R(b"{}"))
    RG._get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=1")
    assert paced == [1]


def test_a_live_transient_failure_is_not_recorded_and_a_404_is(rehearse, monkeypatch):
    monkeypatch.setattr(RG, "ncbi_pace", lambda *a, **k: 0.0)
    for code, kept in ((503, False), (429, False), (404, True)):
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?q=%d" % code

        def live(req, *a, **k):
            raise urllib.error.HTTPError(url, code, "x", Message(), io.BytesIO(b""))
        with pytest.raises(urllib.error.HTTPError):
            RH.cached_urlopen(live, url)
        assert (rehearse / "http" / (RH._key(url) + ".json")).exists() is kept


def test_the_rehearsals_own_failures_are_marked(rehearse, monkeypatch, tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"registry": [{"step": "*", "error": "503"}]}))
    monkeypatch.setenv("WHU_REHEARSE_PLAN", str(p))
    with pytest.raises(urllib.error.HTTPError) as e:
        RH.cached_urlopen(lambda *a, **k: None, "https://api.crossref.org/works/x")
    assert REG.rehearsal_made(e.value)                              # a planned fault
    monkeypatch.setenv("WHU_REHEARSE_OFFLINE", "1")
    with pytest.raises(urllib.error.URLError) as e:
        RH.cached_urlopen(lambda *a, **k: None, "https://api.crossref.org/works/y")
    assert REG.rehearsal_made(e.value)                              # an offline miss
    assert not REG.rehearsal_made(_err(ours=False))


# --- the gate and the pre-run check -----------------------------------------------------------------------------

def test_the_gate_runs_the_replays_at_once_and_times_each(monkeypatch, tmp_path):
    import threading
    import time
    from orch import replay_gate as G
    monkeypatch.setattr(G, "GATE_DIR", tmp_path)
    seen = set()

    def one(slug, offline, out_dir):
        seen.add(threading.current_thread().name)
        time.sleep(0.2)
        return {"slug": slug, "verdict": "PASS"}
    monkeypatch.setattr(G, "replay_one", one)
    rec = G.run()
    assert len(seen) == len(G.RUNS) and all("seconds" in r for r in rec["runs"]) and rec["passed"]


def test_the_prerun_check_deselects_only_the_suite_twice_test_and_keeps_its_assertion():
    from orch import prerun_check as P
    src = (ROOT / "backend" / "tests" / "test_whu_orch_rehearsal.py").read_text(encoding="utf-8")
    assert "def %s(" % P.DESELECT in src
    rows = [{"name": "suite", "start": "2026-01-01T00:00:00", "end": "2026-01-01T00:06:00"},
            {"name": "rehearsal:x", "start": "2026-01-01T00:01:00", "end": "2026-01-01T00:03:00"}]
    assert P.overlap(rows)
    rows[1].update(start="2026-01-01T00:07:00", end="2026-01-01T00:08:00")
    assert not P.overlap(rows)


def test_the_standalone_rehearsals_results_are_asserted_by_the_rehearsal_tests():
    """The old check's four `rehearse --offline` runs asserted one thing each (the result); every one is asserted by a
    rehearsal test, so dropping them drops no assertion."""
    a24 = (ROOT / "backend" / "tests" / "test_whu_orch_after_attempt24.py").read_text(encoding="utf-8")
    reh = (ROOT / "backend" / "tests" / "test_whu_orch_rehearsal.py").read_text(encoding="utf-8")
    assert '_rehearse(tmp_path / "up", "none.json")' in a24 and '_rehearse(tmp_path / "down", "europepmc_down.json")' in a24
    assert 'up["result"] == down_["result"] == "Ready."' in a24
    assert '_rehearse(tmp_path, "only_crossref_answers.json")' in a24
    assert '"registry unavailable; run again later" in r["result"]' in a24
    i = reh.index("def test_rehearsal_every_shape_and_fault_recovered_and_every_step_ran")
    assert '"shapes_and_faults.json"' in reh[i:i + 400] and '"Ready."' in reh[i:i + 900]
