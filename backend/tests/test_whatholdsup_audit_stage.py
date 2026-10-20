"""The audit stage (docs/whu-audit-stage-design.md, approved 2026-10-19).

No model is called: every run here uses a fake `ask` that answers from the
prompt it is given, and records every prompt, so the ruling model's inputs are
asserted from what was actually sent."""
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

DOC = ("Of 795 colonoscopies before AI was introduced, 226 detected an adenoma (28.4%). "
       "After introduction, 145 of 648 did (22.4%). The study is retrospective and "
       "observational, and the authors note that it is vulnerable to confounding.")
HELD = {"demo:S021": DOC}


def _unit(uid, sentence, sid="S021", span="226 detected an adenoma (28.4%)"):
    return {"id": uid, "part": "page", "sentence": sentence, "sha": A.fingerprint(sentence),
            "row": {"source_id": sid, "span": span}}


# ----------------------------------------------------------------- verbatim

def test_a_fabricated_quote_fails_the_verbatim_check():
    v = {"verdict": "holds", "evidence": [{"source": "S021", "quote": "the detection rate fell by a third"}]}
    assert A.bad_quotes(v, {"S021": DOC}, {}, None)


def test_a_genuine_quote_passes_with_typography_and_ligatures_folded():
    v = {"verdict": "holds", "evidence": [{"source": "S021", "quote": "it is vulnerable to confounding"}]}
    assert A.bad_quotes(v, {"S021": DOC}, {}, None) == []
    lig = {"verdict": "holds", "evidence": [{"source": "S1", "quote": "Effects appeared larger"}]}
    assert A.bad_quotes(lig, {"S1": "Eﬀects appeared larger for women"}, {}, None) == []


def test_a_quote_naming_a_document_not_shown_fails():
    v = {"verdict": "holds", "evidence": [{"source": "S999", "quote": "226 detected an adenoma"}]}
    assert A.bad_quotes(v, {"S021": DOC}, {}, None)


def test_a_verdict_with_no_evidence_fails():
    assert A.bad_quotes({"verdict": "finding", "evidence": []}, {"S021": DOC}, {}, None)


# ----------------------------------------------------------------- preflight

def _manifest(tmp_path, **kw):
    d = tmp_path / "20261019T000000Z"; d.mkdir()
    m = {"status": "complete", "state": {}, "limit": None}
    m.update(kw)
    (d / "manifest.json").write_text(json.dumps(m))
    return d


def test_preflight_blocks_an_issue_with_no_audit(monkeypatch):
    monkeypatch.setattr(A, "latest_run", lambda slug: None)
    rows = A.preflight_rows("demo", [], current=[_unit("u1", "A sentence.")])
    assert rows[0][0] == "audit complete" and rows[0][1] == A.BAD


def test_preflight_blocks_a_sentence_with_no_verdict_on_its_current_wording(tmp_path):
    u = _unit("u1", "Of 795 colonoscopies, 226 found an adenoma.")
    d = _manifest(tmp_path, state={A.fingerprint("An older wording."): "holds"})
    assert A.preflight_rows("demo", [], current=[u], run_dir=d)[0][1] == A.BAD


def test_preflight_blocks_a_corrected_or_cut_sentence_still_on_the_page(tmp_path):
    u = _unit("u1", "The rate fell sharply.")
    d = _manifest(tmp_path, state={u["sha"]: "must_leave_page"})
    assert A.preflight_rows("demo", [], current=[u], run_dir=d)[0][1] == A.BAD


def test_preflight_blocks_a_failed_run_and_a_dry_run(tmp_path):
    u = _unit("u1", "x.")
    assert A.preflight_rows("demo", [], current=[u], run_dir=_manifest(tmp_path, status="failed"))[0][1] == A.BAD
    (tmp_path / "20261019T000000Z" / "manifest.json").unlink()
    (tmp_path / "20261019T000000Z").rmdir()
    d = _manifest(tmp_path, limit=20, state={u["sha"]: "holds"})
    assert A.preflight_rows("demo", [], current=[u], run_dir=d)[0][1] == A.BAD


