"""One orchestrator at a time (docs/whu-orchestrator.md §2.4; E4).

An exclusive fcntl lock on backend/data/whatholdsup/orchestrator.lock for the
whole run. The lock file carries the run's token and current step, which the
spend ledger's guard (spend_ledger.orch_guard) compares with the caller's
environment before any paid call.
"""
from __future__ import annotations

import fcntl
import json
import os
import secrets
from pathlib import Path

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "spend_ledger", Path(__file__).resolve().parents[2] / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

LOCK = S.ORCH_LOCK


class Busy(RuntimeError):
    pass


class RunLock:
    """with RunLock(slug, mode) as lk: lk.set_step("bind") ..."""

    def __init__(self, slug: str, mode: str, path: Path | None = None):
        self.slug, self.mode, self.path = slug, mode, Path(path or S.orch_lock_path())
        self.token = secrets.token_hex(16)
        self._fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+", encoding="utf-8")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            raise Busy("another orchestrator run holds %s; one run at a time (E4)" % self.path)
        self._fh = fh
        self._write(step="")
        return self

    def _write(self, **kw):
        self._fh.seek(0)
        self._fh.truncate()
        self._fh.write(json.dumps({"token": self.token, "pid": os.getpid(), "slug": self.slug,
                                   "mode": self.mode, **kw}))
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def set_step(self, step: str):
        self._write(step=step)

    def __exit__(self, *exc):
        try:
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.flush()
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
        return False
