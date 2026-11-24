"""A code hash per step (advisor's ruling 3 after the A/B build, 2026-11-24).

Each step's hash is the sha256 of every file the step runs on:
  * the HARNESS every step runs under (HARNESS: the orchestrator, its step table, chain, ownership, lock, the spend
    ledger and the provider retry) -- a change to any of these changes every step's hash;
  * the step's own code function (orchestrator.STEP_CODE) and the local modules it imports, and each command script
    it runs (orch/steps.py `cmds`) with the local modules THAT imports, closed transitively over the WHU modules
    (backend/scripts/whatholdsup, its orch package, backend/scripts/signal), counting modules loaded by path
    ("<name>.py" named in the source) as imports.

The orchestrator records the hash in each step's chain row and log entry. A resume compares them with the code now:
a TRIAL run resumes from the earliest step whose hash changed (or the failed step, whichever is earlier); a SCORED
run never resumes across any code or document change (orchestrator.prepare_resume).
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
from pathlib import Path

WHU = Path(__file__).resolve().parents[1]
SCRIPTS = WHU.parent
ROOT = SCRIPTS.parents[1]
HARNESS = ("whatholdsup/orchestrator.py", "whatholdsup/orch/steps.py", "whatholdsup/orch/chain.py",
           "whatholdsup/orch/writes.py", "whatholdsup/orch/lock.py", "whatholdsup/orch/checkpoint.py",
           "whatholdsup/orch/code_hash.py", "spend_ledger.py", "provider_retry.py")
_PATH_LOAD = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_]*)\.py[\"']")


def _resolve(name: str) -> Path | None:
    """The local file a module name (or dotted orch.<x>) refers to, else None (a third-party or stdlib module)."""
    parts = name.split(".")
    if parts[0] == "orch":
        p = WHU / "orch" / ("%s.py" % parts[1]) if len(parts) > 1 else WHU / "orch" / "__init__.py"
        return p if p.exists() else None
    for base in (WHU, SCRIPTS / "signal", SCRIPTS):
        p = base / ("%s.py" % parts[0])
        if p.exists():
            return p
    return None


def _imports(src: str) -> set:
    out = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
            if n.module == "orch":
                out |= {"orch." + a.name for a in n.names}
    out |= set(_PATH_LOAD.findall(src))
    return out


def closure(seeds) -> set:
    """Every local file reachable from SEEDS (paths) by import or by path-load."""
    seen, todo = set(), [Path(s) for s in seeds]
    while todo:
        p = todo.pop()
        if p in seen or not p.exists():
            continue
        seen.add(p)
        for name in _imports(p.read_text(encoding="utf-8")):
            q = _resolve(name)
            if q is not None and q not in seen:
                todo.append(q)
    return seen


def _module_level(src: str) -> set:
    """The imports at a module's top level only (not those inside its functions)."""
    out = set()
    for n in ast.parse(src).body:
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
            if n.module == "orch":
                out |= {"orch." + a.name for a in n.names}
    return out


def harness_files() -> set:
    """The HARNESS files themselves, and the closure of the orchestrator's TOP-LEVEL imports (used by every step).
    Not the closure of the harness files: the orchestrator imports nearly every module inside its step functions,
    and those belong to the steps that run them."""
    files = {SCRIPTS / h for h in HARNESS}
    top = {_resolve(n) for n in _module_level((WHU / "orchestrator.py").read_text(encoding="utf-8"))}
    return files | closure([q for q in top if q is not None])


def step_files(step, step_code: dict) -> list[Path]:
    seeds = []
    extra = set()
    for argv in step.cmds or ():
        for a in argv[1:2]:
            p = ROOT / a
            if p.suffix == ".py" and p.exists():
                seeds.append(p)
    fn = step_code.get(step.code) if step.code else None
    if fn is not None:
        for name in _imports(inspect.getsource(fn)):
            q = _resolve(name)
            if q is not None:
                extra.add(q)
    return sorted(harness_files() | closure(list(seeds) + sorted(extra)))


def step_hash(step, step_code: dict) -> str:
    files = step_files(step, step_code)
    rows = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def all_hashes(steps, step_code: dict) -> dict:
    return {s.name: step_hash(s, step_code) for s in steps}
