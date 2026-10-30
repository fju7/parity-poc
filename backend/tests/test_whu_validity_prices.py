"""The 2026-10-30 Google row (advisor's ruling: ai.google.dev/gemini-api/docs/pricing, read that day), two dated
rows, for the WHU validity phase's third judge. No model is called."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location("spend_ledger_validity", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_s)
_s.loader.exec_module(S)

M = "gemini-4-argon"


def test_the_row_is_the_rulings_figures_through_november():
    p = S.PRICES[M]
    assert (p["input"], p["output"], p["cache_read"], p["until"]) == (2.00, 10.00, 0.10, "2026-11-30")
    assert (p["then"]["input"], p["then"]["output"], p["then"]["cache_read"]) == (4.00, 20.00, 0.20)


def test_a_call_after_november_30_uses_the_second_row():
    last = datetime(2026, 11, 30, 23, 59, 59, tzinfo=timezone.utc)
    first = datetime(2026, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert S.rates(M, 1000, at=last)["input"] == 2.00
    assert S.rates(M, 1000, at=first)["input"] == 4.00
    assert S.rates(M, 1000, at=first)["output"] == 20.00


def test_undated_rows_are_unchanged_by_the_date():
    late = datetime(2027, 6, 1, tzinfo=timezone.utc)
    assert S.rates("claude-opus-5-5", 1000, at=late) == S.PRICES["claude-opus-5-5"]
    assert S.rates("claude-haiku-5-5", 100_001, at=late)["input"] == 0.50
