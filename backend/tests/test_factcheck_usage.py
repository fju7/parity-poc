"""What a gate run costs, priced from recorded token usage.

Run:  python3 backend/tests/test_factcheck_usage.py   (or under pytest)

No API calls: every case feeds fabricated usage entries through the same
summariser the gate uses, so the arithmetic can be checked for free.

WHY THIS EXISTS
A gate report recorded the model and no tokens, so the cost of publishing an
issue was a feeling. It could not be priced against and it could not be
optimised — nobody could say which of the six roles was expensive. The prices
here are a copy of a published page and will go stale; the test that matters
most is the one asserting an unknown model reports null rather than a guess.
"""
import importlib.util, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "fc", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

M = "claude-sonnet-4-6"
def e(label, model=M, i=0, o=0, cw=0, cr=0, ws=0):
    return {"label": label, "model": model, "input": i, "output": o,
            "cache_write": cw, "cache_read": cr, "web_searches": ws}


def test_a_million_tokens_costs_the_list_price():
    s = fc.usage_summary([e("SOURCE", i=1_000_000)])
    assert s["total"]["usd"] == 3.0, s["total"]
    s = fc.usage_summary([e("SOURCE", o=1_000_000)])
    assert s["total"]["usd"] == 15.0, s["total"]


def test_cache_reads_are_cheaper_than_input():
    read = fc.usage_summary([e("X", cr=1_000_000)])["total"]["usd"]
    inp = fc.usage_summary([e("X", i=1_000_000)])["total"]["usd"]
    assert read == 0.3 and read < inp


def test_web_searches_are_charged_on_top_of_tokens():
    s = fc.usage_summary([e("COVERAGE", i=1_000_000, ws=100)])
    assert s["total"]["usd"] == 3.0 + 1.0, s["total"]      # 100 searches = $1


def test_roles_are_split_out_so_an_expensive_one_is_visible():
    s = fc.usage_summary([e("SOURCE", i=1_000_000), e("ADVOCATE", i=100_000),
                          e("SOURCE", o=200_000)])
    assert s["by_role"]["SOURCE"]["calls"] == 2
    assert s["by_role"]["ADVOCATE"]["calls"] == 1
    assert s["by_role"]["SOURCE"]["usd"] > s["by_role"]["ADVOCATE"]["usd"]
    assert round(sum(r["usd"] for r in s["by_role"].values()), 4) == s["total"]["usd"]


def test_an_unknown_model_reports_null_rather_than_a_guess():
    s = fc.usage_summary([e("SOURCE", model="some-future-model", i=1_000_000)])
    assert s["total"]["usd"] is None
    assert s["total"]["input"] == 1_000_000          # tokens are still counted


def test_one_unknown_model_poisons_only_the_total_it_belongs_to():
    s = fc.usage_summary([e("A", i=1_000_000),
                          e("B", model="unknown-model", i=1_000_000)])
    assert s["by_role"]["A"]["usd"] == 3.0
    assert s["by_role"]["B"]["usd"] is None
    assert s["total"]["usd"] is None                 # a total with a hole is not a total


def test_the_prices_say_where_and_when_they_came_from():
    s = fc.usage_summary([])
    assert s["prices_checked"] and "pricing" in s["prices_source"]


def test_nothing_recorded_is_zero_not_an_error():
    s = fc.usage_summary([])
    assert s["total"]["calls"] == 0 and s["total"]["usd"] == 0.0


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("  ok   " + name[5:].replace("_", " ")); passed += 1
            except AssertionError as exc:
                print("  FAIL " + name[5:].replace("_", " ") + "  " + str(exc)); failed += 1
    print("\n  %d passed, %d failed\n" % (passed, failed))
    sys.exit(1 if failed else 0)
