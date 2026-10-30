"""The 2026-10-30 price rows (advisor's ruling: platform.claude.com pricing page, read that day) and
lean WHU's tiers. No model is called."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
_s = importlib.util.spec_from_file_location("spend_ledger_prices", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_s)
_s.loader.exec_module(S)
import lean  # noqa: E402

PAGE = {   # USD per million tokens: input, output, cache write 5m, cache write 1h, cache read
    "claude-sonnet-5-5": (2.00, 10.00, 2.50, 4.00, 0.10),
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.20, 0.01),
}
HAIKU_ABOVE = (0.50, 2.50, 0.625, 1.00, 0.05)


@pytest.mark.parametrize("model", sorted(PAGE))
def test_the_new_rows_are_the_pages_figures(model):
    p = S.PRICES[model]
    assert (p["input"], p["output"], p["cache_write"], p["cache_write_1h"], p["cache_read"]) == PAGE[model]


def test_the_existing_rows_match_the_page_at_the_5_minute_rate():
    assert S.PRICES["claude-opus-5-5"] == {"input": 4.0, "output": 20.0, "cache_write": 5.0, "cache_read": 0.2}
    assert S.PRICES["claude-sonnet-4-6"] == {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.3}


def test_haiku_steps_up_over_100000_prompt_tokens_counting_cache_reads_and_writes():
    a = S.PRICES["claude-haiku-5-5"]["above"]
    assert (a["input"], a["output"], a["cache_write"], a["cache_write_1h"], a["cache_read"]) == HAIKU_ABOVE
    assert S.rates("claude-haiku-5-5", 100_000)["input"] == 0.10
    assert S.rates("claude-haiku-5-5", 100_001)["input"] == 0.50
    U = type("U", (), {})
    u = U(); u.input_tokens, u.output_tokens, u.cache_creation_input_tokens, u.cache_read_input_tokens = 60_000, 1_000, 0, 50_000
    usd, _ = S.price("claude-haiku-5-5", u)              # 110,000 prompt tokens: the higher tier throughout
    assert usd == round((60_000 * 0.50 + 1_000 * 2.50 + 50_000 * 0.05) / 1e6, 6)
    u.cache_read_input_tokens = 0                         # 60,000: the lower tier
    assert S.price("claude-haiku-5-5", u)[0] == round((60_000 * 0.10 + 1_000 * 0.50) / 1e6, 6)
    assert S.rates("claude-sonnet-5-5", 900_000)["input"] == 2.00     # no step


def test_lean_prices_with_the_step_too():
    assert lean.usd("claude-haiku-5-5", 200_000, 0) == pytest.approx(200_000 * 0.50 / 1e6)
    assert lean.usd("claude-haiku-5-5", 50_000, 0) == pytest.approx(50_000 * 0.10 / 1e6)


def test_the_lean_default_is_sonnet_5_5_and_haiku_is_a_variant():
    assert lean.SMALL == "claude-sonnet-5-5"
    for k in lean.SMALL_STAGES:
        assert lean.STAGE_MODELS[k] == "claude-sonnet-5-5"
    assert lean.STAGE_MODELS["audit_escalate"] == lean.STAGE_MODELS["judgements_escalate"] == "claude-opus-5-5"
    h = lean.variant_models("haiku-5-5")
    assert {h[k] for k in lean.SMALL_STAGES} == {"claude-haiku-5-5"} and h["audit_escalate"] == "claude-opus-5-5"
    lean.check_models(h)
    lean.check_models(lean.variant_models("sonnet-4-6"))


def test_the_gate_sends_no_temperature_to_a_model_that_refuses_one():
    src = (ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py").read_text(encoding="utf-8")
    assert 'FIXED_SAMPLING = ("claude-sonnet-5-5", "claude-haiku-5-5")' in src
    assert 'if SIGNAL_MODEL in FIXED_SAMPLING:\n                    params.pop("temperature")' in src
