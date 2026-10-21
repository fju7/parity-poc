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
