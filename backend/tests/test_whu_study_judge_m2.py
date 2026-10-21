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
