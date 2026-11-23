"""One orchestrator at a time (docs/whu-orchestrator.md §2.4; E4).

An exclusive fcntl lock on backend/data/whatholdsup/orchestrator.lock for the
whole run. The lock file carries the run's token and current step, which the
spend ledger's guard (spend_ledger.orch_guard) compares with the caller's
environment before any paid call.

The lock file is removed on every exit path the process can run code on
(advisor's ruling 7, 2026-11-23): a normal return, an exception, SystemExit,
KeyboardInterrupt, and SIGTERM / SIGHUP (turned into SystemExit while the lock
is held, so the same clean-up runs). It is removed only while this run still
holds the flock and only if the file still carries this run's token. A SIGKILL
runs no code; the kernel then releases the flock, so a leftover file never
blocks the next run, which overwrites it. On acquiring, the file's inode is
checked against the path's, so a run that opened the file just before another
run removed it cannot lock the orphaned inode.
"""
from __future__ import annotations

import fcntl
import json
import os
import secrets
import signal
import threading
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
        try:
            same = os.stat(self.path).st_ino == os.fstat(fh.fileno()).st_ino
        except FileNotFoundError:
            same = False
        if not same:                       # the file was removed by a run that was finishing
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()
            raise Busy("the lock file %s changed while it was being taken; try again" % self.path)
        self._fh = fh
        self._write(step="")
        self._old_handlers = {}
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGHUP):
                self._old_handlers[sig] = signal.signal(sig, _raise_exit)
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
            for sig, h in getattr(self, "_old_handlers", {}).items():
                signal.signal(sig, h)
            if _token_at(self.path) == self.token:     # a file that is not this run's is left as found
                try:
                    if os.stat(self.path).st_ino == os.fstat(self._fh.fileno()).st_ino:
                        os.unlink(self.path)    # still holding the flock: no other run can be inside
                except FileNotFoundError:
                    pass
                self._fh.seek(0)
                self._fh.truncate()
                self._fh.flush()
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
        return False


def _raise_exit(signum, frame):
    raise SystemExit(128 + signum)


def _token_at(path: Path) -> str:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("token", "")
    except (OSError, ValueError, AttributeError):
        return ""
