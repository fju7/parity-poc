#!/usr/bin/env python3
"""The fresh set's 20-sentence samples (docs/whu-check-an-answer-pilot.md §16.4, §16.9 item 2), drawn and frozen
before any v8 call.

    fresh_samples.py blind | sample

The study's code runs unchanged, as round 1 ran it (quarterly/prepare_round1.py): scripts/prepare_scoring.py is
loaded and its constants pointed at the fresh set:

  FREEZE / SEED   the commit that froze §16 (420f0d65...), read as a hexadecimal integer: the draw is
                  random.Random("<SEED>/<question>/<system>/M1").sample(pool sorted by index, 20), item ids
                  opaque("M1", ...), the judging order random.Random("<SEED>/order/M1").
  QUESTIONS       fresh_set/questions.json (six), SYSTEMS Claude, Gemini, Perplexity.
  PRIVATE         a run root whose answers/ links to answers/check_fresh_set/ and keys/ to an empty folder: the
                  fresh set has no answer keys (§16.2), so key_conclusions is [] for every question and nothing is
                  drawn for M2.
  SCORING         ~/Projects/whu-study-private/check_fresh_set/scoring/ (blinded/, m1/): sentence and source text.
  LOG             check_pilot/fresh_set/scoring/ in the repository: hashes and counts only. sampling_log.json there
                  is the frozen sample; run_fresh_v8.py run refuses to call a model until it exists.

Answers are read from their capture files by run_fresh_v8.capture's adapter choice (round 1's adapters). No model
is called.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SCRIPTS = STUDY / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import run_fresh_v8 as F  # noqa: E402

FREEZE = "420f0d654bd1806e7c8f1db28aaceeb179e1089a"
RUN_ROOT = F.OUT / "scoring"
ROOT_LINKS = RUN_ROOT / "root"
LOG = HERE / "fresh_set" / "scoring"
FROZEN = LOG / "sampling_log.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def links() -> None:
    (RUN_ROOT / "no_keys").mkdir(parents=True, exist_ok=True)
    ROOT_LINKS.mkdir(parents=True, exist_ok=True)
    for name, target in (("answers", F.ANSWERS), ("keys", RUN_ROOT / "no_keys")):
        p = ROOT_LINKS / name
        if not p.exists():
            p.symlink_to(target)
        if p.resolve() != target.resolve():
            raise SystemExit("%s does not point at %s" % (p, target))


def prep():
    links()
    ps = _load("prepare_scoring_fresh", SCRIPTS / "prepare_scoring.py")
    ps.FREEZE, ps.SEED = FREEZE, int(FREEZE, 16)
    ps.QUESTIONS = {q["id"]: q["id"] for q in F.questions()}
    ps.PRIVATE, ps.SCORING, ps.LOG = ROOT_LINKS, RUN_ROOT, LOG
    ps.SYSTEMS = list(F.SYSTEMS)
    ps.TOOL_FILE = dict(ps.TOOL_FILE, **F.TOOL)
    ps.qs = lambda _a: iter(ps.QUESTIONS)
    ps.key_conclusions = lambda _q: []                     # no keys: no M2 (§16.2)

    def tool_answer(q, system):
        import adapt
        md, fmt = F.capture(q, system)
        name = F.TOOL[system] + ".md"
        if system == "Gemini":
            return adapt.report_section(md), adapt.works_cited(md), name
        body, cited = getattr(adapt, fmt)(md)
        return body, cited, name
    ps.tool_answer = tool_answer
    return ps


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("blind", "sample"):
        raise SystemExit(__doc__)
    if F.do_verify():
        raise SystemExit("the captures are not complete and as fingerprinted")
    if cmd == "sample" and FROZEN.exists():
        raise SystemExit("%s exists: the samples are drawn once and frozen" % FROZEN)
    if cmd == "sample" and any((F.work(q, s) / "results.json").exists() for q, s in F.sample()):
        raise SystemExit("a v8 result exists: the samples must be drawn before any v8 call (§16.9 item 2)")
    ps = prep()
    return ps.do_blind(None) if cmd == "blind" else ps.do_sample(None)


if __name__ == "__main__":
    raise SystemExit(main())
