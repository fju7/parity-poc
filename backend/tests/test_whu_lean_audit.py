"""Lean WHU, the audit side (backend/scripts/whatholdsup/lean.py, items 1, 2, 3, 5, 6).

No model is called: every run uses a fake `ask`. The switch is turned on per
test (lean.enable) and off again after, so the rest of the suite runs with it
off, as it does in production."""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("audit_stage", WHU / "audit_stage.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
sys.modules.setdefault("audit_stage", A)
import lean  # noqa: E402
import lean_audit as LA  # noqa: E402
import lean_sentences as LS  # noqa: E402
import passage_index as P  # noqa: E402
import reaudit as RA  # noqa: E402


@pytest.fixture
def lean_on(monkeypatch):
    monkeypatch.delenv(lean.ENV_MODELS, raising=False)
    lean.enable(True)
    yield
    lean.enable(False)
    lean._forced = None


def _para(topic: str, n: int) -> str:
    return " ".join("Sentence %d about %s and its own particular wording number %d." % (i, topic, i)
                    for i in range(n))


# A long held text: the bound passage, a relevant passage elsewhere, and filler.
FILLER = "\n\n".join(_para("unrelated agricultural statistics", 12) for _ in range(40))
BOUND = "Of 795 colonoscopies before AI was introduced, 226 detected an adenoma (28.4%)."
RELEVANT = ("Adenoma detection after the introduction of AI fell to 22.4% in the observational "
            "colonoscopy cohort, which the authors call vulnerable to confounding.")
DOC = FILLER + "\n\n" + BOUND + "\n\n" + FILLER + "\n\n" + RELEVANT + "\n\n" + FILLER
HELD = {"demo:S021": DOC}


def _unit(uid, sentence, span=BOUND, sid="S021"):
    return {"id": uid, "part": "page", "sentence": sentence, "sha": A.fingerprint(sentence),
            "row": {"source_id": sid, "span": span}}


class Fake:
    """Holds every sentence, quoting the bound passage; records prompts and models."""

    def __init__(self, verdict_by_model=None):
        self.prompts, self.models = [], []
        self.verdict_by_model = verdict_by_model or {}

    def __call__(self, prompt, max_tokens, model=None):
        self.prompts.append(prompt)
        self.models.append(model)
        if "THE SENTENCES TO READ" in prompt:
            ids = re.findall(r"^\[(u\d+)\]", prompt, re.M)
            v = self.verdict_by_model.get(model, "holds")
            out = {"verdicts": [{"id": i, "verdict": v,
                                 "kind": "Overstated a finding or a source's claim" if v == "finding" else None,
                                 "evidence": [{"source": "S021", "quote": "226 detected an adenoma (28.4%)"}],
                                 "proposed_text": "A narrower sentence." if v == "finding" else None,
                                 "reason": "test"} for i in ids]}
            return json.dumps(out), {"input": len(prompt) // 4, "output": 50, "usd": 0.0}
        return json.dumps({"ruling": "reject", "text": None, "reason": "holds"}), {"input": 50, "output": 20, "usd": 0.0}


# ----------------------------------------------------------------- the switch

def test_the_switch_is_off_by_default(monkeypatch):
    monkeypatch.delenv(lean.ENV, raising=False)
    lean._forced = None
    assert not lean.enabled()
    assert lean.model_for("audit_first") == lean.CURRENT


def test_the_switch_reads_the_environment_and_the_flag(monkeypatch):
    lean._forced = None
    monkeypatch.setenv(lean.ENV, "1")
    assert lean.enabled()
    monkeypatch.delenv(lean.ENV)
    assert lean.strip_flag(["run", "x", "--lean"]) == ["run", "x"] and lean.enabled()
    lean.enable(False)
    lean._forced = None


def test_an_unpriced_model_is_refused(lean_on, monkeypatch):
    monkeypatch.setenv(lean.ENV_MODELS, json.dumps({"audit_first": "claude-haiku-9"}))
    with pytest.raises(lean.UnpricedModel):
        lean.model_for("audit_first")


def test_every_default_model_is_priced_in_the_ledgers_table():
    lean.check_models(lean.STAGE_MODELS)            # raises otherwise
    p = lean.prices()
    assert p[lean.SMALL]["input"] < p[lean.CURRENT]["input"]


# ----------------------------------------------------------------- retrieval

def test_passages_carry_offsets_into_the_held_text():
    ps = P.split(DOC)
    assert ps and all(DOC[p.start:p.end].strip() for p in ps)
    assert all(a.end <= b.start for a, b in zip(ps, ps[1:]))


def test_retrieval_finds_the_relevant_passage_and_not_the_filler():
    r = P.retrieve(DOC, "Adenoma detection fell to 22.4% after AI was introduced", [BOUND])
    got = [DOC[a:b] for a, b, _ in r["retrieved"]]
    assert any("22.4%" in g for g in got)
    assert all("agricultural" not in g for g in got)
    assert any(BOUND in DOC[a:b] for a, b in r["bound"])


def test_nothing_above_threshold_falls_back_to_the_bound_passage_alone():
    r = P.retrieve(DOC, "zebra quokka", [BOUND])
    assert r["below_threshold"] and r["retrieved"] == []
    assert r["bound"] and sum(b - a for a, b in r["bound"]) < len(DOC) / 10


def test_the_audit_never_sends_the_whole_source_and_logs_the_fallback():
    log = []
    u = _unit("u1", "Zebra quokka.")                # nothing in the text is relevant
    docs, _ = LA.batch_inputs("demo", [u], HELD, log=log)
    assert BOUND in docs["S021"] and len(docs["S021"]) < len(DOC) / 10
    assert log and log[0]["below_threshold"] and log[0]["fallback"] == "bound passages alone"


def test_a_bound_span_not_in_the_held_text_still_fails_the_delivery_check():
    u = _unit("u1", "Zebra quokka.", span="a span that is nowhere in the document")
    docs, _ = LA.batch_inputs("demo", [u], HELD)
    with pytest.raises(A.DocumentNotDelivered):
        A.check_delivery(A.delivery_report("demo", [u], HELD, docs))


def test_a_lean_run_sends_passages_and_the_retrieval_log_is_written(tmp_path, lean_on):
    fake = Fake()
    us = [_unit("u1", "Of 795 colonoscopies, 226 detected an adenoma (28.4%).")]
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    reads = [p for p in fake.prompts if "THE SENTENCES TO READ" in p]
    assert reads and all(len(p) < len(DOC) / 4 for p in reads)
    assert (tmp_path / "retrieval.jsonl").read_text().strip()
    assert m["lean_config"]["models"]["audit_first"] == lean.SMALL


def test_with_the_switch_off_the_run_is_unchanged(tmp_path):
    lean._forced = False
    try:
        fake = Fake()
        us = [_unit("u1", "Of 795 colonoscopies, 226 detected an adenoma (28.4%).")]
        m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set())
        assert "lean_config" not in m and "unit_list" not in m and "reaudit" not in m
        assert not (tmp_path / "retrieval.jsonl").exists()
        assert all(c.get("model") is None for c in m["calls"])
        # off: the held text is trimmed by trim() as before, not reduced to passages
        docs, _ = A.batch_inputs("demo", us, HELD)
        assert docs["S021"] == A.trim(DOC, sorted(A.terms([us[0]["sentence"]])), [BOUND])[0]
        assert any(docs["S021"] in p for p in fake.prompts)
    finally:
        lean._forced = None


# ----------------------------------------------------------------- tiering

def test_a_sentence_the_smaller_model_flags_is_decided_by_the_current_model(tmp_path, lean_on):
    fake = Fake(verdict_by_model={lean.SMALL: "finding", lean.CURRENT: "holds"})
    us = [_unit("u1", "Of 795 colonoscopies, 226 detected an adenoma (28.4%).")]
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    vs = [json.loads(l) for l in (tmp_path / "verdicts.jsonl").read_text().splitlines()]
    small = [v for v in vs if v.get("escalated")]
    final = [v for v in vs if "decided_by" in v]
    assert small and small[0]["model"] == lean.SMALL and small[0]["verdict"] == "finding"
    assert final[0]["decided_by"] == lean.CURRENT and final[0]["verdict"] == "holds"
    assert m["state"][us[0]["sha"]] == "holds"
    assert not (tmp_path / "rulings.jsonl").read_text()          # no ruling: the current model held it


def test_a_bound_sentence_called_not_a_correction_is_escalated():
    assert LA.needs_escalation(_unit("u1", "x."), {"verdict": "not_a_correction"})
    unbound = {"id": "u2", "part": "page", "sentence": "See below.", "sha": "s", "row": None}
    assert not LA.needs_escalation(unbound, {"verdict": "not_a_correction"})
    assert LA.needs_escalation(_unit("u1", "x."), {"verdict": A.FAILED_READ})
    assert not LA.needs_escalation(_unit("u1", "x."), {"verdict": "holds"})


def test_a_held_first_read_is_decided_by_the_smaller_model_and_says_so(tmp_path, lean_on):
    fake = Fake()
    us = [_unit("u1", "Of 795 colonoscopies, 226 detected an adenoma (28.4%).")]
    A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set())
    vs = [json.loads(l) for l in (tmp_path / "verdicts.jsonl").read_text().splitlines()]
    assert [v["decided_by"] for v in vs if "decided_by" in v] == [lean.SMALL]