def test_preflight_passes_only_when_every_current_sentence_is_settled(tmp_path):
    us = [_unit("u1", "One."), _unit("u2", "Two.")]
    d = _manifest(tmp_path, state={us[0]["sha"]: "holds", us[1]["sha"]: "holds_by_ruling"})
    assert A.preflight_rows("demo", [], current=us, run_dir=d)[0][1] == A.OK


def test_an_issue_published_before_adoption_is_skipped_by_name():
    rows = A.preflight_rows("demo", [{"issue": "demo", "action": "publish", "at": "2026-08-30T19:57:20+00:00"}],
                            current=[])
    assert rows[0][1] == A.OK and rows[0][2].startswith("SKIPPED")


def test_publish_preflight_carries_the_row():
    src = (WHU / "publish.py").read_text()
    assert "audit_stage.preflight_rows(slug, load_record())" in src
    assert '("audit complete", BAD,' in src


# ----------------------------------------------------------------- the run

class FakeModel:
    """Answers the reading prompt with a finding for every sentence, quoting the
    document verbatim, and the ruling prompt with 'accept' and a new wording.
    Records every prompt it is sent."""

    def __init__(self, always_finding=True):
        self.prompts = []
        self.n = 0
        self.always_finding = always_finding

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        if "THE SENTENCES TO READ" in prompt:
            ids = re.findall(r"^\[(u\d+)\]", prompt, re.M)
            verdict = "finding" if self.always_finding else "holds"
            out = {"verdicts": [{"id": i, "verdict": verdict,
                                 "kind": "Overstated a finding or a source's claim" if verdict == "finding" else None,
                                 "evidence": [{"source": "S021", "quote": "it is vulnerable to confounding"}],
                                 "proposed_text": "A narrower sentence." if verdict == "finding" else None,
                                 "reason": "test"} for i in ids]}
            return json.dumps(out), {"input": 100, "output": 50, "usd": 0.0}
        self.n += 1
        return json.dumps({"ruling": "accept", "text": "Corrected wording %d." % self.n,
                           "reason": "the source says vulnerable to confounding"}), {"input": 50, "output": 20, "usd": 0.0}


def test_a_sentence_still_failing_after_three_rounds_is_cut_and_logged(tmp_path):
    fake = FakeModel(always_finding=True)
    u = _unit("u1", "The study proves that AI deskills doctors.")
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=[u], cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    reads = [p for p in fake.prompts if "THE SENTENCES TO READ" in p and "second" not in p]
    assert len([p for p in fake.prompts if "THE FINDING:" in p]) == A.MAX_ROUNDS
    cuts = [json.loads(l) for l in (tmp_path / "cuts.jsonl").read_text().splitlines()]
    assert len(cuts) == 1 and len(cuts[0]["rounds"]) == A.MAX_ROUNDS
    assert "3 read-and-correct rounds" in cuts[0]["why"]
    assert m["state"][u["sha"]] == "must_leave_page"
    assert len(reads) == A.MAX_ROUNDS


def test_a_corrected_sentence_that_then_holds_is_not_cut(tmp_path):
    class Once(FakeModel):
        def __call__(self, prompt, max_tokens):
            if "THE SENTENCES TO READ" in prompt and "Corrected wording" in prompt:
                self.always_finding = False
            return super().__call__(prompt, max_tokens)
    fake = Once()
    u = _unit("u1", "The study proves that AI deskills doctors.")
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=[u], cap=1.0, licensed=set())
    assert m["status"] == "complete"
    assert (tmp_path / "cuts.jsonl").read_text() == ""
    assert m["state"][A.fingerprint("Corrected wording 1.")] == "holds"


def test_a_reply_that_is_not_json_stops_the_run(tmp_path):
    m = A.run("demo", out_dir=tmp_path, ask=lambda p, n: ("not json at all", {"usd": 0.0}),
              held=HELD, unit_list=[_unit("u1", "x is y.")], cap=1.0, licensed=set())
    assert m["status"] == "failed"
    assert A.preflight_rows("demo", [], current=[_unit("u1", "x is y.")], run_dir=tmp_path)[0][1] == A.BAD


