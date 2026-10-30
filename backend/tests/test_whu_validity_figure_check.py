"""Check 5b's mechanical figure check (study/whu-reliability/next_phase/figure_check.py, validity plan §5b). Offline,
constructed text only; written before any judge label was read for this check."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location("figure_check_t", ROOT / "study" / "whu-reliability" / "next_phase" / "figure_check.py")
F = importlib.util.module_from_spec(_s)
_s.loader.exec_module(F)


def vals(s):
    return [f["value"] for f in F.figures(s)]


@pytest.mark.parametrize("s,want", [
    ("Adherence rose by 12% in three trials [4].", [12.0]),
    ("Adherence rose by 12 % [4][5].", [12.0]),
    ("Rates fell from 1,234 to 987 cases.", [1234.0, 987.0]),
    ("The risk ratio was 0,85 in Europe.", [0.85]),
    ("Warming of 1.5–2.0 °C by 2050 [2, 3].", [1.5, 2.0]),
    ("Costs were US$5 to US$53 per tonne.", [5.0, 53.0]),
    ("A review published in 2023 [12] covered 18 studies.", [18.0]),
    ("Temperatures fell by −0.3 degrees.", [-0.3]),
    ("Only 12 per cent of 1 200 000 people.", [12.0, 1200000.0]),
    ("Between 2015 and 2020 nothing changed [7].", []),
    ("See [^1_3] for the 40 trials.", [40.0]),
])
def test_figures_years_and_citations(s, want):
    assert vals(s) == want


SRC = ("Results. Digital tracking improved adherence to guidelines by 12% across 18 studies (low-certainty evidence). "
       + "filler text. " * 60 + "Elsewhere, 987 unrelated items were counted. " + "filler text. " * 60 +
       "Annual costs: 1,234 dollars.")


def test_near_absent_ambiguous():
    assert F.classify("Digital tracking improved guideline adherence by 12% [1].", SRC)["class"] == "FIGURE_NEAR"
    assert F.classify("Digital tracking improved guideline adherence by 31% [1].", SRC)["class"] == "FIGURE_ABSENT"
    # found, but not within 300 characters of two content words
    assert F.classify("Digital tracking improved guideline adherence for 987 workers [1].", SRC)["class"] == "AMBIGUOUS"
    # one figure found, one not
    assert F.classify("Tracking improved adherence by 12% and by 44% in two settings.", SRC)["class"] == "AMBIGUOUS"
    # rounding: 12.4 in the source, 12 claimed -> not absent, ambiguous
    assert F.classify("Tracking improved adherence by 12%.", "Tracking improved adherence by 12.4% overall.")["class"] == "AMBIGUOUS"
    # a %-conversion: 0.12 in the source, 12% claimed
    assert F.classify("Tracking improved adherence by 12%.", "Tracking improved adherence: proportion 0.12.")["class"] == "AMBIGUOUS"


def test_number_words_in_the_source_count():
    assert F.classify("Tracking improved guideline adherence in 3 trials [2].",
                      "Three trials found that tracking improved guideline adherence.")["class"] == "FIGURE_NEAR"


def test_thousands_and_decimal_comma_match_across_formats():
    assert F.classify("Annual costs reached 1234 dollars.", SRC)["class"] == "FIGURE_NEAR"
    assert F.classify("The adherence ratio was 0.85 overall.", "adherence ratio 0,85 overall")["class"] == "FIGURE_NEAR"


def test_no_figure_is_not_classified():
    assert F.classify("Tracking may help health workers [3].", SRC)["class"] is None


def test_stopwords_are_not_content_words():
    assert F.content_words("The study found that the evidence was weak [3].") == {"weak"}
