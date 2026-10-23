"""M2 v2 is frozen by sha256 (advisor ruling 2026-10-21); judge_m2's reply checks. Offline."""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "study" / "whu-reliability"
_spec = importlib.util.spec_from_file_location("judge_m2_t", STUDY / "scripts" / "judge_m2.py")
J2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J2)


def test_the_m2_prompt_is_the_frozen_v2():
    assert hashlib.sha256(J2.PROMPT.read_bytes()).hexdigest() == J2.PROMPT_SHA256
    text = J2.PROMPT.read_text(encoding="utf-8")
    assert "Judge certainty, not vocabulary." in text and "landmark trial" in text
    v1 = (STUDY / "prompts" / "m2_conclusion_calibration_v1.md").read_bytes()
    assert hashlib.sha256(v1).hexdigest().startswith("aebfffc1")      # v1 kept


def test_build_puts_the_answer_first_and_fills_every_field():
    c = {k: "x-%s" % k for k in J2.FIELDS}
    prefix, rest = J2.build("THE ANSWER", c)
    assert prefix.endswith("THE ANSWER") and "{" not in rest.replace("{\"label\"", "")
    assert all("x-%s" % k in rest for k in J2.FIELDS)


def test_reply_form_checks():
    ok, p = J2.parse('{"label": "Matches", "span": "a b", "reason": "r"}')
    assert p == []
    _o, p = J2.parse('{"label": "Omits", "span": "a", "reason": "r"}')
    assert "a span with Omits" in p
    _o, p = J2.parse('{"label": "Matches", "span": "", "reason": "r"}')
    assert "no span" in p
    _o, p = J2.parse('{"label": "Maybe", "span": "a", "reason": "r"}')
    assert any(x.startswith("label") for x in p)
    o, p = J2.parse('{"label": "Matches", "span": "a", "reason": "cut off')
    assert o is None and "not JSON" in p


def test_span_verbatim_after_normalisation():
    ans = "The trial found “508 kcal” more — a lot."
    assert J2.span_verbatim('the trial found "508 kcal" more - a lot', ans)
    assert J2.span_verbatim("The trial found … a lot.", ans)
    assert not J2.span_verbatim("The trial found 600 kcal", ans)


class _Stub:
    """A Claude client that records max_tokens and answers with valid JSON."""

    def __init__(self):
        self.seen = []
        self.messages = self

    def create(self, **kw):
        self.seen.append(kw["max_tokens"])
        import types
        return types.SimpleNamespace(content=[types.SimpleNamespace(text='{"label":"Matches","span":"a","reason":"r"}')],
                                     model="claude-opus-5-5", stop_reason="end_turn",
                                     usage=types.SimpleNamespace(input_tokens=1, output_tokens=1,
                                                                 cache_read_input_tokens=0, cache_creation_input_tokens=0))


def test_the_output_limit_is_2048_for_the_claude_judge_on_both_prompts():
    """Raised from 1,024 on 2026-10-21 (a runner setting). The ChatGPT judge
    stays at 6,000, since its reasoning tokens count as output."""
    J1 = J2.J1
    assert J1.CLAUDE_MAX_OUT == 2048 and J2.CLAUDE_MAX_OUT == 2048
    assert J1.OPENAI_MAX_OUT == J2.OPENAI_MAX_OUT == 6000
    s = _Stub()
    J1.call_claude(s, "p", "r", J1.CLAUDE_MODEL)
    J2.call_claude(s, "p", "r")
    assert s.seen == [2048, 2048]


def test_the_prompts_are_unchanged_by_the_limit():
    assert hashlib.sha256(J2.PROMPT.read_bytes()).hexdigest() == J2.PROMPT_SHA256
    m1 = (STUDY / "prompts" / "m1_citation_support.md").read_bytes()
    import subprocess
    head = subprocess.run(["git", "show", "HEAD:study/whu-reliability/prompts/m1_citation_support.md"],
                          cwd=ROOT, capture_output=True).stdout
    assert head == m1


# --- the seeded 20% second read (2026-10-23, as judge_m1.py) ------------------

import json  # noqa: E402
import sys  # noqa: E402


class _FakeAnthropic:
    def __init__(self, api_key=None):
        self.messages = self

    def count_tokens(self, **kw):
        return type("C", (), {"input_tokens": 500})()


