"""Advisor's rulings after orchestrator trial 1 attempt 17 (2026-11-23).

(1) every audit reply that cannot be parsed is saved in the audit run folder;
(2) in lean / orchestrated mode an audit reply (verdict batch, re-quote, ruling) must be exactly one JSON object:
    no brace-matching fallback, one re-ask, then the audit fails as before; counted for the run record;
    non-lean unchanged;
(3) the shared sentence splitter does not break at common abbreviations (lean / orchestrated mode).

No model is called: every run uses a fake `ask`."""
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
import one_sentence  # noqa: E402
import source_ledger as L  # noqa: E402
from orch import page as PG  # noqa: E402


@pytest.fixture
def lean_on(monkeypatch):
    monkeypatch.delenv(lean.ENV_MODELS, raising=False)
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


DOC = "Of 795 colonoscopies before AI was introduced, 226 detected an adenoma (28.4%)."
HELD = {"demo:S021": DOC}
SENT = "Of 795 colonoscopies, 226 detected an adenoma (28.4%)."


def _units():
    return [{"id": "u1", "part": "page", "sentence": SENT, "sha": A.fingerprint(SENT),
             "row": {"source_id": "S021", "span": DOC}}]


def _verdicts(prompt, verdict="holds"):
    ids = re.findall(r"^\[(u\d+)\]", prompt, re.M)
    return {"verdicts": [{"id": i, "verdict": verdict,
                          "kind": "Overstated a finding or a source's claim" if verdict == "finding" else None,
                          "evidence": [{"source": "S021", "quote": "226 detected an adenoma (28.4%)"}],
                          "proposed_text": "A narrower sentence." if verdict == "finding" else None,
                          "reason": "test"} for i in ids]}


# Attempt 17's shape: one JSON value, then more text on line 3 (json: "Extra data: line 3 column 1").
def one_then_extra(value: dict) -> str:
    return json.dumps(value) + "\n\n" + json.dumps({"note": "and a second value"})


