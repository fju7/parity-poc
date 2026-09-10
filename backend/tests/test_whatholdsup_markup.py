"""The structural check must fail on the page we actually served.

A check written after an incident must fail on that incident. On 2026-09-10 the
homepage went out with an anchor inside an anchor and every existing control
passed it, because the extracted text is byte-identical either way.

Both outcomes are here, and the passing half is the one that makes it a check
rather than an alarm: void elements, optional end tags and ordinary nesting must
NOT be reported, or this file becomes noise and gets ignored.
"""
import importlib.util
import sys
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("markup", WHU / "markup.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

SERVED_BROKEN = (
    '<a class="issue" href="/melanoma">\n'
    '  <span class="no">Issue one &middot; published 28 August 2026 &middot; '
    '<a href="/melanoma#updates">14 corrections</a></span>\n'
    '  <h3>The Melanoma Result</h3>\n</a>')
FIXED = SERVED_BROKEN.replace('<a href="/melanoma#updates">14 corrections</a>',
                              '14 corrections')


def kinds(html):
    return {f["kind"] for f in M.check(html)}


def test_it_fails_on_the_page_that_was_served():
    assert "NESTING" in kinds(SERVED_BROKEN), M.check(SERVED_BROKEN)


def test_it_passes_the_same_page_fixed():
    assert not M.check(FIXED), M.check(FIXED)


def test_unclosed_element():
    assert "UNCLOSED" in kinds("<div><p>text</p>")


def test_end_tag_with_no_open_tag():
    assert "MISMATCH" in kinds("<div>x</div></span>")


def test_duplicate_id_breaks_fragment_links():
    assert "DUPLICATE ID" in kinds('<p id="updates">a</p><footer id="updates">b</footer>')


# the half that makes it a check rather than an alarm
def test_void_elements_are_not_unclosed():
    assert not M.check('<div><br><img src="x.png"><hr></div>')


def test_optional_end_tags_are_not_mismatches():
    assert not M.check("<ul><li>one<li>two</ul><table><tr><td>a<td>b</table>")


def test_ordinary_nesting_is_silent():
    assert not M.check('<div><p>a <a href="/x">link</a> b</p><p>c</p></div>')


def test_every_page_we_serve_is_structurally_valid():
    bad = {p.name: M.check_file(p) for p in M.pages() if M.check_file(p)}
    assert not bad, bad


if __name__ == "__main__":
    f = 0
    for n, fn in sorted(globals().items()):
        if n.startswith("test_") and callable(fn):
            try:
                fn(); print("  ok    %s" % n)
            except AssertionError as e:
                f += 1; print("  FAIL  %s: %s" % (n, str(e)[:200]))
    print("\n%s" % ("all pass" if not f else "%d failure(s)" % f))
    raise SystemExit(1 if f else 0)
