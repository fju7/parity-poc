"""The ruling-model consistency sample (2026-10-21).

After each ruling step a seeded random 20% of its rulings (at least 1) is
re-run with the identical payload; each pair is logged, the second ruling is
never applied, and agreement is reported per step and for the issue. The model
is a stub: nothing is spent.
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


CS = _load("consistency_t", WHU / "consistency.py")
import ruling as R  # noqa: E402  (consistency.ruling_reask imports it by this name)

DOC = "Background. The trial found that the intervention reduced weight by 2 kg over 12 weeks. More."
HELD = {"S1": DOC}
SPAN = "the intervention reduced weight by 2 kg over 12 weeks"


def _row(i):
    return {"sentence": "Sentence number %d says the intervention cut weight by 2 kg." % i,
            "on_page": True, "source_id": "S1", "span": SPAN}


class Stub:
    """The model: replies by prompt, so the same payload can be answered alike or not."""

    def __init__(self, decide):
        self.decide, self.prompts, self.roles = decide, [], []

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        self.roles.append(role)
        return json.dumps(self.decide(prompt, len(self.prompts))), {"usd": 0.0}


@pytest.fixture
def study(tmp_path, monkeypatch):
    d = tmp_path / "WHU-P99-xq"
    d.mkdir()
    import source_store
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    return d, types.SimpleNamespace(is_study=lambda slug: slug == "xq")


def _changecheck_step(d, P, monkeypatch, n, decide, seed=None):
    import changecheck as C
    monkeypatch.setattr(C, "record_path", lambda slug: d / "change-reviews.json")
    rows = {"k%d" % i: _row(i) for i in range(n)}
    page = "<html><body><p>%s</p></body></html>" % " ".join(r["sentence"] for r in rows.values())
    fs = [{"sentence": r["sentence"], "kind": "NEW_AND_UNBOUND", "why": "w%d" % i, "other": ""}
          for i, r in enumerate(rows.values())]
    (d / "change-reviews.json").write_text(json.dumps({"reviews": [{"sha": C.page_sha(page), "findings": fs}]}))
    stub = Stub(decide)
    log = d / "rulings" / "rulings.jsonl"
    before = R._log_lines(log)
    R.rule_changecheck("xq", stub, P=P, rows=rows, held=HELD, page_html=page)
    line = R.consistency_sample("xq", "changecheck-20261021T010000Z", log, before, stub, seed=seed)
    return stub, line


def _pairs(d):
    return [r for r in CS.load(d / "rulings" / "consistency.jsonl") if r["type"] == "pair"]


def test_the_sample_is_twenty_percent_at_least_one():
    assert [CS.sample_size(n) for n in (0, 1, 4, 5, 6, 10, 13)] == [0, 1, 1, 1, 2, 2, 3]
    assert CS.choose(10, 7) == CS.choose(10, 7)                          # seeded: reproducible
    assert len(set(CS.choose(13, 7))) == 3


def test_a_step_reruns_a_seeded_sample_with_the_identical_payload_and_logs_each_pair(study, monkeypatch):
    d, P = study
    stub, line = _changecheck_step(d, P, monkeypatch, 10,
                                   lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"})
    assert len(stub.prompts) == 12                                        # 10 rulings + 2 repeats
    firsts, repeats = stub.prompts[:10], stub.prompts[10:]
    assert all(p in firsts for p in repeats)                              # identical prompts
    assert stub.roles[10:] == ["rule-changecheck-repeat"] * 2
    recs = [json.loads(l) for l in (d / "rulings" / "rulings.jsonl").read_text().splitlines()]
    assert len(recs) == 10 and all(r.get("id") for r in recs)            # the repeat is never a ruling
    want_seed = CS.seed_for("changecheck-20261021T010000Z")
    want = [recs[i]["id"] for i in CS.choose(10, want_seed)]
    assert line["seed"] == want_seed and line["sampled_ids"] == want      # seed and ids logged
    pairs = _pairs(d)
    assert [p["ruling_id"] for p in pairs] == want
    for p in pairs:
        assert p["first"] == {"ruling": "reject", "text": None} == p["second"]
        assert p["agree"] and p["applied"] is False and p["seed"] == want_seed
    assert line["agreement"] == 1.0


def test_a_disagreement_is_logged_and_never_applied(study, monkeypatch):
    d, P = study

    def decide(pr, n):
        if n <= 6:
            return {"ruling": "amend", "text": "First text.", "reason": "r"}
        return {"ruling": "amend", "text": "A different text.", "reason": "r"} if n == 7 else \
            {"ruling": "reject", "text": None, "reason": "r"}
    _changecheck_step(d, P, monkeypatch, 6, decide, seed=11)
    p1, p2 = _pairs(d)
    assert p1["first"]["text"] == "First text." and p1["second"]["text"] == "A different text."
    assert p1["agree_decision"] and not p1["agree"]
    assert p2["second"]["ruling"] == "reject" and not p2["agree_decision"]
    disp = json.loads((d / "change-reviews.json").read_text())["dispositions"]
    assert {x["ruling_text"] for x in disp} == {"First text."}            # the second is not applied
    import applied_check as AC
    assert all(r["text"] == "First text." for r in AC.load_rulings(d))     # nor expected on the page


def test_an_unusable_second_reply_is_counted_apart(study, monkeypatch):
    d, P = study
    _changecheck_step(d, P, monkeypatch, 3,
                      lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"} if n <= 3 else
                      {"ruling": "maybe"})
    [p] = _pairs(d)
    assert p["usable"] is False and "not usable" in p["note"]
    rep = CS.report(d / "rulings" / "consistency.jsonl")
    assert rep["issue"]["pairs"] == 1 and rep["issue"]["usable"] == 0 and rep["issue"]["agreement"] is None


def test_the_report_gives_agreement_per_step_and_for_the_issue(study, monkeypatch, capsys):
    d, P = study
    _changecheck_step(d, P, monkeypatch, 5, lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"})
    log = d / "rulings" / "rulings.jsonl"
    before = R._log_lines(log)
    old = "In the UPDATE trial, the intervention cut weight by 2 kg in 12 weeks."
    new = "In the trial, the intervention cut weight by 2 kg in 12 weeks."
    later = "The UPDATE authors call the effect modest."
    with open(log, "a") as f:
        f.write(json.dumps({"at": "2026-10-21T00:00:00+00:00", "ruling_kind": "conclusion", "ruling": "amend",
                            "text": new, "inputs": {"sentence": old}}) + "\n")
    before = R._log_lines(log)
    page = "<html><body><p>An opening sentence stands here.</p><p>%s %s</p></body></html>" % (new, later)
    stub = Stub(lambda pr, n: {"ruling": "amend", "text": "Its authors call it modest." if n == 1 else "Other.",
                               "reason": "r"})
    R.rule_dangling("xq", stub, P=P, rows={"k1": dict(_row(1), sentence=later)}, held=HELD, page_html=page, case=d)
    R.consistency_sample("xq", "dangling-20261021T020000Z", log, before, stub)
    rep = CS.report(d / "rulings" / "consistency.jsonl")
    assert rep["steps"]["changecheck-20261021T010000Z"]["agreement"] == 1.0
    assert rep["steps"]["dangling-20261021T020000Z"]["agreement"] == 0.0
    assert rep["issue"]["pairs"] == 2 and rep["issue"]["agreement"] == 0.5
    CS.print_report("xq", d / "rulings" / "consistency.jsonl")
    out = capsys.readouterr().out
    assert "changecheck-20261021T010000Z" in out and "issue: 2 pair(s)" in out and "50%" in out


def test_a_changed_prompt_refuses_the_sample(study, monkeypatch):
    d, P = study
    real = R.prompt_sha
    # the rulings are made under one prompt; by the time of the sample it differs
    monkeypatch.setattr(R, "consistency_sample", lambda *a, **k: None)
    _changecheck_step(d, P, monkeypatch, 2, lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"})
    monkeypatch.undo()
    monkeypatch.setattr(R, "prompt_sha", lambda kind, grouped=False: "changed-" + real(kind, grouped))
    with pytest.raises(SystemExit) as e:
        R.consistency_sample("xq", "s", d / "rulings" / "rulings.jsonl", 0, Stub(lambda pr, n: {}))
    assert "prompt changed" in str(e.value)
    assert not (d / "rulings" / "consistency.jsonl").exists()


def test_an_audit_runs_rulings_are_sampled_through_the_audit_prompt(study, monkeypatch):
    d, P = study
    import audit_stage as A
    run = d / "audit" / "20261021T030000Z"
    run.mkdir(parents=True)
    psha = A.sha(A.RULE_PROMPT.read_text(encoding="utf-8"))
    payload = {k: "x" for k in A.RULE_FIELDS}
    (run / "rulings.jsonl").write_text("".join(json.dumps(
        {"unit": "u%d" % i, "round": 1, "at": "t%d" % i, "prompt_sha256": psha, "inputs": dict(payload, sentence="s%d" % i),
         "ruling": "reject", "text": None, "reason": "r"}) + "\n" for i in range(5)))
    stub = Stub(lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"})
    monkeypatch.setattr(A, "Caller", lambda **kw: stub)
    import stage_cap, publish
    monkeypatch.setattr(stage_cap, "guard", lambda *a, **k: None)
    monkeypatch.setattr(publish, "is_study", lambda slug: True)
    assert CS.main(["audit", "xq", "20261021T030000Z"]) == 0
    k = CS.choose(5, CS.seed_for("audit-20261021T030000Z"))[0]
    assert stub.prompts == [A.build_rule_prompt(dict(payload, sentence="s%d" % k))]   # the identical payload
    [p] = _pairs(d)
    assert p["kind"] == "audit" and p["agree"] and p["step"] == "audit-20261021T030000Z"
    with pytest.raises(SystemExit):                                       # sampled once
        CS.main(["audit", "xq", "20261021T030000Z"])


def test_ruling_py_runs_the_sample_after_every_mode_and_counts_it_in_the_stage_cap():
    import inspect
    src = inspect.getsource(R.main)
    assert "consistency_sample(" in src and "n + CS.sample_size(n + len(carried))" in src
    assert src.index("done = fn(a.slug, call, failed=failed)") < src.index("consistency_sample(")


# --- current and superseded pairs are reported apart (2026-10-21) ---------

def test_pairs_from_superseded_rulings_are_shown_apart_from_current_ones(study, monkeypatch, capsys):
    d, P = study
    import supersede as SU
    _changecheck_step(d, P, monkeypatch, 5, lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"})
    SU.supersede(d, "re-ruled", "Claude Code (session test)", only=["rulings"])
    assert not (d / "rulings" / "rulings.jsonl").exists()
    (d / "change-reviews.json").unlink()                                   # a fresh changecheck step
    _changecheck_step(d, P, monkeypatch, 5, lambda pr, n: {"ruling": "amend", "text": "T.", "reason": "r"} if n <= 5
                      else {"ruling": "reject", "text": None, "reason": "r"})
    log = d / "rulings" / "consistency.jsonl"
    assert CS.report(log)["issue"]["pairs"] == 2                          # without the case: every pair
    rep = CS.report(log, d)
    assert rep["issue"]["pairs"] == 1 and rep["issue"]["agree_decision"] == 0     # the current step only
    assert rep["superseded"]["rates"]["pairs"] == 1 and rep["superseded"]["rates"]["agreement"] == 1.0
    assert rep["not found"]["rates"]["pairs"] == 0
    assert rep["matched_by_content"] == {"current": 0, "superseded": 0, "not found": 0}
    CS.print_report("xq", log, d)
    out = capsys.readouterr().out
    assert "CURRENT rulings" in out and "SUPERSEDED rulings (not counted above)" in out
    assert out.index("issue: 1 pair(s)") < out.index("superseded: 1 pair(s)")


def test_a_pair_logged_with_no_ruling_id_is_matched_by_payload_and_first_ruling(study, monkeypatch):
    d, P = study
    _changecheck_step(d, P, monkeypatch, 1, lambda pr, n: {"ruling": "reject", "text": None, "reason": "r"})
    log = d / "rulings" / "consistency.jsonl"
    rows = CS.load(log)
    for r in rows:                                                         # as the retroactive sample logged them
        if r["type"] == "pair":
            r["ruling_id"] = None
    log.write_text("".join(json.dumps(r) + "\n" for r in rows))
    rep = CS.report(log, d)
    assert rep["issue"]["pairs"] == 1 and rep["matched_by_content"]["current"] == 1
    rows[0]["first"] = {"ruling": "accept", "text": "Other."}             # no ruling made that decision
    log.write_text("".join(json.dumps(r) + "\n" for r in rows))
    rep = CS.report(log, d)
    assert rep["issue"]["pairs"] == 0 and rep["not found"]["rates"]["pairs"] == 1


def test_a_withdrawn_audit_runs_pairs_are_superseded(study):
    d, P = study
    run = d / "audit" / "20261021T030000Z"
    run.mkdir(parents=True)
    rec = {"unit": "u1", "round": 1, "at": "t", "inputs": {"sentence": "s"}, "ruling": "reject", "text": None}
    (run / "rulings.jsonl").write_text(json.dumps(rec) + "\n")
    (run / "manifest.json").write_text(json.dumps({"withdrawn": {"reason": "bad run"}}))
    log = d / "rulings" / "consistency.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"type": "pair", "step": "audit-20261021T030000Z", "kind": "audit",
                               "ruling_id": CS.record_id(rec), "usable": True, "agree": True,
                               "agree_decision": True}) + "\n")
    rep = CS.report(log, d)
    assert rep["issue"]["pairs"] == 0 and rep["superseded"]["rates"]["pairs"] == 1


def test_every_record_ruling_py_logs_carries_an_id():
    """One writer appends to the ruling log, and it sets the id first."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(R))
    appends = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "open"
               and len(n.args) > 1 and getattr(n.args[1], "value", "") == "a"]
    assert len(appends) == 1
    src = inspect.getsource(R._append)                     # the one writer, for both logs
    assert src.index('rec["id"] = ') < src.index('open(path, "a"')
    assert "_append(log, rec)" in inspect.getsource(R.rule)
