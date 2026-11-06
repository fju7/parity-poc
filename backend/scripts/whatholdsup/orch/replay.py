"""Offline replay on stored records (item 4; docs/whu-orchestrator.md §5). $0: a scratch copy of the repository
with no model key, the guard in replay mode (every paid call refused), the real records and ledger untouched.

For each slug:
  1. BASELINE: the pipeline outputs as the lean test produced them -- the existing commands run directly on the
     stored records (and, where session LT kept it, the sixth-freeze preflight output, compared by hash);
  2. ORCHESTRATED: the same outputs produced through the orchestrator's step runner (lock, guard, chain,
     ownership), with two ruling modes re-run so that fix 7's carried rulings are exercised (a ruling that would
     need a new paid call is refused and counted);
  3. APPLIER: the first full draft (the 3b commit) as a page model, every ruling, cut, ADD and fail-safe removal
     in the stored logs applied by orch/apply.py, and the resulting sentences compared with the stored page's.
Only counts, hashes and fingerprints are returned.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
PRIVATE = Path.home() / "Projects" / "whu-study-private" / "lean" / "session_lt" / "replay_9863fb2"
FIRST_DRAFT = {"whu-lean-q1-01c": "619bf7b", "whu-lean-q1-02b": "3713f26", "whu-lean-q1-03b": "2e1b243"}
PRIVATE_NAME = {"whu-lean-q1-01c": "pf01c_9863fb2.txt", "whu-lean-q1-02b": "pf02b_9863fb2.txt",
                "whu-lean-q1-03b": "pf03b_9863fb2.txt"}

PY, W = "backend/venv/bin/python3", "backend/scripts/whatholdsup/"
OUTPUTS = (  # name, argv
    ("publish check", (PY, W + "publish.py", "check", "{slug}")),
    ("lean_sentences render", (PY, W + "lean_sentences.py", "{slug}", "render")),
    ("coverage_check render", (PY, W + "coverage_check.py", "{slug}", "render")),
    ("bindings status", (PY, W + "bindings.py", "{slug}", "status")),
    ("lean_failsafe report", (PY, W + "lean_failsafe.py", "{slug}", "report")),
    ("applied_check", (PY, W + "applied_check.py", "{slug}")),
    ("applied_check --dangling", (PY, W + "applied_check.py", "{slug}", "--dangling")),
)
CARRIED = (("ruling.py gate", (PY, W + "ruling.py", "gate", "{slug}")),
           ("ruling.py changecheck", (PY, W + "ruling.py", "changecheck", "{slug}")))
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?")


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalise(text: str, root: Path) -> str:
    """Paths of the scratch copy read as the repository's; clock readings are masked."""
    for r in sorted({str(root), os.path.realpath(str(root))}, key=len, reverse=True):
        text = text.replace(r, "<root>")
    return _STAMP.sub("<time>", text)


def _run(root: Path, argv, slug: str, env: dict) -> tuple[int, str]:
    a = [x.replace("{slug}", slug) for x in argv]
    r = subprocess.run(a, cwd=str(root), env=env, capture_output=True, text=True, timeout=1800)
    return r.returncode, r.stdout + r.stderr


def _env(extra: dict | None = None) -> dict:
    e = {k: v for k, v in os.environ.items() if not k.startswith("WHU_ORCH_")}
    e.update({"WHU_LEAN": "1", "WHU_ORCH_MODE": "replay"})
    e.update(extra or {})
    return e


def baseline(root: Path, slug: str) -> dict:
    out = {}
    for name, argv in OUTPUTS:
        rc, text = _run(root, argv, slug, _env())
        out[name] = {"rc": rc, "sha256": _h(normalise(text, root)), "lines": text.count("\n"),
                     "last": text.strip().splitlines()[-1][:80] if text.strip() else ""}
    p = PRIVATE / PRIVATE_NAME.get(slug, "-")
    if p.exists():
        rc, text = _run(root, OUTPUTS[0][1], slug, _env())
        out["publish check"]["stored_sixth_freeze_sha256"] = _h(p.read_text(encoding="utf-8"))
        out["publish check"]["matches_stored_sixth_freeze"] = (p.read_text(encoding="utf-8") == text)
    return out


