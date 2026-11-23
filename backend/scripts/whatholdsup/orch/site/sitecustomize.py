"""Loaded at start-up by every step subprocess of an orchestrated run (the orchestrator puts this folder on
PYTHONPATH): runs the interpreter's own sitecustomize first (Homebrew's Python ships one), then installs
orch/registry_http.py's retry-then-record wrapper. Loaded by file path, so nothing is added to sys.path."""
import importlib.machinery
import importlib.util
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.machinery.PathFinder.find_spec(
    "sitecustomize", [p for p in sys.path if os.path.abspath(p or ".") != _here])
if _spec is not None and _spec.loader is not None:
    _own = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_own)

if os.environ.get("WHU_ORCH_UNAVAILABLE_LOG"):
    _p = os.path.join(os.path.dirname(_here), "registry_http.py")
    _rs = importlib.util.spec_from_file_location("whu_registry_http", _p)
    _m = importlib.util.module_from_spec(_rs)
    _rs.loader.exec_module(_m)
    _m.install(os.environ["WHU_ORCH_UNAVAILABLE_LOG"])