# ----------------------------------------------------------------- caching

def test_a_source_group_of_two_batches_gets_one_stable_document_and_a_cache_prefix(tmp_path, lean_on):
    fake = Fake()
    us = [_unit("u%d" % i, "Sentence %d: 226 detected an adenoma (28.4%%) in the cohort." % i)
          for i in range(1, A.BATCH + 6)]
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    first = [c for c in m["calls"] if c["role"] == "read"]
    assert len(first) == 2 and all(c.get("cache_prefix_chars") for c in first)
    reads = [p for p, mo in zip(fake.prompts, fake.models) if "THE SENTENCES TO READ" in p and mo == lean.SMALL]
    pre = [LA.cache_prefix(p, "S021") for p in reads[:2]]
    assert pre[0] and pre[0] == pre[1]                             # byte for byte the same prefix


def test_cache_blocks_split_the_prompt_without_changing_its_text():
    blocks = lean.cache_blocks("HEAD DOC|TAIL", "HEAD DOC|")
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "".join(b["text"] for b in blocks) == "HEAD DOC|TAIL"
    assert lean.cache_blocks("abc", "zzz") == "abc"


# ----------------------------------------------------------------- incremental re-audit

def _prior(tmp_path, us, state, **kw):
    d = tmp_path / "audit" / "20261029T000000Z"
    d.mkdir(parents=True)
    m = {"status": "complete", "limit": None, "state": state, "model": A.MODEL,
         "read_prompt_sha256": "r", "rule_prompt_sha256": "q", "summary_prompt_sha256": "s",
         "unit_list": [[u["id"], u["part"], u["sha"]] for u in us], "inputs": {"held_texts": {}}}
    m.update(kw)
    (d / "manifest.json").write_text(json.dumps(m))
    return d