# ----------------------------------------------------------------- the ruling model's inputs

FORBIDDEN = {
    "answer_key": "KEY-CONCLUSION: exercise reduces depressive symptoms, GRADE low",
    "source_review": "Cochrane review CD004366 (the drawn review)",
    "other_systems": "Claude Research answered: exercise is as good as drugs",
    "judge_output": "M1 judge label: Overstates",
    "study_file": "study/whu-reliability/runs/prep2/items.json",
}


def test_the_ruling_payload_is_the_allow_list_and_nothing_else():
    finding = {"kind": "Overstated a finding or a source's claim", "reason": "r", "proposed_text": "p",
               "evidence": [{"source": "S021", "quote": "it is vulnerable to confounding"}], **FORBIDDEN}
    payload = A.ruling_payload(finding, "The study proves it.", {"S021": DOC}, {})
    assert tuple(payload) == A.RULE_FIELDS
    sent = json.dumps(payload) + A.build_rule_prompt(payload)
    for v in FORBIDDEN.values():
        assert v not in sent
    assert "S021" not in sent                 # not even the source id travels


def test_what_the_ruling_model_was_actually_sent_contains_none_of_the_forbidden_inputs(tmp_path):
    fake = FakeModel(always_finding=True)
    u = _unit("u1", "The study proves that AI deskills doctors.")
    u["row"].update(FORBIDDEN)                  # smuggled into the binding row
    A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=[u], cap=1.0, licensed=set())
    rule_prompts = [p for p in fake.prompts if "THE FINDING:" in p]
    assert rule_prompts
    for p in rule_prompts:
        for v in FORBIDDEN.values():
            assert v not in p
        assert "demo" not in p and "S021" not in p and "BINDING" not in p
        assert "study/" not in p and "answer key" not in p.lower()


def test_prompts_are_identified_by_sha256_on_the_manifest(tmp_path):
    m = A.run("demo", out_dir=tmp_path, ask=FakeModel(always_finding=False), held=HELD,
              unit_list=[_unit("u1", "Of 795, 226 detected an adenoma.")], cap=1.0, licensed=set())
    assert m["read_prompt_sha256"] == A.sha(A.READ_PROMPT.read_text(encoding="utf-8"))
    assert m["rule_prompt_sha256"] == A.sha(A.RULE_PROMPT.read_text(encoding="utf-8"))


def test_the_spend_cap_stops_a_call_before_it_is_made(tmp_path, monkeypatch):
    class Raw:
        class messages:
            @staticmethod
            def count_tokens(**kw):
                return type("C", (), {"input_tokens": 10_000_000})()
    c = A.Caller.__new__(A.Caller)
    c.cap, c.issue, c.calls, c._ask, c._start, c._raw = 1.0, "demo", [], None, 0.0, Raw()
    monkeypatch.setattr(A.Caller, "_spent", lambda self: 0.0)
    with pytest.raises(A.AuditFailure, match="spend cap"):
        c("prompt", 1000, "read")


def test_the_dry_run_refuses_to_write_inside_issues():
    with pytest.raises(SystemExit):
        A.main(["run", "deskilling", "--dry-run", "--limit", "2", "--out", str(ROOT / "issues" / "x")])


def test_a_finding_that_no_document_is_held_needs_no_quotation():
    v = {"verdict": "finding", "kind": "Rested on a document we do not hold", "evidence": []}
    assert A.bad_quotes(v, {}, {}, None) == []


# ----------------------------------------------------------------- licensed sources

LICENSED_TEXT = "NCCN-LICENSED-PASSAGE: category 1 preferred for ribociclib zx81"


