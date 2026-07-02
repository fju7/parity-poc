"""PH: the appended References list contains ONLY the sources the letter body
actually cites, renumbered sequentially so body and reference list stay in sync.

Retrieval often returns extra, off-condition references (e.g. a bladder-cancer
FDA approval pulled in while appealing a colon-cancer test). Those must be dropped
from the reader-facing References list, and the surviving citations renumbered
1..k in BOTH the body's inline [n] and the list.

Deterministic, offline: no live model, no network, no DB. Exercises the pure
_render_cited_references() helper the generate_appeal tail now uses, driven by the
guard's already-computed used_keys.
"""

import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import _render_cited_references  # noqa: E402


def _keys(n):
    """Evidence pack keys E1..En with distinct, greppable reference text per item."""
    return {
        f"E{i}": {
            "source": "pubmed",
            "source_uid": str(i),
            "title": f"Study{i}",
            "citation": f"Cite{i}",
            "url": f"http://x/{i}",
            "pub_year": 2024,
            "metadata": {"authors": [f"Author{i}"], "journal": "J"},
        }
        for i in range(1, n + 1)
    }


def _refnums(refs):
    """Leading [n] labels of each reference line, in order."""
    return [ln[1:ln.index("]")] for ln in refs.splitlines() if ln.startswith("[")]


# 2.1 — DROP UNCITED: E1,E2,E5 cited of E1..E6 -> only those 3 in references.
def test_drop_uncited_references():
    ev = {"keys": _keys(6)}
    body = "Alpha [E1]. Beta [E2]. Gamma [E5]."
    _, refs = _render_cited_references(body, ev, ["E1", "E2", "E5"])
    assert refs.count("\n") == 2                      # exactly 3 lines
    assert "Study1" in refs and "Study2" in refs and "Study5" in refs
    # the uncited (often off-condition) items are gone entirely
    for dropped in ("Study3", "Study4", "Study6"):
        assert dropped not in refs, f"uncited {dropped} leaked into references"


# 2.2 — RENUMBER + SYNC: E1->1, E2->2, E5->3 in BOTH body and list.
def test_renumber_and_sync_body_and_list():
    ev = {"keys": _keys(6)}
    body = "Alpha [E1]. Beta [E2]. Gamma [E5]."
    body_render, refs = _render_cited_references(body, ev, ["E1", "E2", "E5"])
    assert body_render == "Alpha [1]. Beta [2]. Gamma [3]."   # sequential, gap-free
    assert "[E" not in body_render                            # no internal keys leak
    assert _refnums(refs) == ["1", "2", "3"]                  # list numbering matches body
    # the [3] in the body is the E5 study, and [3] in the list is Study5 -> in sync
    assert refs.splitlines()[2].startswith("[3] ") and "Study5" in refs.splitlines()[2]


# 2.3 — NO CITATIONS: body cites nothing -> no References section (empty string).
def test_no_citations_no_references_section():
    ev = {"keys": _keys(6)}
    body = "This letter makes its case without any bracketed citations."
    body_render, refs = _render_cited_references(body, ev, [])
    assert refs == ""                                # caller appends NO section, not even a header
    assert body_render == body                       # body untouched


# 2.4 — ALL CITED: every E-key used -> 1..n, nothing dropped, identity renumber.
def test_all_cited_sequential_nothing_dropped():
    ev = {"keys": _keys(4)}
    body = "W [E1] X [E2] Y [E3] Z [E4]"
    body_render, refs = _render_cited_references(body, ev, ["E1", "E2", "E3", "E4"])
    assert body_render == "W [1] X [2] Y [3] Z [4]"
    assert _refnums(refs) == ["1", "2", "3", "4"]
    for i in range(1, 5):
        assert f"Study{i}" in refs


# 2.5 — GROUPED: grouped/adjacent citations each count as used and renumber correctly.
def test_grouped_citations_all_used_and_renumbered():
    ev = {"keys": _keys(8)}
    # E3, E6, E7 cited; E6 & E7 appear as an adjacent group.
    body = "Solo [E3]. Grouped [E6][E7] support the point."
    body_render, refs = _render_cited_references(body, ev, ["E3", "E6", "E7"])
    assert body_render == "Solo [1]. Grouped [2][3] support the point."
    assert _refnums(refs) == ["1", "2", "3"]
    assert "Study3" in refs and "Study6" in refs and "Study7" in refs
    # comma-grouped form ([E6, E7]) renumbers to adjacent [2][3] as well
    body2, _ = _render_cited_references("G [E6, E7]", ev, ["E6", "E7"])
    assert body2 == "G [1][2]"