def _now(**kw):
    m = {"model": A.MODEL, "read_prompt_sha256": "r", "rule_prompt_sha256": "q",
         "summary_prompt_sha256": "s", "inputs": {"held_texts": {}}}
    m.update(kw)
    return m


def _page(n):
    return [{"id": "u%d" % i, "part": "page", "sentence": "Plain sentence number %d." % i,
             "sha": A.fingerprint("Plain sentence number %d." % i), "row": None} for i in range(1, n + 1)]


def test_an_unchanged_sentence_carries_its_verdict_and_a_changed_one_is_read_with_its_neighbours(tmp_path):
    old = _page(10)
    d = _prior(tmp_path, old, {u["sha"]: "holds" for u in old})
    new = [dict(u) for u in old]
    new[4] = dict(new[4], sentence="A reworded fifth.", sha=A.fingerprint("A reworded fifth."))
    p = RA.plan("demo", new, {}, _now(), d)
    assert p["mode"] == "incremental"
    assert p["read"] == ["u4", "u5", "u6"]
    assert set(p["carry"]) == {u["id"] for u in new} - {"u4", "u5", "u6"}


def test_more_than_a_quarter_changed_falls_back_to_a_full_audit(tmp_path):
    old = _page(8)
    d = _prior(tmp_path, old, {u["sha"]: "holds" for u in old})
    new = [dict(u, sentence="New %d." % i, sha=A.fingerprint("New %d." % i)) if i < 3 else u
           for i, u in enumerate(old)]
    p = RA.plan("demo", new, {}, _now(), d)
    assert p["mode"] == "full" and "more than 25%" in p["why"]