def test_a_licensed_source_never_appears_in_any_model_request(tmp_path):
    """The licensed text is planted everywhere it could leak from: the held
    texts and the binding's own span. Every prompt sent is inspected."""
    fake = FakeModel(always_finding=True)
    held = {"demo:S021": DOC, "demo:S001": "Preamble. " + LICENSED_TEXT + " More licensed text."}
    mixed = _unit("u1", "The guideline prefers it, and the study is retrospective.")
    mixed["row"]["also_rests_on"] = [{"source_id": "S001", "span": LICENSED_TEXT}]
    only = _unit("u2", "The guideline assigns category 1.", sid="S001", span=LICENSED_TEXT)
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=held, unit_list=[mixed, only], cap=1.0,
              licensed={"S001"})
    assert m["status"] == "complete", m.get("failure")
    assert fake.prompts
    for p in fake.prompts:
        assert LICENSED_TEXT not in p
        assert "zx81" not in p
    assert m["licensed_sources_never_sent"] == ["S001"]
    v = [json.loads(l) for l in (tmp_path / "verdicts.jsonl").read_text().splitlines()]
    assert any(x.get("read_without_licensed_sources") == ["S001"] for x in v if x["unit"] == "u1")


def test_a_sentence_bound_only_to_a_licensed_source_needs_a_human_read(tmp_path):
    fake = FakeModel(always_finding=False)
    only = _unit("u1", "The guideline assigns category 1.", sid="S001", span=LICENSED_TEXT)
    m = A.run("demo", out_dir=tmp_path, ask=fake, held={"demo:S001": LICENSED_TEXT}, unit_list=[only],
              cap=1.0, licensed={"S001"})
    assert m["status"] == "complete"
    assert m["state"][only["sha"]] == A.HUMAN_READ_REQUIRED
    assert fake.prompts == []                      # nothing was sent at all
    row = A.preflight_rows("demo", [], current=[only], run_dir=tmp_path)[0]
    assert row[1] == A.BAD and "human read" in row[2]
    (tmp_path / "human_reads.jsonl").write_text(json.dumps(
        {"sha": only["sha"], "verdict": "holds", "by": "Fred Ugast", "at": "2026-10-20T10:00:00+00:00"}) + "\n")
    assert A.preflight_rows("demo", [], current=[only], run_dir=tmp_path)[0][1] == A.OK


def test_the_licence_is_read_from_the_record_not_hard_coded():
    assert "S001" in A.licensed_ids("cdk46")
    assert "S001" not in A.licensed_ids("deskilling")
    src = (WHU / "audit_stage.py").read_text()
    assert '"S001"' not in src and "'S001'" not in src


# ----------------------------------------------------------------- summaries against the body

