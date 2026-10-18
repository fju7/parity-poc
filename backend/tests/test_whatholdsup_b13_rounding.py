"""B13 reads a correctly rounded figure as found, as rule 1 already does.

Adopted 2026-10-18. Deskilling prints 43.8% for S031's Table 2 "43.79 (40.71-54.89)".
Rule 1 passed it as "43.8 is 43.79 rounded"; B13 reported it as in no document we
hold. The allowance is rule 1's (figure_text.rounds_to): at most one decimal place
dropped, correctly rounded, same sign; asked only after the exact search, the
comma-and-space reading and the declared exclusions.

Fixtures only. Nothing here reads an issue directory or loads publish.py.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


TABLE = ("Inspection time, % (95 %CI) ... All 42.68 (30.14-50.44) 49.50 (41.31-63.28) "
         "43.79 (40.71-54.89) and a change of -6.45 points")


@pytest.fixture
def b13(monkeypatch):
    mod = _load("b13")
    monkeypatch.setattr(mod.store, "held", lambda slug: {"S031": {}})
    monkeypatch.setattr(mod.store, "sources", lambda slug: [{"id": "S031"}])
    monkeypatch.setattr(mod.SC, "_text", lambda slug, sid: TABLE)
    monkeypatch.setattr(mod, "load_exclusions", lambda slug: [])
    return mod


def page(mod, monkeypatch, *sentences):
    monkeypatch.setattr(mod.B, "page_sentences", lambda slug: list(sentences))
    monkeypatch.setattr(mod.B, "_page_html", lambda slug: "<p>%s</p>" % " ".join(sentences))


def test_a_correct_rounding_is_found_with_an_info_note(b13, monkeypatch):
    page(b13, monkeypatch, "They inspected the boxes for 43.8% of the time.")
    r = b13.run("t")
    assert r["missing"] == [] and r["rounded"] == ["43.8 is 43.79 rounded, in S031"]
    rows = {n: (s, d) for n, s, d in b13.preflight_rows("t")}
    st, d = rows["figures found as a held figure correctly rounded"]
    assert st == b13.OK and d.startswith("INFO") and "43.79" in d


@pytest.mark.parametrize("shown", ["43.7", "43.9", "42.6"])
def test_an_incorrect_rounding_still_misses(b13, monkeypatch, shown):
    page(b13, monkeypatch, "They inspected the boxes for %s%% of the time." % shown)
    assert [f for f, _ in b13.run("t")["missing"]] == [shown]


def test_two_places_dropped_still_misses(b13, monkeypatch):
    monkeypatch.setattr(b13.SC, "_text", lambda slug, sid: "SMD -0.946 for walking and 0.946 overall")
    page(b13, monkeypatch, "Walking came to 0.9 overall, or 0.95 on the review's own figure.")
    missing = [f for f, _ in b13.run("t")["missing"]]
    assert missing == ["0.9"]                 # 0.95 is one place, correctly rounded


def test_the_sign_must_match(b13, monkeypatch):
    page(b13, monkeypatch, "That is a reduction of about 6.5% across all participants.")
    assert [f for f, _ in b13.run("t")["missing"]] == ["6.5"]


def test_a_declared_exclusion_is_not_found_as_a_coincidental_rounding(b13, monkeypatch):
    rule = {"figure": "43.8", "in_sentence": "our own sum of 43.8", "why": "ours", "by": "x"}
    monkeypatch.setattr(b13, "load_exclusions", lambda slug: [rule])
    page(b13, monkeypatch, "This is our own sum of 43.8 and nothing else.")
    r = b13.run("t")
    assert r["missing"] == [] and r["rounded"] == [] and [f for f, _ in r["excluded"]] == ["43.8"]


def test_where_is_unchanged_and_does_not_round(b13):
    assert b13.where("43.8", "t") == [] and b13.where("43.79", "t") == ["S031"]