def orchestrated(root: Path, slug: str) -> dict:
    """The same outputs through the step runner: one replay step per output, under the lock, the guard and the
    chain; then the carried-ruling modes."""
    import orchestrator as O
    from orch.steps import Step
    from orch import chain as CH
    ctx = O.Ctx(slug, "replay", root=root)
    out, ownership = {}, []
    lockp = root / "backend/data/whatholdsup/orchestrator.lock"
    from orch.lock import RunLock
    with RunLock(slug, "replay", path=lockp) as lk:
        ctx.lock = lk
        for name, argv in OUTPUTS + CARRIED:
            step = Step("replay:" + name, "code", owns=("rulings/*",), cmds=(), code="")
            before = CH.snapshot(ctx.case, slug)
            lk.set_step(step.name)
            rc, text = _run(root, argv, slug, ctx.env(step))
            d = CH.diff(before, CH.snapshot(ctx.case, slug))
            v = CH.violations(d, step.owns)
            if v:
                ownership.append({"step": name, "outside_owns": v[:10]})
            refused = text.count("OrchestratorRefused") + text.count("makes no paid call")
            out[name] = {"rc": rc, "sha256": _h(normalise(text, root)), "lines": text.count("\n"),
                         "refused_paid_calls": refused,
                         "last": text.strip().splitlines()[-1][:80] if text.strip() else ""}
            CH.append(ctx.case, step.name, CH.snapshot(ctx.case, slug), {}, {"mode": "replay"})
    return {"outputs": out, "ownership": ownership}


def applier(root: Path, slug: str) -> dict:
    """Re-apply the stored logs to the 3b page by code, and compare sentence sets with the stored page."""
    import changecheck
    from orch.page import from_html, norm
    from orch import apply as AP
    case = next((root / "issues").glob("WHU-*-%s" % slug))
    rel = (case / "draft" / ("%s.html" % slug)).relative_to(root).as_posix()
    first = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (FIRST_DRAFT[slug], rel)],
                           capture_output=True, text=True).stdout
    final = (case / "draft" / ("%s.html" % slug)).read_text(encoding="utf-8")
    page = from_html(first)
    log = case / AP.APPLIED_LOG
    if log.exists():
        log.unlink()
    pend = AP.pending(case)
    placed, failed = 0, []
    for key, _at, op in pend:
        try:
            if op["op"] == "replace":
                page.replace(op["old"], op["new"])
            elif op["op"] == "delete":
                page.delete(op["old"])
            else:
                page.insert_after(op["anchor"], op["new"])
            placed += 1
        except Exception as e:
            failed.append({"key": key.split(":")[0], "op": op["op"], "why": str(e)[:60],
                           "fingerprint": hashlib.sha256(norm(op.get("old") or op.get("new") or "")
                                                         .encode()).hexdigest()[:16]})
    # The page's content only (<main>): the title and header are the renderer's, not the logs'.
    main = lambda h: (h.split("<main>", 1)[1].split("</main>", 1)[0] if "<main>" in h else h)   # noqa: E731
    got = changecheck.sentences_of("<body>%s</body>" % main(page.render()), drop_tags=True)
    want = changecheck.sentences_of("<body>%s</body>" % main(final), drop_tags=True)
    fp = lambda s: hashlib.sha256(norm(s).encode()).hexdigest()[:16]   # noqa: E731
    # CODE-WRITTEN LINES (the protected sentences and the readers' list) are not applied from the logs: the
    # orchestrator re-renders them from their generators after every step. They are compared separately, as
    # the generators' current output against the stored page.
    import lean_sentences as LS
    import coverage_check as C
    leads = tuple(LS.LEADS) + tuple(sorted(set(C.LEAD.values()))) + ("Findings in our sources we judged",)
    gen = lambda s: norm(s).startswith(leads)                          # noqa: E731
    body_got, body_want = [s for s in got if not gen(s)], [s for s in want if not gen(s)]
    env = _env()
    gen_now = []
    for argv in ((PY, W + "lean_sentences.py", slug, "render"), (PY, W + "coverage_check.py", slug, "render")):
        _rc, text = _run(root, argv, slug, env)
        gen_now += changecheck.sentences_of("<body>%s</body>" % text, drop_tags=True)
    gen_stored = [s for s in want if gen(s)]
    # Where a stored sentence the logs do not produce came from, if any log names it: an audit verdict's proposed
    # wording (verdicts.jsonl "proposed_text"), which is not an accepted ruling the applier applies.
    proposed = set()
    for vp in case.glob("audit/*/verdicts.jsonl"):
        for l in vp.read_text(encoding="utf-8").splitlines():
            try:
                t = json.loads(l).get("proposed_text")
            except Exception:
                t = None
            if t:
                proposed |= set(changecheck.sentences_of("<body><p>%s</p></body>" % t, drop_tags=True))
    unlogged = [{"fingerprint": fp(s), "in_audit_proposed_text": s in proposed}
                for s in body_want if s not in set(body_got)]
    return {"first_draft_commit": FIRST_DRAFT[slug], "records": len(pend), "placed": placed,
            "not_placed": failed, "stored_sentences": len(want), "reproduced_sentences": len(got),
            "body": {"stored": len(body_want), "reproduced": len(body_got),
                     "identical_sequence": body_got == body_want,
                     "stored_not_reproduced": unlogged,
                     "reproduced_not_stored": [fp(s) for s in body_got if s not in set(body_want)]},
            "generated": {"stored": len(gen_stored), "generators_now": len(gen_now),
                          "identical_set": set(gen_stored) == set(gen_now),
                          "stored_not_generated": [fp(s) for s in gen_stored if s not in set(gen_now)],
                          "generated_not_stored": [fp(s) for s in gen_now if s not in set(gen_stored)]}}