def test_card_and_meta_sentences_are_read_against_the_page_body_not_the_sources(tmp_path):
    fake = FakeModel(always_finding=False)
    page = _unit("u1", "In our reading, the evidence usually offered for it is weak.")
    card = {"id": "u2", "part": "card", "sentence": "The evidence usually offered is weak.",
            "sha": A.fingerprint("The evidence usually offered is weak."), "row": None}

    def ask(prompt, n):
        if "SUMMARIES of that page" in prompt:
            assert "DOCUMENT PAGE" in prompt and page["sentence"] in prompt
            assert DOC not in prompt                       # no source text
            return json.dumps({"verdicts": [{"id": "u2", "verdict": "finding", "kind": A.SUMMARY_KIND,
                                             "evidence": [{"source": "PAGE", "quote": "the evidence usually offered for it is weak"}],
                                             "proposed_text": page["sentence"], "reason": "drops the hedge"}]}), {"usd": 0.0}
        return fake(prompt, n)
    m = A.run("demo", out_dir=tmp_path, ask=ask, held=HELD, unit_list=[card, page], cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    v = [json.loads(l) for l in (tmp_path / "verdicts.jsonl").read_text().splitlines()]
    assert any(x["unit"] == "u2" and x["kind"] == A.SUMMARY_KIND for x in v)


# ------------------------------------- budget ruling of 20 October 2026 (protocol rev 26)

class PerUnit:
    """A reader that gives a finding on a unit in `flag` at its original
    wording, and holds otherwise (so a re-read gives the same verdict, as a
    reader judging the text would); the ruling accepts a new wording. Records
    the unit ids of every reading call (None for a ruling call), in order."""

    def __init__(self, flag=()):
        self.flag, self.reads, self.n = set(flag), [], 0

    def __call__(self, prompt, max_tokens):
        if "THE SENTENCES TO READ" in prompt:
            found = re.findall(r"^\[(u\d+)\] \(.*?\)\nSENTENCE: (.*)$", prompt, re.M)
            ids = [i for i, _s in found]
            self.reads.append(ids)
            out = []
            for i, sentence in found:
                f = i in self.flag and not sentence.startswith("Corrected wording")
                out.append({"id": i, "verdict": "finding" if f else "holds",
                            "kind": "Overstated a finding or a source's claim" if f else None,
                            "evidence": [{"source": "S021", "quote": "it is vulnerable to confounding"}],
                            "proposed_text": "A narrower sentence." if f else None, "reason": "test"})
            return json.dumps({"verdicts": out}), {"input": 100, "output": 50, "usd": 0.0}
        self.reads.append(None)
        self.n += 1
        return json.dumps({"ruling": "accept", "text": "Corrected wording %d." % self.n,
                           "reason": "the source says vulnerable to confounding"}), {"input": 50, "output": 20, "usd": 0.0}


def _many(n=30):
    return [_unit("u%d" % i, "Sentence number %d says 28.4%% of something." % i) for i in range(1, n + 1)]


def _second_read_ids(fake, manifest):
    roles = [c["role"] for c in manifest["calls"]]
    assert len(roles) == len(fake.reads)
    return [i for ids, role in zip(fake.reads, roles) if role.startswith("second-read") for i in ids]


def test_the_second_reader_reads_exactly_the_flagged_sentences_and_the_seeded_sample(tmp_path):
    import random
    us = _many(30)
    fake = PerUnit(flag={"u2", "u7", "u19"})
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set(), seed=4242)
    assert m["status"] == "complete", m.get("failure")
    held_first = [u["id"] for u in us if u["id"] not in {"u2", "u7", "u19"}]
    expected_sample = random.Random(4242).sample(held_first, round(A.SECOND_SHARE * len(held_first)))
    expected = {"u2", "u7", "u19"} | set(expected_sample)
    # What the model was actually called on in the second-read phase:
    called = _second_read_ids(fake, m)
    assert sorted(called) == sorted(expected) and len(called) == len(expected) == 6
    # ... and what was logged, with the seed and the sample on the manifest.
    logged = [json.loads(l) for l in (tmp_path / "second_reads.jsonl").read_text().splitlines()]
    assert sorted(r["unit"] for r in logged) == sorted(expected)
    assert {r["unit"] for r in logged if r["why_read"] == "had a finding"} == {"u2", "u7", "u19"}
    assert m["second_read"]["seed"] == m["second_seed"] == 4242
    assert m["second_read"]["sampled_units"] == expected_sample
    assert m["second_read"]["holds_pool"] == 27 and m["second_read"]["had_finding"] == 3
    # A flagged sentence is read again at its corrected wording, not the old one.
    flagged_second = [r for r in logged if r["unit"] == "u2"][0]
    assert flagged_second["sha"] == A.fingerprint(m["progress"]["done"]["u2"]["sentence"])
    assert m["progress"]["done"]["u2"]["sentence"].startswith("Corrected wording")


def test_the_same_seed_draws_the_same_sample_and_another_seed_does_not(tmp_path):
    runs = [A.run("demo", out_dir=tmp_path / str(s) / str(k), ask=PerUnit(), held=HELD, unit_list=_many(60),
                  cap=1.0, licensed=set(), seed=s)["second_read"]["sampled_units"]
            for s, k in ((1, "a"), (1, "b"), (2, "c"))]
    assert runs[0] == runs[1] and runs[0] != runs[2] and len(runs[0]) == 6


def _day_cap_after(n):
    """A stubbed day cap: lets n calls through, then stops the run the way
    spend_ledger.check_day_cap does, with OverCap."""
    count = {"n": 0}

    def cap(about):
        count["n"] += 1
        if count["n"] > n:
            raise A.S.OverCap("DAY cap $25.00 reached (stub)")
    return cap


def _first_reads(path):
    return [json.loads(l)["unit"] for l in (path / "verdicts.jsonl").read_text().splitlines()
            if json.loads(l)["round"] == 1]


