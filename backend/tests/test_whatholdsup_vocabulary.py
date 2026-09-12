"""One word, one meaning: every check module's OK / BAD / WARN equal publish.py's.

12 September 2026: five modules defined BAD as "STOP" (the display mark) where
publish.py's state is "BLOCKED". index_dates and watch feed preflight rows
straight into publish.show(), so each blocking row they emitted was caught by
the unknown-state guard and printed with "this check returned the state
'STOP', which is not one of [...]" instead of its own message -- promoted
correctly, reason invisible. The guard caught it; this test makes it the last
time. Modules are ENUMERATED FROM THE FILESYSTEM, never listed by hand: a
hand-written list is the same failure one level up.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
NAMES = ("OK", "BAD", "WARN")


def _constants(path: Path) -> dict[str, str]:
    """Module-level string constants named OK/BAD/WARN, read from the source
    without importing it -- several modules touch the network or the shell at
    import, and the vocabulary is a fact about the file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = node.targets[0]
        names = [t.id for t in (targets.elts if isinstance(targets, ast.Tuple) else [targets])
                 if isinstance(t, ast.Name)]
        values = node.value.elts if isinstance(node.value, ast.Tuple) else [node.value]
        for n, v in zip(names, values):
            if n in NAMES and isinstance(v, ast.Constant) and isinstance(v.value, str):
                out[n] = v.value
    return out


MODULES = sorted(p for p in WHU.glob("*.py") if _constants(p) and p.name != "publish.py")
PUBLISH = _constants(WHU / "publish.py")


def test_the_enumeration_is_real():
    assert PUBLISH == {"OK": "ok", "BAD": "BLOCKED", "WARN": "warn"}
    assert len(MODULES) >= 30, "the glob found %d modules; the enumeration is broken" % len(MODULES)
    assert {p.name for p in MODULES} >= {"index_dates.py", "watch.py", "epistemic.py",
                                         "markup.py", "open_list.py"}


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_every_module_uses_publish_vocabulary(path):
    got = _constants(path)
    for name in NAMES:
        if name in got:
            assert got[name] == PUBLISH[name], (
                "%s defines %s = %r; publish.py says %r. The display mark is ' STOP'; "
                "the state is 'BLOCKED'." % (path.name, name, got[name], PUBLISH[name]))
    assert "STOP" not in got.values(), "%s uses the display mark as a state" % path.name
