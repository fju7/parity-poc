"""Amendment 1 of the shared assertion policy: static assertions are a
first-class enforcement locus. Every string literal in backend/ and every
source file under frontend/src is scanned by the per-class extractors; a
LEGAL_PROVISION or resolvable IDENTIFIER not covered by a reviewed allow-list
entry fails the build.

Seen to fail: the second test plants a citation in a scratch frontend file
and asserts the lint reports it.
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify import lint_literals as L  # noqa: E402


def test_no_unallowed_citation_or_identifier_in_our_own_code_or_copy():
    r = L.run()
    assert not r["hard_failures"], "\n".join(f"{h.path}:{h.line} [{h.kind}] {h.text!r}" for h in r["hard_failures"])


def test_every_allow_entry_still_covers_something():
    """An allow entry that matches nothing is dead weight, or a literal that was removed."""
    r = L.run()
    used = {h.allowed_by for h in r["allowed"]}
    for a in L._allow():
        assert a["reason"] in used, f"allow entry no longer matches any hit: {a['path']} -- remove it"


def test_lint_reports_a_planted_citation(tmp_path, monkeypatch):
    planted = tmp_path / "src" / "components"
    planted.mkdir(parents=True)
    (planted / "Planted.jsx").write_text('export const x = "Under 42 CFR § 410.32(a) this is required.";\n')
    monkeypatch.setattr(L, "FRONTEND_SRC", str(tmp_path / "src"))
    r = L.run()
    assert any("Planted.jsx" in h.path and "410.32" in h.text for h in r["hard_failures"])