class Fake:
    """READS: the replies to give read prompts, in order (a callable of the prompt); the last repeats.
    RULES likewise for ruling prompts."""

    def __init__(self, reads, rules=None):
        self.reads, self.rules = list(reads), list(rules or [])
        self.prompts = []

    def __call__(self, prompt, max_tokens, model=None):
        self.prompts.append(prompt)
        if "THE SENTENCES TO READ" in prompt:
            f = self.reads.pop(0) if len(self.reads) > 1 else self.reads[0]
        else:
            f = self.rules.pop(0) if len(self.rules) > 1 else self.rules[0]
        return f(prompt), {"input": len(prompt) // 4, "output": 50, "usd": 0.0}


def _malformed(tmp_path, monkeypatch):
    log = tmp_path / "malformed.jsonl"
    monkeypatch.setenv("WHU_ORCH_MALFORMED_LOG", str(log))
    return log


def _events(log):
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def _unparsed(out):
    p = out / A.UNPARSED_FILE
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


# ----------------------------------------------------------------- (2) strict, with (1)

def test_lean_a_value_then_extra_text_is_reasked_once_and_the_second_reply_is_used(tmp_path, lean_on, monkeypatch):
    log = _malformed(tmp_path, monkeypatch)
    out = tmp_path / "run"
    fake = Fake([lambda p: one_then_extra(_verdicts(p)), lambda p: json.dumps(_verdicts(p))])
    m = A.run("demo", out_dir=out, ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    reads = [p for p in fake.prompts if "THE SENTENCES TO READ" in p]
    # the first read, its one re-ask (the same prompt plus REASK_ONE), then any later read (the second reader)
    assert [p.endswith(A.REASK_ONE) for p in reads[:2]] == [False, True] and reads[1][:-len(A.REASK_ONE)] == reads[0]
    assert sum(p.endswith(A.REASK_ONE) for p in reads) == 1
    ev = _events(log)
    assert [e["event"] for e in ev] == ["malformed", "reask"] and ev[0]["role"] == "audit:read"
    saved = _unparsed(out)
    assert len(saved) == 1 and saved[0]["text"] == one_then_extra(_verdicts(reads[0]))


def test_lean_a_second_malformed_reply_fails_the_audit_as_before(tmp_path, lean_on, monkeypatch):
    log = _malformed(tmp_path, monkeypatch)
    out = tmp_path / "run"
    fake = Fake([lambda p: one_then_extra(_verdicts(p))])
    m = A.run("demo", out_dir=out, ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "failed" and "after a re-ask" in m["failure"]
    assert len([p for p in fake.prompts if "THE SENTENCES TO READ" in p]) == 2
    assert [e["event"] for e in _events(log)] == ["malformed", "reask", "malformed"]
    assert [s["role"] for s in _unparsed(out)] == ["read", "read-reask"]


def test_lean_there_is_no_brace_matching_fallback(tmp_path, lean_on, monkeypatch):
    _malformed(tmp_path, monkeypatch)
    out = tmp_path / "run"
    fake = Fake([lambda p: "Here are the verdicts:\n" + json.dumps(_verdicts(p)) + "\nDone."])
    m = A.run("demo", out_dir=out, ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "failed"


def test_lean_a_fenced_single_object_is_one_value(tmp_path, lean_on, monkeypatch):
    log = _malformed(tmp_path, monkeypatch)
    fake = Fake([lambda p: "```json\n" + json.dumps(_verdicts(p)) + "\n```"])
    m = A.run("demo", out_dir=tmp_path / "run", ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    assert _events(log) == []


def test_lean_an_array_is_not_the_expected_object():
    assert A.one_object(json.dumps([{"verdicts": []}])) is None
    assert A.one_object(json.dumps({"verdicts": []})) == {"verdicts": []}


def test_lean_a_ruling_reply_is_reasked_too(tmp_path, lean_on, monkeypatch):
    log = _malformed(tmp_path, monkeypatch)
    ruling = {"ruling": "reject", "text": None, "reason": "holds"}
    fake = Fake([lambda p: json.dumps(_verdicts(p, "finding"))],
                [lambda p: one_then_extra(ruling), lambda p: json.dumps(ruling)])
    m = A.run("demo", out_dir=tmp_path / "run", ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    rules = [p for p in fake.prompts if "THE SENTENCES TO READ" not in p]
    assert [p.endswith(A.REASK_ONE) for p in rules[:2]] == [False, True] and rules[1][:-len(A.REASK_ONE)] == rules[0]
    assert sum(p.endswith(A.REASK_ONE) for p in rules) == 1
    assert [(e["role"], e["event"]) for e in _events(log)] == [("audit:rule", "malformed"), ("audit:rule", "reask")]


def test_the_orchestrator_counts_the_audits_events():
    import orchestrator as O
    s = O.malformed_summary([{"role": "audit:read", "event": "malformed"}, {"role": "audit:read", "event": "reask"}])
    assert s["malformed"] == 1 and s["reasks"] == 1


# ----------------------------------------------------------------- non-lean unchanged, with (1)

def test_off_a_value_then_extra_text_fails_as_before_and_is_saved(tmp_path, lean_off, monkeypatch):
    log = _malformed(tmp_path, monkeypatch)
    out = tmp_path / "run"
    fake = Fake([lambda p: one_then_extra(_verdicts(p))])
    m = A.run("demo", out_dir=out, ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "failed" and "Extra data" in m["failure"]
    assert len([p for p in fake.prompts if "THE SENTENCES TO READ" in p]) == 1      # no re-ask
    assert _events(log) == []
    saved = _unparsed(out)
    assert len(saved) == 1 and "Extra data" in saved[0]["why"]


def test_off_the_prose_wrapped_object_is_still_accepted(tmp_path, lean_off):
    fake = Fake([lambda p: "Here are the verdicts:\n" + json.dumps(_verdicts(p)) + "\nDone."])
    m = A.run("demo", out_dir=tmp_path / "run", ask=fake, held=HELD, unit_list=_units(), cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    assert not (tmp_path / "run" / A.UNPARSED_FILE).exists()


# ----------------------------------------------------------------- (3) the splitter

ABBREVIATED = [
    "Smith et al. (2020) found a smaller effect in rural schools.",
    "Some supports, e.g. classroom assistants, were studied.",
    "The outcome, i.e. enrolment, rose in two trials.",
    "The review differs, cf. the 2020 map.",
    "Training vs. no training was compared in one trial.",
    "The gap was approx. 12 points.",
    "Fig. 2 shows the map and Figs. 3 and 4 show the trends.",
    "Report No. 5 gives the totals.",
    "The review by J. Smith was cited.",
    "The review by J. R. Smith was cited.",
]


@pytest.mark.parametrize("s", ABBREVIATED)
def test_lean_an_abbreviation_is_not_a_sentence_end(s, lean_on):
    assert L.sentences(s + " The next sentence follows.") == [s, "The next sentence follows."]
    assert one_sentence.count(s) == 1


def test_lean_a_real_sentence_end_still_splits(lean_on):
    assert L.sentences("It ended. The next began. Was it? Yes!") == ["It ended.", "The next began.", "Was it?",
                                                                   "Yes!"]
    assert L.sentences("The U.S. The next.") == ["The U.S.", "The next."]
    assert L.sentences("See No. Then go.") == ["See No.", "Then go."]       # No. only before a number


def test_off_the_split_is_unchanged(lean_off):
    assert L.sentences("Smith et al. (2020) found it. Next.") == ["Smith et al.", "(2020) found it.", "Next."]
    assert one_sentence.count("Smith et al. (2020) found it.") == 2


def test_the_orchestrator_step_switches_it_on_too(lean_off, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "audit")
    assert L.sentences("Smith et al. (2020) found it. Next.") == ["Smith et al. (2020) found it.", "Next."]


def test_lean_the_page_writer_and_the_audits_splitter_agree(lean_on):
    """One splitter: a stored page sentence holding every abbreviation is one unit of bindings.page_sentences, so
    the standing page-sentence check finds no mismatch."""
    import orchestrator as O
    body = " ".join(ABBREVIATED)
    stored = PG.split(body)
    assert stored == ABBREVIATED
    page = PG.Page({"title": "T", "blocks": [{"tag": "p", "sentences": stored}]})
    html = "<html><body><article><p>%s</p></article></body></html>" % body
    assert O.splitter_mismatches("demo-not-an-issue", page, html) == []
