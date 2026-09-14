"""Every router read of a Signal corpus table goes through signal_reader().

WHY
---
Migration 078 gates the corpus on signal_issues.status = 'published' with
row-level security. RLS does not bind service_role, and the backend's
ordinary client is service_role. So the gate holds for the backend only if
every router reads the corpus through the anon-key client in
backend/signal_reader.py -- and "every" has to be enforced, not remembered.
On 2026-09-14 five separate consumers read signal_claims with no status
check at all, and a sixth (the denial playbook enrichment) was found only
by grepping. This test is what makes a seventh inherit the gate.

THE RULE
--------
In backend/routers/*.py, a call `X.table("<corpus table>")` is allowed only
when, inside the same function, X was bound by `X = signal_reader()`.

Two exemptions, both explicit in the source:
  * a function decorated with a route whose path contains "/admin" -- admins
    need to see drafts;
  * a line carrying the marker `# corpus read via service role:` with a
    reason, directly above the call.

Run: python3 -m pytest backend/tests/signal/test_signal_reads_are_gated.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from signal_reader import CORPUS_TABLES  # noqa: E402

ROUTERS = sorted((BACKEND / "routers").glob("*.py"))
MARKER = "# corpus read via service role:"


def _marked(lines: list[str], lineno: int) -> bool:
    """Is the marker in the run of comment lines directly above `lineno`?"""
    i = lineno - 2
    while i >= 0 and lines[i].strip().startswith("#"):
        if MARKER in lines[i]:
            return True
        i -= 1
    return False


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else None


def _is_admin_route(fn: ast.AST) -> bool:
    for d in getattr(fn, "decorator_list", []):
        if isinstance(d, ast.Call) and d.args and isinstance(d.args[0], ast.Constant):
            if "/admin" in str(d.args[0].value):
                return True
    return False


def _reader_bound_names(fn: ast.AST, lines: list[str]) -> set[str]:
    """Names bound ONLY by signal_reader() in this function.

    A name bound once from the reader and once from the service client is
    not a reader: the second binding is what the call site may be using.
    Such a binding is allowed only with the marker directly above it.
    """
    reader, other = set(), set()
    for n in ast.walk(fn):
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if not isinstance(t, ast.Name):
                continue
            if isinstance(n.value, ast.Call) and _root_name(n.value) == "signal_reader":
                reader.add(t.id)
            elif _marked(lines, n.lineno):
                continue
            else:
                other.add(t.id)
    return reader - other


def violations(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "table" and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in CORPUS_TABLES):
            continue
        fn = node
        while fn is not None and not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = parents.get(fn)
        where = f"{path.name}:{node.lineno} .table({node.args[0].value!r})"
        if fn is None:
            out.append(where + " at module level"); continue
        if _is_admin_route(fn):
            continue
        if _marked(lines, node.lineno):
            continue
        if _root_name(node.func.value) in _reader_bound_names(fn, lines):
            continue
        out.append(where + f" in {fn.name}() is not read through signal_reader()")
    return out


@pytest.mark.parametrize("path", ROUTERS, ids=[p.name for p in ROUTERS])
def test_corpus_reads_go_through_signal_reader(path):
    bad = violations(path)
    assert not bad, "\n".join(bad)


def test_rule_catches_a_service_role_read(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("def f():\n    sb = _get_sb()\n    return sb.table('signal_claims').select('*')\n")
    assert violations(p) == ["x.py:3 .table('signal_claims') in f() is not read through signal_reader()"]


def test_rule_rejects_a_name_rebound_to_the_service_client(tmp_path):
    p = tmp_path / "z.py"
    p.write_text("def f(admin):\n    sb = signal_reader()\n    if admin:\n        sb = _get_sb()\n"
                 "    return sb.table('signal_claims')\n")
    assert len(violations(p)) == 1


def test_rule_accepts_the_reader_and_the_two_exemptions(tmp_path):
    p = tmp_path / "y.py"
    p.write_text(
        "def a():\n    sb = signal_reader()\n    return sb.table('signal_claims').select('*')\n"
        "@router.get('/admin/x')\ndef b():\n    sb = _get_sb()\n    return sb.table('signal_issues')\n"
        "def c():\n    sb = _get_sb()\n    # corpus read via service role: writes need the id\n"
        "    return sb.table('signal_issues')\n")
    assert violations(p) == []