def _m2_run(tmp_path, n_answers=3, n_concl=5):
    run = tmp_path / "run"; (run / "answers").mkdir(parents=True)
    answers, items = {}, []
    concl = [{"id": "C%d" % k, "statement": "statement %d" % k, "direction": "helps", "size": "", "certainty": "low",
              "scope": "", "quote": "q"} for k in range(n_concl)]
    for a in range(n_answers):
        (run / "answers" / ("A%d.txt" % a)).write_text("An answer %d." % a)
        answers["A%d" % a] = {"file": "answers/A%d.txt" % a}
        items += [{"item": "M2-%d-%d" % (a, k), "answer": "A%d" % a, "conclusion": "C%d" % k} for k in range(n_concl)]
    (run / "items.json").write_text(json.dumps({"answers": answers, "conclusions": concl, "items": items}))
    return run, sorted(i["item"] for i in items)


def _wire(monkeypatch, calls):
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    monkeypatch.setattr(J2.J1, "env_keys", lambda: {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "y"})
    monkeypatch.setattr(J2.S, "metered", lambda raw, **kw: raw)
    monkeypatch.setattr(J2.J1, "spent", lambda issue: 0.0)
    reply = json.dumps({"label": "Matches", "span": "An answer", "reason": "r"})

    def fake(judge):
        def f(*args):
            calls.append((judge, args[1] + args[2]))       # the whole prompt: prefix + rest
            return reply, {"input": 10, "output": 5, "model": "m"}, 0.0, False
        return f
    monkeypatch.setattr(J2, "call_claude", fake("claude"))
    monkeypatch.setattr(J2, "call_openai", fake("openai"))


def test_each_judge_reads_each_m2_item_once_and_a_seeded_20_percent_twice(tmp_path, monkeypatch):
    run, pool = _m2_run(tmp_path)
    calls = []
    _wire(monkeypatch, calls)
    monkeypatch.setattr(sys, "argv", ["judge_m2.py", str(run), "--seed", "777"])
    assert J2.main() == 0
    expected = J2.J1.consistency_sample(pool, 0.2, 777)
    assert len(expected) == 3                                              # 20% of 15
    for jd in ("claude", "openai"):
        assert sorted(p.stem for p in (run / "replies" / jd).glob("*.json")) == pool
        assert sorted(p.stem for p in (run / "replies_repeat" / jd).glob("*.json")) == expected
    s = json.loads((run / "replies" / "consistency_sample.json").read_text())
    assert s["seed"] == 777 and s["share"] == 0.2 and s["items"] == expected and s["pool"] == pool
    # Another seed: the recorded sample stands, and nothing is read.
    n = len(calls)
    monkeypatch.setattr(sys, "argv", ["judge_m2.py", str(run), "--seed", "778"])
    assert J2.main() == 4 and len(calls) == n


def test_a_sampled_items_second_read_follows_its_first_with_the_identical_prompt(tmp_path, monkeypatch):
    run, pool = _m2_run(tmp_path, n_answers=2, n_concl=5)
    calls = []
    _wire(monkeypatch, calls)
    monkeypatch.setattr(sys, "argv", ["judge_m2.py", str(run), "--judges", "claude", "--seed", "3"])
    assert J2.main() == 0
    sample = J2.J1.consistency_sample(pool, 0.2, 3)
    rests = [r for _j, r in calls]
    assert len(rests) == len(pool) + len(sample)
    # Each repeat is the call straight after its first read, with the same prompt.
    repeats = [i for i in range(1, len(rests)) if rests[i] == rests[i - 1]]
    assert len(repeats) == len(sample)


def test_share_zero_reads_once(tmp_path, monkeypatch):
    run, pool = _m2_run(tmp_path)
    calls = []
    _wire(monkeypatch, calls)
    monkeypatch.setattr(sys, "argv", ["judge_m2.py", str(run), "--consistency-share", "0"])
    assert J2.main() == 0
    assert not (run / "replies_repeat").exists() and len(calls) == 2 * len(pool)


def test_both_runners_seed_the_repeat_from_the_freeze_commit():
    J1 = J2.J1
    assert J1.FREEZE_COMMIT == "5d83e9b8025312923f3fb8ea2d5de3b47c212362"
    assert J1.CONSISTENCY_SEED == int(J1.FREEZE_COMMIT, 16)
    src2 = (STUDY / "scripts" / "judge_m2.py").read_text()
    assert "default=J1.CONSISTENCY_SEED" in src2 and "default=J1.CONSISTENCY_SHARE" in src2
    src1 = (STUDY / "scripts" / "judge_m1.py").read_text()
    assert "default=CONSISTENCY_SEED" in src1
    ps = (STUDY / "scripts" / "prepare_scoring.py").read_text()
    assert 'FREEZE = "%s"' % J1.FREEZE_COMMIT in ps                       # the sampler's seed is the same hash
