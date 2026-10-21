"""Blinding fixes before the freeze (protocol rev 33, "Pre-freeze rulings").

Conversion defects are fixed, writing style is not, for every system alike:
leftover markup removed (Wikipedia tags, "site +2" chips, "[cite: n]",
numerals glued to "et al."), the approximation-sign rules made correct,
"on this page" deleted, and British spellings mapped by a fixed word list
identified by its sha256. Free: no model calls.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BL = ROOT / "study" / "whu-reliability" / "blinding"
_spec = importlib.util.spec_from_file_location("blind_t", BL / "blind.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def md(raw):
    body, refs = B.from_markdown(raw)
    return " ".join(body.split()), refs


def rules(text):
    return B.apply_rules(text)[0]


# --- leftover markup ------------------------------------------------------

def test_a_wikipedia_tag_after_a_sentence_becomes_a_marker_inside_the_full_stop():
    t, refs = md("NOVA was first presented in 2009. [preventncd](https://www.preventncd.eu/x)"
                 "[Wikipedia](https://en.wikipedia.org/wiki/Carlos_Augusto_Monteiro) It sorts foods.")
    assert t == "NOVA was first presented in 2009 [1][2]. It sorts foods."
    assert "Wikipedia" not in t and refs == ["https://www.preventncd.eu/x", "https://en.wikipedia.org/wiki/Carlos_Augusto_Monteiro"]


def test_a_site_chip_with_a_count_after_a_closing_quote_leaves_no_fragment():
    t, _ = md("They do not use the term “ultra-processed.” [cacfp +2](https://www.cacfp.org/2026/01/08/x/)\n\nNext.")
    assert "cacfp" not in t and "+2" not in t
    assert t.startswith("They do not use the term “ultra-processed [1].”")


def test_a_chip_mid_sentence_and_a_prose_link_are_told_apart_by_the_host():
    t, _ = md("Series [sciencedaily +2](https://www.sciencedaily.com/r.htm) reported it, as did "
              "[the Lancet series](https://www.thelancet.com/series).")
    assert t == "Series [1] reported it, as did the Lancet series [2]."


def test_a_link_whose_text_is_its_url_becomes_a_marker():
    t, _ = md("See [https\\://pubmed.ncbi.nlm.nih.gov/38418082/](https://pubmed.ncbi.nlm.nih.gov/38418082/) for it.")
    assert t == "See [1] for it."


def test_an_escaped_cite_marker_becomes_numbered_markers():
    t, _ = md("Two-Week Body Weight Shift \\[cite: 5\\] and intake \\[cite: 5, 26\\].")
    assert "cite" not in t and "[5]" in t and "[26]" in t


def test_a_numeral_glued_to_et_al_becomes_a_marker_for_every_answer():
    t, _ = md("| Cardiovascular mortality | RR: 1.50 | Lane et al.3 |\n| Diabetes | OR 1.40 | Lane et al.1,4 |")
    assert "et al.3" not in t and "Lane et al. [3]" in t and "Lane et al. [1][4]" in t
    t, _ = md("Smith et al. 2019 found it; Jones et al.2019 too.")   # a year is not a marker
    assert "Smith et al. 2019" in t and "et al.2019" in t


# --- approximation signs --------------------------------------------------

@pytest.mark.parametrize("before, after", [
    ("was associated with a ~15% higher risk", "was associated with a roughly 15% higher risk"),
    ("an ≈8% rise", "a roughly 8% rise"),
    ("mortality (HR≈1.62, Q4 vs Q1)", "mortality (HR about 1.62, Q4 vs Q1)"),
    ("French adults (N≈44,000)", "French adults (N about 44,000)"),
    ("about (~5%) of calories", "about (about 5%) of calories"),
    ("cut intake by ~500 kcal", "cut intake by about 500 kcal"),
])
def test_approximation_signs(before, after):
    out = rules(before)
    assert out == after and "a about" not in out


# --- "on this page" --------------------------------------------------------

@pytest.mark.parametrize("before, after", [
    ("The two randomized trials on this page test the effect.", "The two randomized trials test the effect."),
    ("On this page, the cohorts disagree.", "The cohorts disagree."),
    ("Everything on this page was read in full.", "Everything was read in full."),
    ("This page reads the cohorts.", "This report reads the cohorts."),         # W15 unchanged
])
def test_on_this_page_is_deleted_not_rewritten(before, after):
    out = rules(before)
    assert out == after and "on this report" not in out


# --- spelling ---------------------------------------------------------------

def test_british_spellings_map_by_the_fixed_list_and_names_are_left():
    out = rules("yoghurt and savoury snacks; a glycaemic load; the Science Media Centre's centre; flavour")
    assert out == "yogurt and savory snacks; a glycemic load; the Science Media Centre's center; flavor"


def test_the_spelling_list_is_identified_by_its_sha256():
    raw = (BL / "spelling_us.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == B.SPELLING_SHA256
    words = json.loads(raw)["words"]
    assert words["yoghurt"] == "yogurt" and words["savoury"] == "savory"
    assert all(k != v and k.isalpha() and v.isalpha() for k, v in words.items())
    assert "spelling" not in B.PHRASES                                   # one list, not two


def test_a_changed_spelling_list_is_refused(tmp_path, monkeypatch):
    f = tmp_path / "spelling_us.json"
    f.write_text(json.dumps({"words": {"colour": "color"}}))
    monkeypatch.setattr(B, "SPELLING_FILE", f)
    with pytest.raises(SystemExit) as e:
        B.load_spelling()
    assert "not the pinned" in str(e.value)


def test_no_other_wording_changes():
    s = ("On its own criteria the review rated four associations as convincing, and the cohorts here "
         "read the other way; we cannot reconcile them.")
    assert rules(s) == s


# --- found by the re-run check (same round) --------------------------------

def test_a_url_with_parentheses_leaves_no_fragment():
    t, refs = md("They ate more. [cell](https://www.cell.com/fulltext/S1550-4131(19)30248-7) Results.")
    assert t == "They ate more [1]. Results." and refs == ["https://www.cell.com/fulltext/S1550-4131(19)30248-7"]


def test_a_less_than_sign_is_text_and_a_code_block_is_dropped():
    t, _ = md("odds than those consuming <20%. Inflammation is a risk factor.\n\n```mermaid\ngraph LR\n"
              "    A[\"x (↑ sugar)\"] --> B\n```\n\nNext paragraph.")
    assert "<20%. Inflammation is a risk factor." in t and "Next paragraph." in t
    assert "mermaid" not in t and "graph LR" not in t and "sugar" not in t


def test_html_tags_still_go():
    t, _ = md("<table><tr><td>a</td><td>b</td></tr></table> <span class=\"x\">kept</span>")
    assert "<" not in t and "a ; b" in t and "kept" in t


def test_a_numeral_glued_after_a_closing_quote_becomes_a_marker():
    t, _ = md('The evidence is "limited"47. Next methods46.\n\n## Works cited\n1. a')   # a Gemini export
    assert t.startswith('The evidence is "limited" [47]. Next methods [46].')


def test_runs_of_empty_cells_collapse():
    assert B.empty_cells("Eating Speed ; ; ; ; [5] Next ; ;  ; x") == "Eating Speed ; [5] Next ; x"