@pytest.mark.parametrize("stop_after", [3, 2])
def test_a_run_stopped_by_the_day_cap_resumes_next_day_without_rereading_finished_sentences(tmp_path, stop_after):
    us = _many(30)                      # two reading batches: u1-u20, u21-u30
    flag = {"u1", "u2"}
    whole = A.run("demo", out_dir=tmp_path / "whole", ask=PerUnit(flag), held=HELD, unit_list=us,
                  cap=1.0, licensed=set())
    # Day one: calls are read batch 1, rule u1, rule u2, read batch 2, ...
    # stop_after=3 stops between the batches; stop_after=2 stops before u2's ruling.
    run_dir = tmp_path / "stopped"
    day1 = PerUnit(flag)
    m1 = A.run("demo", out_dir=run_dir, ask=day1, held=HELD, unit_list=us, cap=1.0, licensed=set(),
               day_cap=_day_cap_after(stop_after))
    assert m1["status"] == "failed" and m1["stopped_by"] == "day cap" and "OverCap" in m1["failure"]
    finished = set(m1["progress"]["done"])
    # Day two: same inputs, a fresh day, no cap reached.
    day2 = PerUnit(flag)
    day2.n = day1.n                     # the ruling model's wordings carry on from day one
    m2 = A.run("demo", out_dir=run_dir, ask=day2, held=HELD, unit_list=us, cap=1.0, licensed=set(), resume=True)
    assert m2["status"] == "complete", m2.get("failure")
    reread = {i for ids in day2.reads if ids for i in ids} & finished
    second = set(m2["progress"]["second"]["flagged"] + m2["progress"]["second"]["sampled"])
    assert reread <= second, "a finished sentence was read again outside the second reader: %s" % (reread - second)
    if stop_after == 3:
        # Batch 1 was finished on day one; day two's first reads are exactly batch 2.
        assert finished >= {"u%d" % i for i in range(3, 21)}
        assert sorted(_first_reads(run_dir)) == sorted(u["id"] for u in us)    # each read once
        assert {i for i in day2.reads[0]} == {"u%d" % i for i in range(21, 31)}
    else:
        # u1 was ruled (its new wording is queued for round 2); u2's read was
        # logged but not ruled, so u2 and the rest of batch 1 are read again.
        assert "u1" not in day2.reads[0] and "u2" in day2.reads[0]
    # Same end state as a run that was never stopped.
    assert m2["state"] == whole["state"]
    assert m2["progress"]["second"]["sampled"] == whole["progress"]["second"]["sampled"]
    assert len(m2["resumed"]) == 1 and m2["started"] == m1["started"]
    assert m2["calls"][:len(m1["calls"])] == m1["calls"]


def test_resume_refuses_when_an_input_changed_or_the_run_is_complete(tmp_path):
    us = _many(30)
    A.run("demo", out_dir=tmp_path, ask=PerUnit(), held=HELD, unit_list=us, cap=1.0, licensed=set(),
          day_cap=_day_cap_after(1))
    edited = us[:5] + [_unit("u6", "An edited sentence.")] + us[6:]
    with pytest.raises(A.AuditFailure, match="changed since the run stopped"):
        A.run("demo", out_dir=tmp_path, ask=PerUnit(), held=HELD, unit_list=edited, cap=1.0, licensed=set(),
              resume=True)
    with pytest.raises(A.AuditFailure, match="changed since the run stopped"):
        A.run("demo", out_dir=tmp_path, ask=PerUnit(), held={"demo:S021": DOC + " More."}, unit_list=us,
              cap=1.0, licensed=set(), resume=True)
    m = A.run("demo", out_dir=tmp_path, ask=PerUnit(), held=HELD, unit_list=us, cap=1.0, licensed=set(), resume=True)
    assert m["status"] == "complete"
    with pytest.raises(A.AuditFailure, match="not a stopped run"):
        A.run("demo", out_dir=tmp_path, ask=PerUnit(), held=HELD, unit_list=us, cap=1.0, licensed=set(), resume=True)


# ------------------------------------- what the stage may apply (2026-10-20, round 4)