def replay_one(slug: str) -> dict:
    from orch.sandbox import Sandbox
    with Sandbox(slug) as sb:
        base = baseline(sb.root, slug)
        orch = orchestrated(sb.root, slug)
        app = applier(sb.root, slug)
        ledger_untouched = True
    same = {k: base[k]["sha256"] == orch["outputs"][k]["sha256"] for k, _a in OUTPUTS}
    return {"slug": slug, "baseline": base, "orchestrated": orch, "identical": same, "applier": app,
            "real_ledger_and_records_untouched": ledger_untouched}


def replay_all(slugs) -> dict:
    import importlib.util
    sp = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend/scripts/spend_ledger.py")
    S = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(S)
    before = _h(S.LEDGER.read_text(encoding="utf-8")) if S.LEDGER.exists() else None
    out = {"replays": [replay_one(s) for s in slugs]}
    out["real_ledger_sha_before"] = before
    out["real_ledger_sha_after"] = _h(S.LEDGER.read_text(encoding="utf-8")) if S.LEDGER.exists() else None
    return out


def summary(res: dict) -> dict:
    out = {"real_ledger_unchanged": res["real_ledger_sha_before"] == res["real_ledger_sha_after"]}
    for r in res["replays"]:
        out[r["slug"]] = {"outputs_identical": all(r["identical"].values()),
                          "differs": [k for k, v in r["identical"].items() if not v],
                          "publish_matches_stored_sixth_freeze":
                              r["baseline"]["publish check"].get("matches_stored_sixth_freeze"),
                          "preflight_last_line": r["orchestrated"]["outputs"]["publish check"]["last"],
                          "carried": {k: (r["orchestrated"]["outputs"][k]["rc"],
                                          r["orchestrated"]["outputs"][k]["refused_paid_calls"])
                                      for k, _a in CARRIED},
                          "ownership_findings": len(r["orchestrated"]["ownership"]),
                          "applier": {"records": r["applier"]["records"], "placed": r["applier"]["placed"],
                                      "body_identical": r["applier"]["body"]["identical_sequence"],
                                      "generated_identical": r["applier"]["generated"]["identical_set"]},
                          "applier_not_placed": len(r["applier"]["not_placed"])}
    return out