def test_a_changed_prompt_or_held_text_forces_a_read(tmp_path):
    old = _page(4)
    d = _prior(tmp_path, old, {u["sha"]: "holds" for u in old})
    assert RA.plan("demo", old, {}, _now(read_prompt_sha256="other"), d)["mode"] == "full"
    bound = [_unit("u1", "Of 795, 226 detected an adenoma (28.4%).")] + _page(4)[1:]
    d2 = _prior(tmp_path / "b", bound, {u["sha"]: "holds" for u in bound},
                inputs={"held_texts": {"demo:S021": "old sha"}})
    p = RA.plan("demo", bound, HELD, _now(inputs={"held_texts": {"demo:S021": "new sha"}}), d2)
    assert "u1" in p["read"] and "u1" in p["source_changed"]


def test_a_sentence_bound_to_the_same_passage_as_a_changed_one_is_read(tmp_path):
    a = _unit("u1", "Of 795, 226 detected an adenoma (28.4%).")
    b = _unit("u2", "The cohort had 795 colonoscopies.", span="Of 795 colonoscopies before AI was introduced")
    rest = _page(8)[2:]
    old = [a, b] + rest
    d = _prior(tmp_path, old, {u["sha"]: "holds" for u in old})
    a2 = _unit("u1", "Of 795 procedures, 226 detected an adenoma (28.4%).")
    p = RA.plan("demo", [a2, b] + rest, HELD, _now(), d)
    assert "u2" in p["read"]


def test_an_unsettled_sentence_is_read_again(tmp_path):
    old = _page(6)
    st = {u["sha"]: "holds" for u in old}
    st[old[5]["sha"]] = "must_leave_page"
    p = RA.plan("demo", old, {}, _now(), _prior(tmp_path, old, st))
    assert p["read"] == ["u6"] and "u6" not in p["carry"]


def test_a_carried_verdict_is_recorded_as_carried_with_its_source_run(tmp_path, lean_on):
    old = _page(6)
    d = _prior(tmp_path, old, {u["sha"]: "holds" for u in old},
               read_prompt_sha256=A.sha(A.READ_PROMPT.read_text(encoding="utf-8")),
               rule_prompt_sha256=A.sha(A.RULE_PROMPT.read_text(encoding="utf-8")),
               summary_prompt_sha256=A.sha(A.SUMMARY_PROMPT.read_text(encoding="utf-8")))
    out = tmp_path / "audit" / "20261030T000000Z"
    m = A.run("demo", out_dir=out, ask=Fake(), held={}, unit_list=old, cap=1.0, licensed=set(), prior_dir=d)
    assert m["status"] == "complete", m.get("failure")
    vs = [json.loads(l) for l in (out / "verdicts.jsonl").read_text().splitlines()]
    assert vs and all(v["verdict"] == "carried" and v["carried_from"] == d.name for v in vs)
    assert m["reaudit"]["mode"] == "incremental" and m["reaudit"]["carried"] == 6
    assert A.preflight_rows("demo", [], current=old, run_dir=out)[0][1] == A.OK


