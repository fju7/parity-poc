"""backend/scripts must never end up on sys.path.

backend/scripts/signal/ is a package literally named `signal`. If
backend/scripts is on sys.path it becomes importable as top-level `signal` and
shadows the standard library, so anyio's `from signal import Signals` resolves
to ours and EVERY import of anthropic fails. That means the gate cannot start.

It happened on 2026-08-31: wiring the spend ledger in with
sys.path.insert(0, parents[1]) broke factcheck_draft.py outright, and it was
committed without being run, because nothing here imports anthropic in a test.

    ImportError: cannot import name 'Signals' from 'signal'
    (backend/scripts/signal/__init__.py)

Load siblings with spec_from_file_location instead, which is what the rest of
the repo already does.
"""
import ast
import importlib.util
import signal as stdlib_signal
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "backend" / "scripts"


def test_the_collision_is_real_and_this_test_is_not_theatre():
    """If scripts/signal ever stops being a package, this test can be deleted."""
    assert (SCRIPTS / "signal" / "__init__.py").exists()
    assert hasattr(stdlib_signal, "Signals")


@pytest.mark.parametrize("mod", ["signal/factcheck_draft.py",
                                 "whatholdsup/publish.py",
                                 "backfill_spend.py"])
def test_no_module_puts_backend_scripts_on_sys_path(mod):
    """Static check: nothing may insert the scripts directory itself.

    Inserting a module's OWN directory (scripts/signal, scripts/whatholdsup) is
    fine and long-standing. Inserting their parent is the fault.
    """
    src = (SCRIPTS / mod).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in ("insert", "append"):
            continue
        seg = ast.unparse(node)
        if "sys.path" not in seg and "path.insert" not in seg:
            continue
        # parents[1] from scripts/<pkg>/x.py, or .parent from scripts/x.py,
        # both resolve to backend/scripts.
        depth_is_scripts = ("parents[1]" in seg if "/" in mod else ".parent" in seg)
        assert not depth_is_scripts, (
            f"{mod} puts backend/scripts on sys.path: {seg}\n"
            "That shadows the stdlib `signal` module and breaks every anthropic import."
        )


def test_importing_the_gate_leaves_stdlib_signal_intact():
    """The behavioural version. Load the gate, then check the stdlib survived."""
    spec = importlib.util.spec_from_file_location(
        "factcheck_draft_undertest", SCRIPTS / "signal" / "factcheck_draft.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    assert not any(p.rstrip("/").endswith("backend/scripts") for p in sys.path), \
        "backend/scripts got onto sys.path while loading the gate"

    import signal as after
    assert hasattr(after, "Signals"), "stdlib signal was shadowed by scripts/signal"
    assert "scripts/signal" not in getattr(after, "__file__", "")
