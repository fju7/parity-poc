"""Each mark must be able to fail, or it is an exemption with a longer name.

After the two writing rules were adopted with no exemption, issue one came down
to eight items that were not sentences: an axis tick, a legend label, a
comparison table, a chart caption, and the scorecard's composite 3.4. None
rests on a source and none should.

The obvious move — an attribute that means "skip this" — is the grandfathering
argument in a different hat, and worse, because it would live in the HTML where
anyone editing the page could extend it to a sentence that was merely
inconvenient. So each mark is a CLAIM about the marked text, and the tests
below are the claims being falsified:

  restates  a table may restate what the article proved; it may never be where
            a number enters the page.
  scale     these figures are a ruler, not measurements. Put a measurement in
            an axis and the even spacing breaks.
  computed  the working must use the scores actually shown, its weights must
            sum to 1, and it must come to the number printed.
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


F = _load("furniture")
HELD = {0.51, 0.294, 0.887, 1137.0, 157.0, 107.0, 50.0}


# --- restates ---------------------------------------------------------------

def test_restates_passes_when_every_figure_is_already_bound():
    assert F.check_restates("Patients 157 (107 vs 50) 1,137", HELD, set()) is None


def test_restates_blocks_a_figure_the_article_never_proved():
    why = F.check_restates("Median follow-up 60.3 months", HELD, set())
    assert why and "60.3" in why


def test_a_table_may_not_be_where_a_number_enters_the_page():
    """The whole point of the mark, stated as a test."""
    why = F.check_restates("Overall survival HR 0.333 (0.111 to 0.999)",
                           HELD, set())
    assert why is not None


def test_restates_ignores_a_trial_name_that_looks_like_a_figure():
    assert F.check_restates("KEYNOTE-942 CheckMate 238", HELD,
                            {"KEYNOTE-942", "CheckMate 238"}) is None


# --- scale ------------------------------------------------------------------

def test_a_real_axis_is_a_ruler():
    assert F.check_scale("0 0.5 1.0 — no effect 1.5") is None


def test_a_measurement_cannot_hide_in_an_axis():
    """This is what stops `scale` becoming the new exemption."""
    why = F.check_scale("0 0.5 0.51 1.0 1.5")
    assert why and "even steps" in why


def test_an_axis_of_two_ticks_is_not_a_scale():
    assert F.check_scale("0 1.5") is not None


def test_a_descending_or_repeated_axis_blocks():
    assert F.check_scale("1.5 1.0 0.5 0") is None      # sorted before checking
    assert F.check_scale("0 0 0") is not None


# --- computed ---------------------------------------------------------------

GOOD = ("3 / 5 1 / 5 4 / 5 4 / 5 5 / 5 5 / 5 3.4 Moderate "
        "(3×.25)+(1×.20)+(4×.15)+(4×.15)+(5×.15)+(5×.10)")


def test_the_scorecard_working_checks_out():
    assert F.check_computed(GOOD) is None


def test_a_composite_that_does_not_match_its_own_working_blocks():
    why = F.check_computed(GOOD.replace("3.4 Moderate", "4.8 Strong"))
    assert why and "comes to 3.4" in why


def test_working_that_multiplies_scores_the_page_does_not_show_blocks():
    """The arithmetic must use the scores actually displayed beside it."""
    why = F.check_computed(GOOD.replace("(1×.20)", "(5×.20)"))
    assert why and "scores shown" in why


def test_weights_that_do_not_sum_to_one_block():
    why = F.check_computed(GOOD.replace("(5×.10)", "(5×.30)"))
    assert why and "sum to" in why


def test_computed_with_no_arithmetic_shown_blocks():
    assert F.check_computed("3.4 Moderate") is not None


# --- the marks themselves ---------------------------------------------------

def test_an_unknown_mark_is_a_defect_not_a_pass(monkeypatch):
    monkeypatch.setattr(F, "bound_figures", lambda slug: HELD)
    monkeypatch.setattr(F.B, "trial_names", lambda srcs: set())
    monkeypatch.setattr(F.store, "sources", lambda slug: [])
    bad = F.findings("x", '<div data-whu="skip">anything at all</div>')
    assert bad and "not one of" in bad[0]["why"]


def test_a_void_element_does_not_swallow_the_rest_of_the_page():
    """The first run of the parser reported figures nowhere near the table.

    <br> fires a start tag and no end tag, so the marked element never closed
    and it collected the whole rest of the document. The finding was about the
    parser, not the article.
    """
    html = ('<div data-whu="restates">inside 157<br>still inside</div>'
            'OUTSIDE 60.3 months')
    got = dict((m, t) for m, t in F.marked(html))
    assert "OUTSIDE" not in got["restates"]
    assert "still inside" in got["restates"]


def test_marked_elements_are_removed_from_what_the_binder_scans():
    html = '<p>Bound prose.</p><div data-whu="scale">0 0.5 1.0</div><p>More.</p>'
    left = F.strip_marked(html)
    assert "0.5" not in left and "Bound prose" in left and "More" in left


def test_strip_marked_survives_a_void_element_inside_the_mark():
    html = '<div data-whu="restates">a<br>b</div><p>kept 60.3</p>'
    left = F.strip_marked(html)
    assert "kept 60.3" in left and ">a" not in left


def test_stripping_a_mark_does_not_fuse_a_heading_to_the_paragraph_below():
    """The first strip_marked kept only the text between tags, not the tags.

    Every heading on the page fused onto the sentence beneath it — "And one
    thing almost nobody mentioned Two specialist outlets touched it" — which is
    the defect source_ledger's BREAK sentinel exists to prevent, made again
    three days later by a function whose job was something else entirely.
    """
    html = ('<h2>A heading</h2><p>A sentence.</p>'
            '<div data-whu="scale">0 0.5 1.0</div>'
            '<h2>Another heading</h2><p>Another sentence.</p>')
    left = F.strip_marked(html)
    assert "<h2>" in left and "<p>" in left
    assert "A heading</h2>" in left
    assert "0.5" not in left
    for glued in ("A heading A sentence", "Another heading Another sentence"):
        assert glued not in left


def test_stripping_keeps_everything_outside_the_mark_byte_for_byte():
    html = '<p>before</p><span data-whu="restates">gone</span><p>after</p>'
    left = F.strip_marked(html)
    assert "<p>before</p>" in left and "<p>after</p>" in left
    assert "gone" not in left


def test_stripping_handles_nested_elements_inside_the_mark():
    html = ('<p>keep</p><div data-whu="restates"><table><tr><td>x 60.3</td>'
            '</tr></table></div><p>keep too</p>')
    left = F.strip_marked(html)
    assert "60.3" not in left and "keep" in left and "keep too" in left


def test_a_page_with_no_marks_is_returned_unchanged():
    html = '<h2>Heading</h2><p>Body with 60.3 in it.</p>'
    assert F.strip_marked(html) == html