def _card_run(tmp_path, ruled_text):
    page = _unit("u1", "In our reading, the evidence usually offered for it is weak.")
    card = {"id": "u2", "part": "card", "sentence": "The evidence usually offered is weak.",
            "sha": A.fingerprint("The evidence usually offered is weak."), "row": None}
    seen = {"card_reads": []}

    def ask(prompt, n):
        if "SUMMARIES of that page" in prompt:
            seen["card_reads"].append(prompt)
            first = len(seen["card_reads"]) == 1
            return json.dumps({"verdicts": [{"id": "u2", "verdict": "finding" if first else "holds",
                                             "kind": A.SUMMARY_KIND if first else None,
                                             "evidence": [{"source": "PAGE", "quote": "the evidence usually offered for it is weak"}],
                                             "proposed_text": ruled_text if first else None, "reason": "drops the hedge"}]}), {"usd": 0.0}
        if "THE SENTENCES TO READ" in prompt:
            return FakeModel(always_finding=False)(prompt, n)
        return json.dumps({"ruling": "amend", "text": ruled_text, "reason": "the page says in our reading"}), {"usd": 0.0}
    m = A.run("demo", out_dir=tmp_path, ask=ask, held=HELD, unit_list=[card, page], cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    return m, card, seen


def test_a_card_wording_the_model_composed_is_left_for_a_person_and_never_applied(tmp_path):
    composed = "In our reading, the usual evidence is weak."            # true to the page, not a body sentence
    m, card, seen = _card_run(tmp_path, composed)
    cuts = [json.loads(l) for l in (tmp_path / "cuts.jsonl").read_text().splitlines()]
    assert len(cuts) == 1 and cuts[0]["left_for_person"] and cuts[0]["not_applied"] == composed
    assert m["progress"]["done"]["u2"]["status"] == "left_for_person"
    assert m["progress"]["done"]["u2"]["sentence"] == card["sentence"]    # nothing applied
    assert A.fingerprint(composed) not in m["state"]
    assert m["state"][card["sha"]] == "must_leave_page"                 # the old card still has to change
    assert len(seen["card_reads"]) == 1                                  # the composed wording was never read as applied


def test_a_card_wording_that_is_a_body_sentence_word_for_word_is_applied(tmp_path):
    body = "In our reading, the evidence usually offered for it is weak."
    m, card, seen = _card_run(tmp_path, body)
    assert (tmp_path / "cuts.jsonl").read_text() == ""
    assert m["progress"]["done"]["u2"]["sentence"] == body and m["progress"]["done"]["u2"]["status"] == "holds"
    assert m["state"][A.fingerprint(body)] == "holds"
    assert A.body_sentence("In our reading, the evidence usually offered for it is weak.", [_unit("x", body)])
    assert not A.body_sentence("in our reading, the evidence usually offered for it is weak.", [_unit("x", body)])
    assert not A.body_sentence("In our reading, the evidence usually offered for it is weak", [_unit("x", body + " More.")])


def test_a_body_wording_the_stage_applies_is_in_changechecks_changed_set(tmp_path):
    """Step 2d: what the stage applies to the body is exactly what changecheck
    then reads, so the next preflight's 'changed sentences reviewed' row covers it."""
    spec = importlib.util.spec_from_file_location("changecheck", WHU / "changecheck.py")
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
    before = ("<html><body><main><p>The study proves that AI deskills doctors. "
              "Of 795 colonoscopies before AI was introduced, 226 detected an adenoma.</p></main>"
              "<footer id=\"updates\"><p>Updated 12 September 2026. We withdrew a promise.</p></footer></body></html>")
    sents = C.sentences_of(before)
    us = [_unit("u%d" % (i + 1), s) for i, s in enumerate(sents)]
    m = A.run("demo", out_dir=tmp_path, ask=PerUnit(flag={"u1"}), held=HELD, unit_list=us, cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    applied = m["progress"]["done"]["u1"]["sentence"]
    assert applied != us[0]["sentence"] and m["state"][A.fingerprint(applied)] == "holds"
    after = before.replace(us[0]["sentence"], applied)
    send, withheld = C.changed(before, after)
    assert send == [applied] and withheld == []