def test_round_one_style_runs_without_a_unit_list_are_read_from_their_verdicts(tmp_path):
    d = tmp_path / "r"; d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"status": "complete"}))
    (d / "verdicts.jsonl").write_text("\n".join(json.dumps(r) for r in [
        {"unit": "u2", "part": "page", "sha": "b", "round": 1},
        {"unit": "u1", "part": "page", "sha": "a", "round": 0},
        {"unit": "u2", "part": "page", "sha": "c", "round": 2}]))
    assert [u["sha"] for u in RA.prior_units(d)] == ["a", "b"]


# ----------------------------------------------------------------- generated sentences

ISSUE = {"question": "Does exercise reduce depressive symptoms in adults?"}
SOURCES = [{"id": "S001", "title": "A review", "also_called": ["Cochrane review 2013"],
            "access": {"state": "full_text_held", "sections": ["abstract", "results; tables 1-3"],
                       "not_read": ["the appendices"]}},
           {"id": "S002", "title": "A trial", "also_called": ["The TREAD trial"], "access": {"state": "blocked"}}]


def test_the_question_restatement_is_the_question_verbatim_in_its_frame():
    g = LS.generate(ISSUE, SOURCES)
    assert g[0]["sentence"] == "The question is: “Does exercise reduce depressive symptoms in adults?”"


def test_reading_sentences_come_from_sources_json_with_a_numbered_citation():
    s = [g["sentence"] for g in LS.generate(ISSUE, SOURCES)]
    assert "We hold the full text of Cochrane review 2013 [1]." in s
    assert "Of Cochrane review 2013 [1], we read: abstract; results, tables 1-3." in s
    assert "Of Cochrane review 2013 [1], we did not read: the appendices." in s
    assert "We could not obtain The TREAD trial [2]." in s


def test_the_check_passes_matching_sentences_and_stops_a_stale_one():
    g = LS.generate(ISSUE, SOURCES)
    page = [x["sentence"] for x in g] + ["An ordinary sentence."]
    assert LS.check(page, g)[1] == LS.OK
    stale = page + ["We hold the full text of The TREAD trial [2]."]     # the records say blocked
    assert LS.check(stale, g)[1] == LS.BAD
    assert LS.check(page[1:], g)[1] == LS.BAD                              # no question restatement


def test_the_audit_settles_a_generated_sentence_by_code_and_reads_no_model(tmp_path, lean_on, monkeypatch):
    g = LS.generate(ISSUE, SOURCES)
    monkeypatch.setattr(LS, "generated", lambda slug: g)
    q = g[0]["sentence"]
    hand = "We did not search for trials published after 2020."          # protected, not generated
    us = [{"id": "u1", "part": "page", "sentence": q, "sha": A.fingerprint(q), "row": None},
          {"id": "u2", "part": "page", "sentence": hand, "sha": A.fingerprint(hand), "row": None}]
    fake = Fake()
    m = A.run("demo", out_dir=tmp_path, ask=fake, held={}, unit_list=us, cap=1.0, licensed=set())
    assert m["state"][us[0]["sha"]] == LS.RECORD_CHECK
    assert m["state"][us[1]["sha"]] == A.HUMAN_READ_REQUIRED               # a person still reads it
    assert not [p for p in fake.prompts if q in p]


# ----------------------------------------------------------------- the advocate's re-asks

def test_a_lean_requote_is_shown_retrieved_passages_and_off_it_is_trimmed_as_before():
    import source_advocate as SA
    q = "Adenoma detection fell to 22.4% after AI, vulnerable to confounding"
    lean._forced = False
    try:
        assert SA.held_view(DOC, q) == A.trim(DOC, re.findall(r"[A-Za-z][A-Za-z'-]{6,}|\d[\d.,]*%?", q))[0]
    finally:
        lean._forced = None
    lean.enable(True)
    try:
        log = []
        got = SA.held_view(DOC, q, log)
        assert RELEVANT in got and len(got) < len(DOC) / 10 and log[0]["retrieved"]
        log = []
        SA.held_view(DOC, "zebra quokka", log)
        assert log == [{"below_threshold": True, "fallback": "trim"}]
    finally:
        lean.enable(False)
        lean._forced = None
