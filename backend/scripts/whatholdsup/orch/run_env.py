"""The environment a run ran in, read back from its run record (advisor's ruling 2026-11-25, P103).

A probe of a run's records must see what the run saw. On 2026-11-25 a probe of WHU-OT1-02z ran without the run's
WHU_LIBRARY_ROOT, read the main library (which does not hold the trial copy of S001), and reported "1 declaration with
an empty quotation" against 10 readers'-list lines: a probe error, not a finding.

  capture()            the WHU_* settings of this process (names carrying KEY, TOKEN, SECRET or PASSWORD left out),
                       written into the run record as "environment" (orchestrator.py run);
  recorded(case)       the settings a run record names: its "environment", or for a record written before this rule,
                       its "library_root" and WHU_LEAN=1 (the orchestrator refuses to run otherwise), marked derived;
  use(slug_or_case)    apply them to this process (and source_store.LIB, which is read at import);
  python3 orch/run_env.py <slug> -- <command ...>   run a probe under the run's environment.

Diagnostics in orchestrator.py (replay, estimate, status) call use_for() by default for slugs with a run record.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RECORDS = ("run_paid.json", "run_rehearse.json")
_SECRET = ("KEY", "TOKEN", "SECRET", "PASSWORD")


class NoRunRecord(LookupError):
    pass


class RunsDisagree(ValueError):
    pass


def capture(environ=None) -> dict:
    env = os.environ if environ is None else environ
    return {k: v for k, v in sorted(env.items())
            if k.startswith("WHU_") and not any(s in k.upper() for s in _SECRET)}


def case_of(slug_or_case, root: Path = ROOT) -> Path:
    p = Path(str(slug_or_case))
    if p.is_dir():
        return p
    hits = list((Path(root) / "issues").glob("WHU-*-%s" % slug_or_case))
    if len(hits) != 1:
        raise NoRunRecord("no single case folder for %r" % (slug_or_case,))
    return hits[0]


def recorded(slug_or_case, root: Path = ROOT) -> dict:
    case = case_of(slug_or_case, root)
    for name in RECORDS:
        p = case / "orchestrator" / name
        if p.exists():
            rec = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(rec.get("environment"), dict):
                return {"env": dict(rec["environment"]), "derived": False, "record": str(p)}
            env = {"WHU_LEAN": "1"}
            if rec.get("library_root"):
                env["WHU_LIBRARY_ROOT"] = rec["library_root"]
            return {"env": env, "derived": True, "record": str(p)}
    raise NoRunRecord("no run record in %s/orchestrator" % case)


STORE = Path(__file__).resolve().parents[1] / "source_store.py"


def _is_store(mod) -> bool:
    f = getattr(mod, "__file__", None)
    try:
        return bool(f) and Path(f).resolve() == STORE
    except (OSError, TypeError):
        return False


def _stores():
    """Every loaded copy of source_store, each with its own LIB read at import: the one in sys.modules, and any copy a
    loaded module still holds (a module loaded by path, or one replaced in sys.modules after other modules imported it,
    as several test files do)."""
    out = []
    for mod in list(sys.modules.values()):
        for m in [mod] + [v for v in list(getattr(mod, "__dict__", {}).values()) if isinstance(v, type(sys))]:
            if _is_store(m) and not any(m is o for o in out):
                out.append(m)
    return out


def apply(env: dict) -> None:
    os.environ.update(env)
    if env.get("WHU_LIBRARY_ROOT"):
        for store in _stores():
            store.use_library(env["WHU_LIBRARY_ROOT"])


def snapshot() -> dict:
    """What apply() changes, to put back afterwards (tests): every source_store copy's LIB and WHU_LIBRARY_ROOT."""
    return {"stores": [(m, m.LIB) for m in _stores()], "env": os.environ.get("WHU_LIBRARY_ROOT")}


def restore(snap: dict) -> None:
    for m, lib in snap["stores"]:
        m.LIB = lib
    if snap["env"] is None:
        os.environ.pop("WHU_LIBRARY_ROOT", None)
    else:
        os.environ["WHU_LIBRARY_ROOT"] = snap["env"]


def use(slug_or_case, root: Path = ROOT) -> dict:
    got = recorded(slug_or_case, root)
    apply(got["env"])
    return got


def use_for(slugs, root: Path = ROOT) -> dict | None:
    """Apply the recorded environment shared by the slugs that have a run record; refuse if they differ (a probe
    across runs with different environments must be run once per run). None if no slug has a record."""
    envs = {}
    for s in slugs:
        try:
            envs[s] = recorded(s, root)
        except NoRunRecord:
            continue
    if not envs:
        return None
    kinds = {json.dumps(v["env"], sort_keys=True) for v in envs.values()}
    if len(kinds) > 1:
        raise RunsDisagree("these runs were made in different environments; probe them one at a time: %s"
                           % ", ".join(sorted(envs)))
    got = next(iter(envs.values()))
    apply(got["env"])
    return got


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv or argv.index("--") != 1:
        print("usage: run_env.py <slug> -- <command ...>")
        return 2
    got = recorded(argv[0])
    env = dict(os.environ, **got["env"])
    print("run_env: %s environment of %s%s" % ("derived" if got["derived"] else "recorded", got["record"],
                                                 "" if not got["derived"] else " (library_root, WHU_LEAN=1)"),
          file=sys.stderr)
    return subprocess.run(argv[2:], env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
