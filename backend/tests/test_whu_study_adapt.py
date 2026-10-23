"""The study's capture files, taken apart for blind.py (2026-10-23).

adapt.py takes the report out of a capture file and makes each citation marker
a link blind.py already converts, changing no wording. Synthetic captures only:
no answer is read. Free.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BL = ROOT / "study" / "whu-reliability" / "blinding"
sys.path.insert(0, str(BL))
_spec = importlib.util.spec_from_file_location("adapt_t", BL / "adapt.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)
_spec = importlib.util.spec_from_file_location("blind_adapt_t", BL / "blind.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

HEADER = "# WHU-S09 — Tool (research)\n\n- Share URL: https://example.org/share/1\n- Captured (UTC): x\n\n---\n\n"


def test_the_report_runs_from_its_heading_to_the_next_capture_boundary():
    md = (HEADER + "## Full report (verbatim, from page data)\n\nThe trial enrolled 120 adults.\n\n---\n\n"
          "## Final chat message (verbatim)\n\nHere is your report.\n\n---\n\n## Cited URLs (1)\n\n1. https://a.org/x\n")
    assert A.report_section(md).strip() == "The trial enrolled 120 adults."


def test_a_capture_heading_without_a_rule_also_ends_the_report():
    md = "# T\n\n| Field | Value |\n|---|---|\n| Share URL | u |\n\n## Report\n\nText one.\n\n## Cited URLs (in order of citation)\n\n1. https://a.org\n"
    assert A.report_section(md).strip() == "Text one."


def test_no_report_heading_stops():
    with pytest.raises(A.AdaptError):
        A.report_section("# T\n\nJust text.\n")


def test_chatgpt_page_data_markers_are_looked_up_in_the_capture_table():
    md = (HEADER + "## Report (verbatim, citation markers as in page data)\n\n"
          "Risk fell by 12%【46†L181-L190】. It rose in 2020【82†L1405-L1413】.\n\n---\n\n"
          "## Citations (from report metadata; marker -> title -> URL)\n\n"
          "1. 【46†L181-L190】 [10-20] — (pdf) A title — https://a.org/p#:~:text=Risk%20fell\n"
          "2. 【82†L1405-L1413】 [30-40] — Another — https://b.org/q\n")
    body = A.chatgpt_lenticular(md)
    assert "【" not in body
    text, refs = B.from_markdown(body)
    assert refs == ["https://a.org/p#:~:text=Risk%20fell", "https://b.org/q"]
    assert "Risk fell by 12% [1]." in " ".join(text.split())
    assert A.fragment_free(refs[0]) == "https://a.org/p"


def test_a_chatgpt_marker_missing_from_the_table_stops():
    md = (HEADER + "## Report\n\nA claim【9†L1-L2】.\n\n---\n\n## Citations (from report metadata; marker -> title -> URL)\n\n"
          "1. 【8†L1-L2】 [1-2] — T — https://a.org\n")
    with pytest.raises(A.AdaptError):
        A.chatgpt_lenticular(md)


def test_chatgpt_bracketed_links_become_markers():
    md = "## Report\n\nCosts doubled in 2019[[1]](https://a.org/r). Then fell[[2]](https://b.org/s).\n\n## Cited URLs (in order of citation)\n"
    text, refs = B.from_markdown(A.chatgpt_bracketed(md))
    assert refs == ["https://a.org/r", "https://b.org/s"]
    assert "[[" not in text and "](" not in text


def test_gemini_markdown_works_cited_numbering():
    md = (HEADER + "## Report (verbatim export)\n\nAdults improved by 30%1.\n\n#### **Works cited**\n\n"
          "> 1. A study, [https\\://a.org/1](https://a.org/1)  \n> 2. Another, [https\\://b.org/2](https://b.org/2)\n\n---\n")
    assert A.works_cited(md) == ["https://a.org/1", "https://b.org/2"]


GDOC = """<html><head><style>.c1{color:red}</style></head><body>
<h1><span>Title</span></h1>
<p><span>Mortality fell by 20% in 2021.</span><span style="vertical-align:super;font-size:8pt">2,1</span><span> More text.</span></p>
<table><tr><td><p><span>Row</span></p></td><td><p><span>Value [cite: 2]</span></p></td></tr></table>
<p><span>A formula </span><img src="data:image/png;base64,AAAA"><span> here.</span></p>
<h4><span>Works cited</span></h4>
<ol><li><span>First source, </span><a href="https://www.google.com/url?q=https://a.org/one&amp;sa=D&amp;source=editors">https://a.org/one</a></li>
<li><span>Second, </span><a href="https://www.google.com/url?q=https://b.org/two%3Fx%3D1&amp;sa=D">https://b.org/two?x=1</a></li></ol>
</body></html>"""


def test_gemini_html_superscripts_and_cite_markers_use_the_works_cited_list():
    md = A.gemini_html(GDOC)
    assert "Works cited" not in md and "First source" not in md
    text, refs = B.from_markdown(md)
    flat = " ".join(text.split())
    assert refs == ["https://b.org/two?x=1", "https://a.org/one"]   # numbered by first citation
    assert "Mortality fell by 20% in 2021 [1][2]." in flat
    assert "Value [1]" in flat                                       # [cite: 2] is Works cited entry 2
    assert B.LOST in text                                            # the image is a lost value
    assert A.gemini_html_counts(GDOC) == {"works_cited": 2, "images": 1}


def test_a_superscript_outside_works_cited_stops():
    bad = GDOC.replace(">2,1<", ">7<")
    with pytest.raises(A.AdaptError):
        A.gemini_html(bad)


def test_the_adapter_changes_no_word():
    import re
    md = A.gemini_html(GDOC)
    md = re.sub(r"!\[\]\[image\d+\]", "", md)                      # the lost-value token
    words = re.findall(r"[A-Za-z]{3,}", re.sub(r"\[(https?://[^\]]*)\]\(https?://[^)\s]+\)", "", md))
    assert words == ["Title", "Mortality", "fell", "More", "text", "Row", "Value", "formula", "here"]


def test_the_prepare_script_writes_no_answer_text_into_the_repository():
    src = (ROOT / "study" / "whu-reliability" / "scripts" / "prepare_scoring.py").read_text()
    # Everything with text goes under PRIVATE (~/Projects/whu-study-private/scoring); LOG gets hashes.
    for name in ("items.json", "uncited.json", "key_map.json", "operator_fetch.json", "blind.txt", "refs.json"):
        for line in src.splitlines():
            if name in line and "write" in line:
                assert "LOG" not in line, line
