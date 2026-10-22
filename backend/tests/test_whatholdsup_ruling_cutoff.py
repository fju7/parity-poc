"""A ruling reply cut off at its output limit (2026-10-22).

On WHU-S01 a ruling reply ran past the 1,500-token limit, the caller raised
AuditFailure, and the step stopped mid-way, before its consistency sample. Now
the limit is 4,000; a cut-off reply is asked once more with the identical
prompt and both attempts are logged; cut off again, the sentence's findings are
logged RULING_FAILED, left open, and the step goes on. A step that stopped
before its sample is sampled by the run that resumes it. The model is a stub:
nothing is spent.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CS = _load("consistency_cut_t", WHU / "consistency.py")
A = _load("audit_stage_cut_t", WHU / "audit_stage.py")
import ruling as R  # noqa: E402  (consistency.ruling_reask imports it by this name)

DOC = "Background. The trial found that the intervention reduced weight by 2 kg over 12 weeks. More."
HELD = {"S1": DOC}
SPAN = "the intervention reduced weight by 2 kg over 12 weeks"
REJECT = {"ruling": "reject", "text": None, "reason": "r"}


def _row(i):
    return {"sentence": "Sentence number %d says the intervention cut weight by 2 kg." % i,
            "on_page": True, "source_id": "S1", "span": SPAN}


class Model:
    """A stub model behind the real audit_stage.Caller: `cut(prompt, n)` says
    whether call n (1-based) is cut off at max_tokens."""

    def __init__(self, cut=lambda prompt, n: False):
        self.cut, self.prompts, self.limits = cut, [], []

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        self.limits.append(max_tokens)
        usage = {"input": 10, "output": max_tokens, "usd": 0.01}
        if self.cut(prompt, len(self.prompts)):
            return '{"ruling": "amend", "text": "unfinish', dict(usage, stop_reason="max_tokens")
        return json.dumps(REJECT), dict(usage, output=5)


@pytest.fixture
def study(tmp_path, monkeypatch):
    d = tmp_path / "WHU-S99-xq"
    d.mkdir()
    import source_store
    import changecheck as C
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    monkeypatch.setattr(C, "record_path", lambda slug: d / "change-reviews.json")
    return d, types.SimpleNamespace(is_study=lambda slug: slug == "xq")


def _setup(d, n):
    import changecheck as C
    rows = {"k%d" % i: _row(i) for i in range(n)}
    page = "<html><body><p>%s</p></body></html>" % " ".join(r["sentence"] for r in rows.values())
    fs = [{"sentence": r["sentence"], "kind": "NEW_AND_UNBOUND", "why": "w%d" % i, "other": ""}
          for i, r in enumerate(rows.values())]
    (d / "change-reviews.json").write_text(json.dumps({"reviews": [{"sha": C.page_sha(page), "findings": fs}]}))
    return rows, page


def _caller(model):
    return A.Caller(cap=5.0, ledger_issue="xq", ask=model, day_cap=lambda usd: None)


def _jsonl(p):
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def test_the_limit_is_4000_tokens():
    assert R.MAX_OUT == 4000 and R.ATTEMPTS == 2


def test_the_caller_raises_a_cut_off_that_carries_what_it_cost():
    m = Model(cut=lambda p, n: True)
    call = _caller(m)
    with pytest.raises(A.ReplyCutOff) as e:
        call("prompt", 4000, "rule-gate")
    assert isinstance(e.value, A.AuditFailure) and e.value.cut_off
    assert e.value.usage["usd"] == 0.01 and call.calls[0]["output"] == 4000   # paid for, counted


def test_a_cut_off_reply_is_retried_once_with_the_same_prompt_and_both_are_logged(study):
    d, P = study
    rows, page = _setup(d, 1)
    m = Model(cut=lambda p, n: n == 1)
    done = R.rule_changecheck("xq", _caller(m), P=P, rows=rows, held=HELD, page_html=page)
    assert len(done) == 1 and done[0]["decision"] == "reject"
    assert len(m.prompts) == 2 and m.prompts[0] == m.prompts[1] and m.limits == [4000, 4000]
    cut = _jsonl(d / "rulings" / "attempts.jsonl")
    assert [c["type"] for c in cut] == ["cut_off"] and cut[0]["attempt"] == 1
    assert cut[0]["inputs"]["sentence"].startswith("Sentence number 0") and cut[0]["max_tokens"] == 4000
    rec = _jsonl(d / "rulings" / "rulings.jsonl")
    assert len(rec) == 1 and rec[0]["after_cut_off"] == [cut[0]["id"]]
    assert rec[0]["inputs_sha256"] == cut[0]["inputs_sha256"]                 # the same payload


def test_cut_off_twice_is_ruling_failed_and_the_step_goes_on(study):
    d, P = study
    rows, page = _setup(d, 3)
    # every call about sentence 1 is cut off; the others are answered
    m = Model(cut=lambda p, n: "Sentence number 1 " in p)
    failed = []
    done = R.rule_changecheck("xq", _caller(m), P=P, rows=rows, held=HELD, page_html=page, failed=failed)
    assert len(done) == 2                                                    # 0 and 2 ruled
    assert {x["sentence"][:17] for x in done} == {"Sentence number 0", "Sentence number 2"}
    assert len(failed) == 1 and "cut off at 4000 tokens on all 2 attempts" in failed[0]["why"]
    att = _jsonl(d / "rulings" / "attempts.jsonl")
    assert [a["type"] for a in att] == ["cut_off", "cut_off", "RULING_FAILED"]
    assert att[2]["status"] == "RULING_FAILED" and att[2]["attempts"] == [att[0]["id"], att[1]["id"]]
    assert att[2]["covers"] == failed[0]["refs"]
    rulings = _jsonl(d / "rulings" / "rulings.jsonl")
    assert len(rulings) == 2                                                 # no ruling for the failure
    disp = json.loads((d / "change-reviews.json").read_text())["dispositions"]
    assert len(disp) == 2                                                    # it stays open
    import changecheck as C
    _doc, items = R._changecheck_items("xq", rows, HELD, page)
    assert [it["sentence"][:17] for it in items] == ["Sentence number 1"]   # ruled again next run


def test_main_finishes_the_step_runs_the_sample_and_exits_4(study, monkeypatch, capsys):
    d, P = study
    rows, page = _setup(d, 3)
    m = Model(cut=lambda p, n: "Sentence number 1 " in p)
    import stage_cap
    import audit_stage
    monkeypatch.setattr(R, "require_study", lambda slug, P=None: None)
    monkeypatch.setattr(R, "pending", lambda cmd, slug, P=None: 3)
    monkeypatch.setattr(stage_cap, "guard", lambda *a, **k: None)
    monkeypatch.setattr(audit_stage, "Caller", lambda **k: _caller(m))
    real = R.rule_changecheck
    monkeypatch.setattr(R, "rule_changecheck",
                        lambda slug, call, failed=None: real(slug, call, P=P, rows=rows, held=HELD,
                                                             page_html=page, failed=failed))
    assert R.main(["changecheck", "xq", "--seed", "7"]) == 4
    out = capsys.readouterr().out
    assert "RULING_FAILED: 1 sentence(s)" in out and "consistency: re-ran 1 of 2" in out
    step = [s for s in _jsonl(d / "rulings" / "consistency.jsonl") if s["type"] == "step"]
    assert len(step) == 1 and len(step[0]["ruling_ids"]) == 2


def _sample(d, before, model, step, carried):
    return R.consistency_sample("xq", step, d / "rulings" / "rulings.jsonl", before, _caller(model),
                                seed=3, kind="changecheck", carried=carried)


def test_a_step_that_stopped_before_its_sample_is_sampled_when_it_resumes(study):
    d, P = study
    rows, page = _setup(d, 5)
    log, cons = d / "rulings" / "rulings.jsonl", d / "rulings" / "consistency.jsonl"
    m = Model()
    # the first run rules three sentences, then stops (as the S01 step did):
    # no sample, no step line
    calls = {"n": 0}

    def stops(prompt, max_tokens):
        calls["n"] += 1
        if calls["n"] == 4:
            raise A.AuditFailure("spend cap: stopped")
        return m(prompt, max_tokens)
    with pytest.raises(A.AuditFailure):
        R.rule_changecheck("xq", _caller(stops), P=P, rows=rows, held=HELD, page_html=page)
    first = _jsonl(log)
    assert len(first) == 3 and not cons.exists()
    # the stopped run was earlier (its records' ids then differ from the
    # resumed run's, as they would in a real run)
    for i, r in enumerate(first):
        r["at"], r["id"] = "2026-10-22T08:10:4%d+00:00" % i, "stopped%d" % i
    log.write_text("".join(json.dumps(r) + "\n" for r in first))
    carried = R.unsampled(log, cons, "changecheck")
    assert [r["id"] for r in carried] == [r["id"] for r in first]
    # the resumed run rules all five again (changecheck writes its dispositions
    # at the end, so the stopped run left none), and samples all eight logged
    before = R._log_lines(log)
    R.rule_changecheck("xq", _caller(m), P=P, rows=rows, held=HELD, page_html=page)
    line = _sample(d, before, m, "changecheck-20261022T120000Z", carried)
    assert line["ruling_ids"][:3] == ["stopped0", "stopped1", "stopped2"]
    assert set(line["ruling_ids"]) == {r["id"] for r in _jsonl(log)}
    assert line["rulings"] == len(line["ruling_ids"]) >= 4 and line["sampled"] >= 1
    assert line["carried_ids"] == [r["id"] for r in first]
    assert R.unsampled(log, cons, "changecheck") == []                       # nothing carried twice


def test_a_resumed_step_with_nothing_left_to_rule_still_samples_what_the_stopped_one_ruled(study):
    d, P = study
    rows, page = _setup(d, 2)
    log, cons = d / "rulings" / "rulings.jsonl", d / "rulings" / "consistency.jsonl"
    R.rule_changecheck("xq", _caller(Model()), P=P, rows=rows, held=HELD, page_html=page)  # no sample
    carried = R.unsampled(log, cons, "changecheck")
    line = _sample(d, R._log_lines(log), Model(), "changecheck-20261022T130000Z", carried)
    assert line is not None and line["rulings"] == 2 and line["sampled"] == 1


def test_rulings_a_completed_step_sampled_are_not_carried(study):
    d, P = study
    rows, page = _setup(d, 3)
    log, cons = d / "rulings" / "rulings.jsonl", d / "rulings" / "consistency.jsonl"
    before = R._log_lines(log)
    R.rule_changecheck("xq", _caller(Model()), P=P, rows=rows, held=HELD, page_html=page)
    _sample(d, before, Model(), "changecheck-20261022T140000Z", [])
    assert R.unsampled(log, cons, "changecheck") == []
    # a step line written before ruling_ids existed covers what precedes it
    step = [s for s in _jsonl(cons) if s["type"] == "step"][0]
    step.pop("ruling_ids")
    cons.write_text(json.dumps(step) + "\n")
    assert R.unsampled(log, cons, "changecheck") == []
    # other kinds, and rulings before the sample began, are never carried
    assert R.unsampled(log, cons, "gate") == []
    recs = _jsonl(log)
    for r in recs:
        r["at"] = "2026-10-20T10:00:00+00:00"
    log.write_text("".join(json.dumps(r) + "\n" for r in recs))
    cons.unlink()
    assert R.unsampled(log, cons, "changecheck") == []


def test_a_cut_off_repeat_in_the_sample_is_an_unusable_pair_not_a_crash(study):
    d, P = study
    rows, page = _setup(d, 1)
    log = d / "rulings" / "rulings.jsonl"
    R.rule_changecheck("xq", _caller(Model()), P=P, rows=rows, held=HELD, page_html=page)
    line = _sample(d, 0, Model(cut=lambda p, n: True), "changecheck-20261022T150000Z", [])
    assert line["sampled"] == 1 and line["usable"] == 0
    pair = [p for p in _jsonl(d / "rulings" / "consistency.jsonl") if p["type"] == "pair"][0]
    assert pair["usable"] is False and "second reply cut off" in pair["note"]
