"""WHU quarterly round 1: the two export forms the study's adapters did not read
(round1_deviations.md, 2026-10-29, advisor rulings 1 and 2). Synthetic captures
only: no answer is read. Free.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BL = ROOT / "study" / "whu-reliability" / "blinding"
sys.path.insert(0, str(BL))
_spec = importlib.util.spec_from_file_location("adapt_r1_t", BL / "adapt.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
_spec = importlib.util.spec_from_file_location("blind_r1_t", BL / "blind.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def capture(raw: str) -> str:
    """As tools/build_capture.py writes one: a header, the raw export, the capture's own rule and URL list."""
    return ("# WHU-Q9-01: Tool (capture file)\n\n- Tool: x\n\n## Report\n\n" + raw
            + "\n---\n\n## Cited URLs (unique, in order of first appearance; 1)\n\n1. https://z.org/\n")


CLAUDE_RULES = ("# Title\n\nCarbon removal grew 5% in 2025 \\[1\\].\n\n---\n\n## Part two\n\n"
                "Costs fell \\[2\\]\\[1\\].\n\n---\n\nLast words.\n\n## Sources\n\n"
                "1. [One](https://a.org/1)\n2. [Two](<https://b.org/2>)\n")


def test_a_rule_inside_a_claude_report_is_not_a_boundary():
    body, urls = A.claude_sources_r1(capture(CLAUDE_RULES))
    assert urls == ["https://a.org/1", "https://b.org/2"]
    assert "Costs fell" in body and "Last words." in body and body.count("---") == 2
    with pytest.raises(A.AdaptError):                       # the study's adapter stops at the first rule
        A.claude_sources(capture(CLAUDE_RULES))


def test_without_rules_claude_r1_gives_the_study_adapters_text():
    raw = CLAUDE_RULES.replace("---\n\n", "")
    assert A.claude_sources_r1(capture(raw)) == A.claude_sources(capture(raw))


def test_a_claude_r1_marker_beyond_the_sources_list_stops():
    with pytest.raises(A.AdaptError):
        A.claude_sources_r1(capture(CLAUDE_RULES.replace("\\[2\\]\\[1\\]", "\\[3\\]")))


PPLX = ("<img src=\"https://p.ai/logo.png\" style=\"height:64px\"/>\n\n# Question?\n\n"
        "Removal is small.[^1_1][^1_2] One review agrees. [Smith, 2025](https://b.org/2)\n\n"
        "| A | B |\n| :-- | :-- |\n| x | y [Jones, 2024](https://c.org/3(x)) |\n\n"
        "Later [Smith, 2025](https://b.org/2) and [d.org](https://d.org/4) and again [^1_2].\n\n"
        "[^1_1]: <https://a.org/1>\n\n[^1_2]: <https://b.org/2>\n")


def test_perplexity_footnotes_number_by_their_own_definitions():
    body, refs = A.perplexity_footnotes(capture(PPLX))
    # Definitions first, in their own order; then unmatched inline links by first appearance.
    assert refs == ["https://a.org/1", "https://b.org/2", "https://c.org/3(x)", "https://d.org/4"]
    assert "Removal is small.[1][2]" in body
    assert "Smith, 2025 [2]" in body and body.count("Smith, 2025 [2]") == 2   # equals footnote 2's URL
    assert "Jones, 2024 [3]" in body                                          # parentheses kept whole
    assert " [4] and again [2]." in body                                      # a site-name chip: marker alone
    assert "[^" not in body and "](" not in body and "a.org" not in body


def test_a_definition_whose_url_has_spaces_is_kept_whole():
    body, refs = A.perplexity_footnotes(capture(PPLX.replace("[^1_1]: <https://a.org/1>",
                                                             "[^1_1]: https://a.org/up/My File 2024.pdf")))
    assert refs[0] == "https://a.org/up/My File 2024.pdf"


def test_perplexity_r1_output_is_read_by_blind_without_links():
    body, refs = A.perplexity_footnotes(capture(PPLX))
    text, links = B.from_markdown(body)
    assert links == []
    flat = " ".join(text.split())
    assert "Removal is small.[1][2]" in flat and "Smith, 2025 [2]" in flat


def test_perplexity_r1_changes_no_word():
    body, _ = A.perplexity_footnotes(capture(PPLX))
    raw_body = PPLX.split("[^1_1]: ")[0].replace("[d.org](https://d.org/4)", "")   # a chip: no prose
    words = lambda t: re.findall(r"[A-Za-z]{2,}", re.sub(r"\[\^\d+_\d+\]|\[\d+\]", " ",
                                                         re.sub(r"\]\(https?://\S+?\)(?=[\s|]|$)", "] ", t)))
    raw_words = words(re.sub(r"<img[^>]*>", "", raw_body))
    assert words(body.replace('<img src="https://p.ai/logo.png" style="height:64px"/>', "")) == raw_words


@pytest.mark.parametrize("bad", [
    PPLX.replace("[^1_2]: <https://b.org/2>", "[^1_3]: <https://b.org/2>"),          # gap
    PPLX.replace("[^1_2]: <https://b.org/2>", "[^1_2]: a title only"),                # no URL
    PPLX.replace("again [^1_2]", "again [^1_7]"),                                    # marker with no definition
    PPLX.replace("again [^1_2]", "again [^2_1]"),                                    # another thread turn
    PPLX.replace("\n[^1_1]: <https://a.org/1>\n\n[^1_2]: <https://b.org/2>\n", "\n"),  # no definitions
])
def test_perplexity_r1_stops(bad):
    with pytest.raises(A.AdaptError):
        A.perplexity_footnotes(capture(bad))


def test_the_study_adapters_are_unchanged():
    import hashlib
    src = (BL / "adapt.py").read_text()
    study = src.split("# Quarterly round 1 (round1_deviations.md")[0] + "def works_cited" + \
        src.split("\ndef works_cited", 1)[1]
    assert "def claude_sources(md" in study and "def perplexity_sources(md" in study
    assert "claude_sources_r1" not in study and "perplexity_footnotes" not in study
    # The study's adapt.py (f1cc1941...) is this file with the round-1 block taken out.
    assert hashlib.sha256(study.encode()).hexdigest() == \
        "f1cc1941da21794fc23d9271f70502fa91b6cfbbba314f29cbfb1395da70ea01"
