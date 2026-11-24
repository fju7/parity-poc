#!/usr/bin/env python3
"""The WHU orchestrator: code runs every lean WHU step in a fixed order (docs/whu-orchestrator.md).

    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py run <slug> --mode paid|trial
    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py replay <slug> [--out results.json]
    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py status <slug>
    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py estimate <slug> [<slug> ...]

It replaces the drafting agent. Models are called only inside the steps of orch/steps.py, each with its
inputs, outputs and limits fixed in code; every paid call passes spend_ledger.orch_guard. One run at a time
(orch/lock.py); a record changed outside the step that owns it stops the run (orch/chain.py); rulings are
applied by code (orch/apply.py). A step that needs a person ends the run Not Ready with the reason recorded.

`--mode paid` is refused in this build unless WHU_ORCH_PAID_RULED names the advisor's ruling that allows a paid
run (the build is $0 until then). `--mode trial` and `replay` run in a scratch copy of the repository
(orch/sandbox.py) whose ledger and records are discarded, and the guard refuses every paid call.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

from orch import chain as CH  # noqa: E402
from orch import steps as ST  # noqa: E402
from orch import manifest as MF  # noqa: E402
from orch.lock import RunLock, Busy  # noqa: E402
from orch.model_steps import StepFailed  # noqa: E402
from orch.page import NotPlaced  # noqa: E402

PAID_RULING_ENV = "WHU_ORCH_PAID_RULED"
REHEARSE = "rehearse"                    # the offline rehearsal (orch/rehearsal.py; Fred's term A1 after attempt 23)
SANDBOX_MARKER = ".whu_sandbox"          # written by orch/sandbox.Sandbox; rehearse mode runs only where it is


def rehearsal_module():
    """orch/rehearsal.py, loaded by path and shared as sys.modules["whu_rehearsal"] (see its load())."""
    m = sys.modules.get("whu_rehearsal")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("whu_rehearsal", HERE / "orch" / "rehearsal.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["whu_rehearsal"] = m
        spec.loader.exec_module(m)
    return m.load()


class RunStop(RuntimeError):
    """The run ends here; the reason is its recorded result."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Ctx:
    def __init__(self, slug: str, mode: str, root: Path = ROOT, ask=None, google=None, search=None):
        self.slug, self.mode, self.root = slug, mode, Path(root)
        self.case = next((self.root / "issues").glob("WHU-*-%s" % slug))
        self.page = self.case / "draft" / ("%s.html" % slug)
        self.page_json = self.case / "draft" / "page.json"
        self.gate = Path(str(self.page) + ".gate.json")
        self.ask, self.google, self.search = ask, google, search    # injected model access (tests, replay)
        self.first = None
        self.repeats = 0
        self.log: list[dict] = []
        self.frozen: dict = {}
        self.lock = None
        self.page_prev = None
        self.replies: list[dict] = []
        self.malformed: list[dict] = []     # every malformed reply and re-ask (ruling 1, 2026-11-23)

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def fmt(self, arg: str, step) -> str:
        cap = "%.2f" % step.cap_usd
        return (arg.replace("{slug}", self.slug).replace("{page}", self.rel(self.page))
                .replace("{gate}", self.rel(self.gate)).replace("{cap}", cap).replace("{first}", self.first or "")
                .replace("{stamp}", "").replace("{case}", self.rel(self.case)))

    def env(self, step) -> dict:
        e = {k: v for k, v in os.environ.items() if not k.startswith("WHU_ORCH_")}
        e.update({"WHU_LEAN": "1", "WHU_ORCH_MODE": self.mode, "WHU_ORCH_STEP": step.name,
                  "WHU_ORCH_TOKEN": self.lock.token if self.lock else "", "WHU_ORCH_ISSUE": self.slug,
                  "WHU_ORCH_ALLOW": json.dumps(ST.allow_for(step)), "WHU_ORCH_STEP_START": now(),
                  "WHU_ORCH_STEP_CAP": str(step.cap_usd), "WHU_ORCH_STEP_CALLS": str(step.max_calls)})
        if self.lock:
            e["WHU_ORCH_LOCK"] = str(self.lock.path)
        if getattr(self, "malformed_log", None):
            e["WHU_ORCH_MALFORMED_LOG"] = str(self.malformed_log)   # fc.call counts malformed replies here
        if getattr(self, "unavailable_log", None):                  # every registry lookup retried, outages logged
            e["WHU_ORCH_UNAVAILABLE_LOG"] = str(self.unavailable_log)
            e["PYTHONPATH"] = os.pathsep.join([str(SITE)] + ([e["PYTHONPATH"]] if e.get("PYTHONPATH") else []))
        if getattr(self, "model_log", None):                        # every model call retried, outages logged
            e[MODEL_LOG_ENV] = str(self.model_log)
        return e


# ---------------------------------------------------------------------------------------------------------------
# running one step
# ---------------------------------------------------------------------------------------------------------------

def run_cmds(ctx: Ctx, step) -> list[dict]:
    """Every command of STEP, its exit read through ST.EXITS (advisor's ruling after attempt 6)."""
    out = []
    env = ctx.env(step)
    for tmpl in step.cmds:
        argv = [ctx.fmt(a, step) for a in tmpl]
        script = Path(argv[1]).name if len(argv) > 1 else ""
        rules = ST.EXITS.get(script, ST.DEFAULT_EXITS)
        started = datetime.now(timezone.utc).timestamp()
        r = subprocess.run(argv, cwd=str(ctx.root), env=env, capture_output=True, text=True)
        row = {"argv": argv[1:], "rc": r.returncode, "tail": (r.stdout + r.stderr)[-1500:]}
        out.append(row)
        if step.name == "preflight":
            continue                            # read by its output, Ready or Not Ready
        rule = rules.get(r.returncode)
        if rule == "rerun":
            r = subprocess.run(argv, cwd=str(ctx.root), env=env, capture_output=True, text=True)
            row2 = {"argv": argv[1:], "rc": r.returncode, "tail": (r.stdout + r.stderr)[-1500:], "rerun": True}
            out.append(row2)
            rule = rules.get(r.returncode)
            if rule == "rerun":
                e = RunStop("%s: %s exited %d twice (rulings failed, findings left open): Not Ready"
                            % (step.name, " ".join(argv[1:3]), r.returncode))
                e.cmds = out
                raise e
            row = row2
        if rule == "proof":
            why = exit_proof(ctx, script, argv, r.returncode, started)
            row["proof"] = why if why.startswith("proved") else None
            if not why.startswith("proved"):
                e = RunStop("%s: %s exited %d without proof it completed (%s)"
                            % (step.name, " ".join(argv[1:3]), r.returncode, why))
                e.cmds = out
                raise e
            rule = "ok"
        if rule != "ok":
            e = RunStop("%s: %s exited %d" % (step.name, " ".join(argv[1:3]), r.returncode))
            e.cmds = out                        # every command so far, with its exit code and output tail
            raise e
    return out


def _arg_after(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def exit_proof(ctx: Ctx, script: str, argv: list[str], rc: int, started: float) -> str:
    """Positive proof that a command whose non-zero exit is accepted completed (advisor's ruling after attempt 6):
    an output file written by this step (newer than the command's start), parseable, whose content matches the exit.
    Returns "proved: ..." or the reason there is no proof."""
    if script == "factcheck_draft.py":
        out = _arg_after(argv, "--report")
        if not out:
            return "no --report file named (only a report run's exit 1 means findings)"
        want = "findings present"
    elif script == "changecheck_coverage.py":
        out = _arg_after(argv, "--out")
        if not out:
            return "no --out file named"
        want = "unread changed sentences listed"
    elif script == "acquire_sources.py":
        out = _arg_after(argv, "--out")
        if not out:
            return "no --out file named"
        want = "each unheld source listed with its reason"
    else:
        return "no proof rule for %s" % script
    p = Path(out) if Path(out).is_absolute() else ctx.root / out
    if not p.exists():
        return "%s was not written" % out
    if p.stat().st_mtime < started - 1:
        return "%s was not written by this step (older than its start)" % out
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return "%s is not parseable (%s)" % (out, type(e).__name__)
    if script == "factcheck_draft.py":
        if not (isinstance(doc, dict) and doc.get("passed") is False and doc.get("checked_at")):
            return "%s does not record a completed run with findings (passed is not false)" % out
    elif script == "acquire_sources.py":
        rows = doc.get("not_held") if isinstance(doc, dict) else None
        if not (isinstance(doc, dict) and doc.get("complete") is True and isinstance(rows, list) and rows
                and all(isinstance(r, dict) and r.get("id") and str(r.get("reason") or "").strip() for r in rows)):
            return "%s does not list each unheld source with its reason" % out
    else:
        if not (isinstance(doc, dict) and doc.get("complete") is True and isinstance(doc.get("missed"), list)
                and doc["missed"]):
            return "%s does not list unread changed sentences" % out
    return "proved: %s written in this step, %s" % (out, want)


def run_step(ctx: Ctx, step) -> dict:
    before = CH.snapshot(ctx.case, ctx.slug)
    if ctx.lock:
        ctx.lock.set_step(step.name)
    started = now()
    # In-process step code (a model step's call) sees the same environment a child stage gets; it is restored
    # exactly afterwards, so nothing of one step's environment outlives it.
    mine = {k: v for k, v in ctx.env(step).items() if k.startswith("WHU_ORCH_") or k == "WHU_LEAN"}
    saved = {k: os.environ.get(k) for k in mine}
    os.environ.update(mine)
    result = {"step": step.name, "start": started}
    ctx.replies = []
    try:
        result["cmds"] = run_cmds(ctx, step) if step.cmds and step.code not in ("premise",) else []
        if step.code:
            result["code"] = STEP_CODE[step.code](ctx, step)
    except BaseException as e:
        _log_failed(ctx, step, result, e)
        raise
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    try:
        page_bad = _account_page(ctx, step)
    except BaseException as e:
        _log_failed(ctx, step, result, e)
        raise
    after = CH.snapshot(ctx.case, ctx.slug)
    bad = CH.violations(CH.diff(before, after), ST.owns_for(step, ctx.slug)) + page_bad
    bad += ["frozen field changed: %s" % b for b in CH.frozen_breaks(ctx.case, ctx.frozen)]
    split = [b for b in bad if b.startswith(SPLIT_PREFIX)]
    if split:                    # the standing check (ruling after attempt 15): its own stop, before any paid audit
        e = RunStop("%s: %d page sentence(s) are not the audit's units, stopped at $0: %s"
                    % (step.name, len(split), "; ".join(split[:3])))
        _log_failed(ctx, step, result, e)
        raise e
    if bad:
        e = RunStop("%s: %s: %s" % (step.name, CH.STOP, "; ".join(bad[:6])))
        _log_failed(ctx, step, result, e)
        raise e
    for name, (fn, after_step, _why) in CH.FROZEN.items():
        if after_step == step.name:
            ctx.frozen[name] = fn(ctx.case)
    CH.append(ctx.case, step.name, after, ctx.frozen, {"mode": ctx.mode})
    result["end"] = now()
    ctx.log.append(result)
    _study_log(ctx, result)
    return result


def _log_failed(ctx: Ctx, step, result: dict, e: BaseException) -> None:
    """A failed step goes into the run record and the study log with its cost, its reason, the commands run so far
    and every reply it received -- a cut-off or unusable one included -- before the run stops (ruling 2026-11-07)."""
    if result.get("failed"):
        return
    result["failed"] = "%s: %s" % (type(e).__name__, e)
    result["end"] = now()
    if getattr(e, "cmds", None) is not None:
        result["cmds"] = e.cmds
    if getattr(e, "consistency", None) is not None:          # ruling 2 after attempt 18: outputs kept on a stop
        result["consistency"] = e.consistency
    replies = list(getattr(ctx, "replies", None) or [])
    if getattr(e, "cut_off", False) and getattr(e, "text", None) is not None and \
            not any(r.get("cut_off") for r in replies):
        replies.append({"role": None, "cut_off": True, "text": e.text, "usage": getattr(e, "usage", None)})
    result["replies"] = replies
    ctx.log.append(result)
    try:
        _study_log(ctx, result)
    except Exception:
        pass


def _account_page(ctx: Ctx, step) -> list[str]:
    """E7-E9 (orch/accounting.py): after a step that owns the page, every sentence on it and every sentence gone
    from it must have a record. The code-written blocks are first re-rendered from their generators."""
    from orch import accounting as AA
    from orch.page import Page
    if "draft/page.json" not in ST.owns_for(step, ctx.slug) or not ctx.page_json.exists():
        return []
    _rerender(ctx, Page.load(ctx.page_json))
    page = Page.load(ctx.page_json)
    q_html, limits_html, readers_html = _generated_blocks(ctx)
    generated = {"question": q_html, "limits": limits_html, "readers": readers_html, "sources": _source_list(ctx)}
    bad = AA.problems(ctx.case, page, generated, getattr(ctx, "page_prev", None))
    ctx.page_prev = AA.on_page(page)
    html = ctx.page.read_text(encoding="utf-8") if ctx.page.exists() else ""
    return bad + splitter_mismatches(ctx.slug, page, html) + entry_problems(ctx, html) + holding_problems(ctx, html)


HOLDING_PREFIX = "cites a source not held: "


def holding_problems(ctx: Ctx, html: str) -> list[str]:
    """Standing check (advisor's ruling C after attempt 21): no page sentence cites a source the holdings record
    (holdings.record) does not hold; the generated record sentences are exempt (holdings.page_problems)."""
    import bindings as B
    import holdings as HD
    if not html:
        return []
    srcs = json.loads((ctx.case / "sources.json").read_text(encoding="utf-8")).get("sources") or []
    rec = HD.classify(srcs, {s.get("id") for s in srcs if is_held(s)})   # in a run, held = full text held
    return [HOLDING_PREFIX + p for p in HD.page_problems(ctx.slug, B.page_sentences(ctx.slug, html=html),
                                                         sources=srcs, rec=rec)]


ENTRY_PREFIX = "source-list entry: "


def entry_problems(ctx: Ctx, html: str) -> list[str]:
    """Standing check (advisor's ruling 3 after attempt 18): every source-list entry on the page is its source's own
    registry record -- no doubled punctuation, one year, the first author's initials where the registry gives them."""
    import source_entries as SE
    doc = json.loads((ctx.case / "sources.json").read_text(encoding="utf-8"))
    return [ENTRY_PREFIX + p for p in SE.page_problems(doc.get("sources") or [], html)]


SPLIT_PREFIX = "page sentence is not one unit of the audit's splitter: "


def splitter_mismatches(slug: str, page, html: str) -> list[str]:
    """Standing check (advisor's ruling after attempt 15): every sentence stored on the page must be exactly one
    unit of the audit's splitter (bindings.page_sentences on the rendered page). Run after every page-changing step,
    so a mismatch stops the run at $0, before any paid audit rules on text that is on no page."""
    import bindings as B
    units = {" ".join(u.split()) for u in B.page_sentences(slug, html=html)}
    out = []
    for b in page.blocks():
        if b.get("tag") != "p":
            continue
        for s in b.get("sentences") or []:
            if " ".join(s.split()) not in units:
                out.append(SPLIT_PREFIX + "%r" % s[-160:])
    return out


def step_cost(entries: list[dict], slug: str, step: str, since: str) -> float:
    """A step's cost: the ledger rows of this issue labelled with this step, from the step's start (ruling
    2026-11-07: by the ledger's step labels, not by time alone; a row written in the same second by the step before
    is not this step's)."""
    from datetime import datetime as _dt
    t0 = _dt.fromisoformat(since)
    tot = 0.0
    for e in entries:
        if e.get("issue") != slug or e.get("step") != step:
            continue
        try:
            if _dt.fromisoformat(e.get("at")) < t0:
                continue
        except Exception:
            continue
        tot += float(e.get("usd") or 0)
    return tot


def _study_log(ctx: Ctx, r: dict) -> None:
    p = ctx.case / "study_log.md"
    if not p.exists():
        p.write_text("| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |\n"
                     "|---|---|---|---|---|---|\n", encoding="utf-8")
    import importlib.util
    sp = importlib.util.spec_from_file_location("spend_ledger", ctx.root / "backend/scripts/spend_ledger.py")
    S = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(S)
    usd = step_cost(S.entries(), ctx.slug, r["step"], r["start"])
    outcome = (r.get("code") or {}).get("outcome") if isinstance(r.get("code"), dict) else None
    if r.get("failed"):
        outcome = "FAILED: %s" % " ".join(str(r["failed"]).split())[:300]
    r["usd"] = round(usd, 6)
    with p.open("a", encoding="utf-8") as fh:
        fh.write("| %s (orchestrator) | %s | %s | $%.4f | 0 | %s |\n"
                 % (r["step"], r["start"], r.get("end", ""), usd, outcome or "done"))


# ---------------------------------------------------------------------------------------------------------------
# step code
# ---------------------------------------------------------------------------------------------------------------

def _ask_for(ctx: Ctx, step, model: str):
    """The model access a step gets: the injected one (tests), or a metered, guarded Caller."""
    if ctx.ask is not None:
        return _kept(ctx, ctx.ask)
    import audit_stage as A
    caller = A.Caller(cap=step.cap_usd, ledger_issue=ctx.slug, model=model)
    return _kept(ctx, lambda prompt, max_tokens, role: caller(prompt, max_tokens, role)[0])


def _kept(ctx: Ctx, ask):
    """ASK, with every reply put in the step's record (ctx.replies), a cut-off one with what it carried."""
    def kept(prompt, max_tokens, role):
        if getattr(ctx, "replies", None) is None:
            ctx.replies = []
        try:
            text = ask(prompt, max_tokens, role)
        except Exception as e:
            if getattr(e, "cut_off", False):
                ctx.replies.append({"role": role, "max_tokens": max_tokens, "cut_off": True,
                                    "text": getattr(e, "text", ""), "usage": getattr(e, "usage", None)})
            raise
        ctx.replies.append({"role": role, "max_tokens": max_tokens, "text": text})
        return text
    return _counting(ctx, kept)


def _counting(ctx: Ctx, ask):
    """Give ASK the note_malformed hook model_steps.ask_json reports to (ruling 1: counted in the run record)."""
    def note(role, event, text):
        if getattr(ctx, "malformed", None) is None:
            ctx.malformed = []
        ctx.malformed.append({"role": role, "event": event, "at": now(), "text": (text or "")[:20000]})
    ask.note_malformed = note
    return ask


def malformed_summary(events: list[dict]) -> dict:
    """Counts by role. "narration" (a web-search reply's text before its last search; ruling 1 after attempt 12)
    is logged and counted apart: it is not a malformed reply."""
    by: dict = {}
    for e in events:
        r = by.setdefault(e["role"], {"malformed": 0, "reasks": 0})
        if e["event"] == "narration":
            r["narration"] = r.get("narration", 0) + 1
        elif e["event"] == "multi_sentence":
            r["multi_sentence"] = r.get("multi_sentence", 0) + 1
        else:
            r["malformed" if e["event"] == "malformed" else "reasks"] += 1
    return {"malformed": sum(r["malformed"] for r in by.values()), "reasks": sum(r["reasks"] for r in by.values()),
            "narration": sum(r.get("narration", 0) for r in by.values()),
            "multi_sentence": sum(r.get("multi_sentence", 0) for r in by.values()), "by_role": by, "events": events}


def code_provenance(ctx: Ctx, step) -> dict:
    m = MF.build(ctx.root, ST.STEPS, {"mode": ctx.mode, "slug": ctx.slug})
    p = ctx.case / "orchestrator" / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    if issue.get("orchestrated") is not True:
        raise RunStop("issue.json does not say \"orchestrated\": true; the orchestrator runs only such issues")
    cap = issue.get("run_cap_usd")
    if not isinstance(cap, (int, float)) or not 0 < cap <= 10:
        raise RunStop("issue.json needs a run cap (run_cap_usd, at most $10): every paid call checks it")
    return {"outcome": "manifest written (%d code files)" % len(m["code"])}


def code_premise(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    if any((ctx.case / "sources.json").exists() for _ in [0]) and \
            (json.loads((ctx.case / "sources.json").read_text(encoding="utf-8")).get("sources") or []):
        raise RunStop("premise: sources exist before the premise; the premise is written before any source (C)")
    if not (ctx.case / "premise.json").exists():
        run_cmds(ctx, step)
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    fixed = M.premise(issue.get("question") or "", _ask_for(ctx, step, ST.DRAFT_MODEL), by=ST.DRAFT_MODEL)
    p = ctx.case / "premise.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["belief"] = dict(d.get("belief") or {}, statement=fixed["belief"]["statement"])
    for k in ("kill_condition", "reader_with_a_decision", "scope", "evidence_standard"):
        d[k] = fixed[k] if not isinstance(d.get(k), dict) else dict(d[k], **fixed[k])
    d["lead_came_from"] = issue.get("lead_came_from") or "the question in issue.json (orchestrator)"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"outcome": "premise fixed rows written before any source"}


AGENCY_HOSTS = ("who.int", "ipcc.ch", "nice.org.uk", "cdc.gov", "nih.gov", "europa.eu", "un.org",
                "worldbank.org", "oecd.org", "gov.uk")
PUBLISHER_TERMS = ("sciencedirect.com", "thelancet.com", "cell.com", "onlinelibrary.wiley.com",
                   "cochranelibrary.com", "journals.sagepub.com", "nccn.org")
NOT_SEARCHED = ("trial registries", "Crossref", "MEDLINE, Embase and CENTRAL directly", "national guidelines")


NO_TYPE = "none of these"          # ruling (b): the type field never forces a fixed type
PMC_HOSTS = ("pmc.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "europepmc.org")


def pmcid_of(url: str) -> str | None:
    import re as _re
    from urllib.parse import urlparse
    host = urlparse(url or "").netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    m = _re.search(r"\b(PMC\d{4,9})\b", url or "")
    return m.group(1) if m and host in PMC_HOSTS else None


def is_pmc(host: str, url: str) -> bool:
    """Ruling (c): PMC is an article host, never an agency's own site."""
    return host == "pmc.ncbi.nlm.nih.gov" or (host == "ncbi.nlm.nih.gov" and "/pmc/" in (url or "").lower())


def _pmcid_resolver():
    from orch import resolve as RV
    return RV.search_pmcid


def resolve_proposals(proposals: list[dict], search, search_pmcid=None) -> tuple[list[dict], list[dict]]:
    """(sources, unresolved). A proposal is kept only if a registry resolves it, or it was found on an agency's
    own site (AGENCY_HOSTS). Never an identifier the registry did not give. Publisher terms (the study rule after
    WHU-S05) by code: a blocked publisher's copy is never the URL; the Europe PMC copy is used when the registry
    gives one, else the source is recorded not held, "publisher terms"."""
    from urllib.parse import urlparse
    out, unresolved = [], []
    for i, p in enumerate(proposals, 1):
        host = urlparse(p.get("url") or "").netloc.lower()
        host = host[4:] if host.startswith("www.") else host
        if p["type"] == NO_TYPE:
            continue                                        # recorded by code_discover (ruling (b))
        got = search(p["title"], p.get("first_author"), p.get("year"),
                     "trial" if p["type"] == "registry" else "article")
        pmc = pmcid_of(p.get("url") or "")
        if getattr(got, "identifier", None) is None and pmc:
            # ruling (c): an article hosted on PMC is confirmed through Europe PMC by its PMCID
            got = (search_pmcid or _pmcid_resolver())(pmc, p["title"], p.get("first_author"), p.get("year"))
        src = {"id": "S%03d" % (len(out) + 1), "type": p["type"], "title": p["title"], "year": p.get("year"),
               "container": p.get("container") or None, "authors": p.get("first_author"),
               "used_for": p.get("why") or None, "proposed_by": "orchestrator discover step"}
        ident = getattr(got, "identifier", None)
        if ident is not None:
            kind, value = getattr(ident, "kind", None), getattr(ident, "value", None)
            if kind in ("doi", "pmid", "pmcid", "nct"):
                src[kind] = value
            src["title"] = getattr(got, "heading", None) or p["title"]
            src["registry"] = getattr(got, "registry", None)
            rec = (getattr(got, "extra", {}) or {}).get("record")
            if rec:                     # the source-list entry is built from this (source_entries, ruling 3)
                src["registry_record"] = rec
            pmcid = (getattr(got, "extra", {}) or {}).get("pmcid") or src.get("pmcid")
            if pmcid:
                src["pmcid"] = pmcid
                src["url"] = "https://europepmc.org/article/PMC/%s" % pmcid
            elif any(host.endswith(b) for b in PUBLISHER_TERMS):
                src["url"] = None
                src["access"] = {"state": "not_held", "reason": "publisher terms"}
            else:
                src["url"] = p.get("url") or None
            out.append(src)
        elif host and not is_pmc(host, p.get("url") or "") and \
                any(host == h or host.endswith("." + h) for h in AGENCY_HOSTS):
            src["url"] = p["url"]
            src["registry"] = "none (an agency's own site: %s)" % host
            out.append(src)
        else:
            unresolved.append({"proposal": p, "why": getattr(got, "reason", "not resolved"),
                               "status": getattr(got, "status", None)})
    return out, unresolved


def code_discover(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    import source_store as store
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    types = sorted(store.TYPES)
    prompt = M.discover_prompt(issue.get("question") or "", 8, types)
    searched = {"queries": [], "domains": []}
    if ctx.ask is not None:
        ask = _kept(ctx, ctx.ask)
    else:
        sys.path.insert(0, str(ctx.root / "backend" / "scripts" / "signal"))
        import factcheck_draft as fc
        fc.enter_issue(ctx.slug)

        def ask(p, max_tokens, role):          # a re-ask (ruling 1) repeats the search call
            r = fc.call("You find primary sources for a fact-check. JSON only.", p, search=True,
                        label="discover", max_tokens=max_tokens, raw=True)
            if r is None:
                raise RunStop("discover: no reply")
            if getattr(ctx, "replies", None) is None:
                ctx.replies = []
            ctx.replies.append({"role": role, "max_tokens": max_tokens, "text": r})
            for k, v in dict(fc.LAST_SEARCH).items():
                searched[k] = list(dict.fromkeys(list(searched.get(k) or []) + list(v or [])))
            return r
        ask = _counting(ctx, ask)
    reply = M.ask_json(ask, prompt, ST.REPLY_LIMITS["discover"], "discover")
    proposals = M.discover_proposals(reply, set(types), 8)
    search = ctx.search
    if search is None:
        from orch import resolve as RV
        search = RV.search
    sources, unresolved = resolve_proposals(proposals, search, getattr(ctx, "search_pmcid", None))
    # Ruling (b): a source of no type we can check is recorded, never forced into a type; the page says so.
    no_type = []
    for p in proposals:
        if p["type"] != NO_TYPE:
            continue
        got = search(p["title"], p.get("first_author"), p.get("year"), "article")
        pmc = pmcid_of(p.get("url") or "")
        if getattr(got, "identifier", None) is None and pmc:
            got = (getattr(ctx, "search_pmcid", None) or _pmcid_resolver())(pmc, p["title"], p.get("first_author"),
                                                                            p.get("year"))
        if getattr(got, "identifier", None) is None:
            unresolved.append({"proposal": p, "why": getattr(got, "reason", "not resolved"),
                               "status": getattr(got, "status", None)})
            continue
        no_type.append({"title": getattr(got, "heading", None) or p["title"], "proposed_title": p["title"],
                        "url": p.get("url") or None, "why": "not of a type we can check",
                        "registry": getattr(got, "registry", None)})
    if not sources:
        raise RunStop("discover: no proposal resolved to a source")
    for s in sources:
        s["also_called"] = [s["title"][:80]]
    doc = {"sources": sources,
           "search": {"searched": ["web search: %s" % q for q in searched.get("queries") or []] +
                      ["registry: Europe PMC"],
                      "not_searched": list(NOT_SEARCHED)},
           "unresolved_proposals": unresolved,
           "not_of_a_type": no_type}
    (ctx.case / "sources.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"outcome": "%d source(s), %d unresolved proposal(s)" % (len(sources), len(unresolved))}


def code_acquire(ctx: Ctx, step) -> dict:
    """The fetch stages ran (step.cmds). The reading records are code's: a held full text is "searched, checked
    the passages relevant to each sentence" (fix 6 builds the statement from what the stages received); nothing
    is listed as read in full, and nothing a model said is recorded."""
    import source_store as store
    doc = json.loads((ctx.case / "sources.json").read_text(encoding="utf-8"))
    for s in doc.get("sources") or []:
        acc = s.setdefault("access", {})
        acc.pop("sections", None)
        acc.pop("not_read", None)
        s["form"] = store.form_of({"type": s.get("type")})        # derived, never chosen (E6)
    (ctx.case / "sources.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    import source_ledger as SL
    from orch import corrections as CR

    def mark(s: dict, line: str, why: str) -> None:
        acc = s.setdefault("access", {})
        acc["not_held"] = {"line": line, "why": why}
        if acc.get("state") not in SL.STATES or acc.get("state") in (SL.NOT_OPENED, SL.FULL_TEXT_HELD):
            # the source ledger's own state for "we tried, by a named route, and could not get it" (or must not use it)
            acc["state"] = SL.BLOCKED
            acc["blocked_by"] = "orchestrator acquire (%s): %s" % (line, why[:300])
            acc.setdefault("on", (acc.get("last_fetch") or {}).get("on") or now()[:10])

    # Ruling 2026-11-07 (corrections and retractions): every source's bibliographic record is read for a retraction;
    # a held source's corrections are fetched as linked records; a correction to a source not held needs nothing.
    lookup, crossref, fulltext = (getattr(ctx, "lookup", None), getattr(ctx, "crossref", None),
                                  getattr(ctx, "fulltext", None))
    for s in doc.get("sources") or []:
        acc = s.setdefault("access", {})
        acc.pop("not_held", None)
        try:
            st = CR.status(s, lookup, crossref)
        except CR.RegistryUnavailable as e:    # never a status from a subset of registries (ruling 2, attempt 12)
            raise RunStop("acquire: registry unavailable; run again later (%s: %s)" % (s.get("id"), e))
        s["retraction_check"] = {"retracted": st["retracted"], "concern": st.get("concern", False), "why": st["why"],
                                 "answered": st["answered"],
                                 "corrections": st["corrections"], "on": now()[:10]}
        if st["retracted"]:
            mark(s, "retracted", "; ".join(st["why"]))
            continue
        if st.get("concern"):
            mark(s, "concern", "; ".join(st["why"]))
            continue
        if acc.get("state") != SL.FULL_TEXT_HELD or not st["corrections"]:
            continue
        held_notices, missing = [], None
        for c in st["corrections"]:
            try:
                text, how = CR.notice_text(c, lookup, fulltext)
            except CR.RegistryUnavailable as e:
                raise RunStop("acquire: registry unavailable; run again later (%s: %s)" % (s.get("id"), e))
            if text is None:
                missing = ("correction_not_held", "%s %s: %s" % (c["type"], c["id"], how))
                break
            if not CR.names_source(text, s):
                # ruling after attempt 4: a linked notice whose text does not name this source is a correction we
                # could not read (a multi-article notice, attempt 4's S002)
                missing = ("correction_unread", "%s %s: the notice's text does not name this source by title, DOI "
                                                "or PMID" % (c["type"], c["id"]))
                break
            held_notices.append(CR.hold_notice(ctx.case, c, text, how))
        if missing:
            mark(s, *missing)
        else:
            s["correction_notices"] = held_notices
    # Ruling (a): a source that could not be held is recorded "not held" and nothing on the page draws on it (the
    # passages come from held texts only); the page's limits block says so (lean_sentences, code-written lines).
    # No human search list.
    for s in doc.get("sources") or []:
        acc = s.setdefault("access", {})
        if acc.get("state") == SL.FULL_TEXT_HELD or acc.get("not_held"):
            continue
        mark(s, "could_not_hold", (acc.get("last_fetch") or {}).get("why") or acc.get("reason") or "not fetched")
    (ctx.case / "sources.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    held = [s["id"] for s in doc.get("sources") or [] if (s.get("access") or {}).get("state") == SL.FULL_TEXT_HELD]
    not_held = [s["id"] for s in doc.get("sources") or [] if (s.get("access") or {}).get("not_held")]
    # Ruling 2 after attempt 11 (2026-11-23): a registry still unavailable after acquire_sources' retries stops
    # the run; the source is never treated as not found.
    down = [s for s in doc.get("sources") or [] if s["id"] in not_held
            and ((s.get("access") or {}).get("last_fetch") or {}).get("registry_unavailable")]
    if down:
        raise RunStop("acquire: registry unavailable; run again later (%s)" % "; ".join(
            "%s: %s" % (s["id"], (s["access"]["last_fetch"].get("why") or "")[:120]) for s in down))
    if not held:
        raise RunStop("acquire: no source is held (Not Ready)")
    from orch import results as RS
    why = RS.stop_reason([s for s in doc.get("sources") or [] if s["id"] in held])
    if why:
        raise RunStop("acquire: " + why)
    import holdings as HD
    return {"outcome": "%d held, %d not held" % (len(held), len(not_held)), "not_held": not_held,
            # the one record every stage reads (ruling C after attempt 21); in a run, held = full text held
            "holdings": HD.classify(doc.get("sources") or [], held),
            "lines": {s["id"]: s["access"]["not_held"]["line"] for s in doc.get("sources") or []
                      if s["access"].get("not_held")}}


def is_held(s: dict) -> bool:
    return (s.get("access") or {}).get("state") == "full_text_held"


def _passages(ctx: Ctx, budget: int = 60000) -> dict:
    import passage_index as P
    import ruling as R
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    held = R.held_texts(ctx.slug)
    out = {}
    per = max(1, budget // max(1, len(held)))
    for sid, text in sorted(held.items()):
        idx = P.index_of(text)
        used = 0
        for p, _score in idx.top(issue.get("question") or "", k=200):
            t = text[p.start:p.end]
            if used + len(t) > per:
                break
            out["%s#%d" % (sid, p.idx)] = {"source": sid, "start": p.start, "end": p.end, "text": t}
            used += len(t)
    return out


def _cite_numbers(ctx: Ctx) -> dict:
    doc = json.loads((ctx.case / "sources.json").read_text(encoding="utf-8"))
    return {s["id"]: n for n, s in enumerate(doc.get("sources") or [], 1)}


_ENDS_IN_QUOTE = re.compile(r"^(.*?)([.!?])([\"\u201d\u2019']+)$", re.S)


def _with_marker(text: str, nums: list[int]) -> str:
    """The citation goes before the sentence's final period: "... [1].". A sentence ending in a quotation takes
    the marker after the closing quote and the period after the marker, the quoted words verbatim:
    '... are needed" [1].' (advisor's ruling after attempt 15, option a: the period moves outside the quote).
    A quotation ending in "?" or "!" keeps it inside the quote."""
    if not nums:
        return text
    mark = " [%s]" % ", ".join(str(n) for n in sorted(set(nums)))
    m = _ENDS_IN_QUOTE.match(text)
    if m:
        body, punct, quotes = m.groups()
        return body + ("" if punct == "." else punct) + quotes + mark + "."
    return text[:-1] + mark + "." if text.endswith(".") else text + mark


def _generated_blocks(ctx: Ctx) -> tuple[str, str, str]:
    """(question html, limits html, readers' list html), from the code generators."""
    import lean_sentences as LS
    import coverage_check as C
    import ruling as R
    gen = LS.render(LS.generated(ctx.slug))
    lines = [l for l in str(gen).splitlines() if l.strip()]
    q = [l for l in lines if "The question is:" in l]
    rest = [l for l in lines if l not in q and "Findings in our sources we judged" not in l
            and not l.strip().startswith(("<p>Judged", "<p>Not added", "<p>Already stated"))]
    readers = C.render(C.declarations(ctx.slug, R.held_texts(ctx.slug)))
    return "\n".join(q), "\n".join(rest), readers


def _source_list(ctx: Ctx) -> str:
    """Each entry from its source's own registry record (source_entries; advisor's ruling 3 after attempt 18)."""
    import source_entries as SE
    doc = json.loads((ctx.case / "sources.json").read_text(encoding="utf-8"))
    out = ['<div class="sources">']
    for n, s in enumerate(doc.get("sources") or [], 1):
        out.append(SE.entry_html(n, s))
    out.append("</div>")
    return "\n".join(out)


def code_draft(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    from orch.page import Page
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    passages = _passages(ctx)
    reply = M.ask_json(_ask_for(ctx, step, ST.DRAFT_MODEL), M.draft_prompt(issue.get("question") or "", passages),
                       ST.REPLY_LIMITS["draft"], "draft")
    d = M.draft_page(reply, passages)
    nums = _cite_numbers(ctx)
    q_html, limits_html, readers_html = _generated_blocks(ctx)
    blocks = [{"tag": "h2", "section": "question", "text": "The question"},
              {"tag": "html", "section": "question", "html": q_html}]
    provenance = {}
    for sec in d["sections"]:
        blocks.append({"tag": "h2", "section": sec["id"], "text": sec["heading"]})
        for b in sec["blocks"]:
            if "h3" in b:
                blocks.append({"tag": "h3", "section": sec["id"], "text": b["h3"]})
                continue
            sents = []
            for x in b["sentences"]:
                srcs = [nums[passages[p]["source"]] for p in x["passages"]]
                t = _with_marker(x["text"], srcs)
                sents.append(t)
                provenance[t] = [{k: passages[p][k] for k in ("source", "start", "end")} for p in x["passages"]]
            blocks.append({"tag": "p", "section": sec["id"], "sentences": sents})
    blocks += [{"tag": "h2", "section": "limits", "text": "What we read and what we did not"},
               {"tag": "html", "section": "limits", "html": limits_html},
               {"tag": "html", "section": "readers", "html": readers_html},
               {"tag": "h2", "section": "sources", "text": "Sources"},
               {"tag": "html", "section": "sources", "html": _source_list(ctx)}]
    page = Page({"title": d["title"], "blocks": blocks, "provenance": provenance})
    ctx.page.parent.mkdir(parents=True, exist_ok=True)
    page.save(ctx.page_json)
    ctx.page.write_text(page.render(), encoding="utf-8")
    return {"outcome": "%d sentences drafted from %d passages" % (len(provenance), len(passages))}


def _rerender(ctx: Ctx, page) -> None:
    q_html, limits_html, readers_html = _generated_blocks(ctx)
    for sec, h in (("question", q_html), ("limits", limits_html), ("readers", readers_html)):
        try:
            page.set_html(sec, h)
        except NotPlaced:
            pass
    page.save(ctx.page_json)
    ctx.page.write_text(page.render(), encoding="utf-8")


def code_bind(ctx: Ctx, step, only: list[str] | None = None) -> dict:
    """Bind each drafted sentence to the exact passages it named (code locates them; none is chosen)."""
    import bindings as B
    import ruling as R
    from orch.page import Page, norm
    page = Page.load(ctx.page_json)
    held = R.held_texts(ctx.slug)
    doc = B.load(ctx.slug)
    rows = doc.setdefault("bindings", {})
    shas = {s.get("id"): ((s.get("access") or {}).get("held") or {}).get("sha256")
            for s in json.loads((ctx.case / "sources.json").read_text(encoding="utf-8")).get("sources") or []}
    bound = 0
    for sentence, provs in (page.doc.get("provenance") or {}).items():
        if only is not None and norm(sentence) not in {norm(x) for x in only}:
            continue
        if not provs:
            continue
        sha = B.fingerprint(sentence)
        row = rows.get(sha) or B.blank_row(sentence, "drafted from a passage (orchestrator)")
        first = provs[0]
        text = held.get(first["source"]) or ""
        row.update({"on_page": True, "source_id": first["source"], "document_sha": shas.get(first["source"]),
                    "locator_type": "prose", "locator": "passage %s@%d" % (first["source"], first["start"]),
                    "span": text[first["start"]:first["end"]], "offsets": [first["start"], first["end"]],
                    "by": "code (orchestrator: the passage the draft named)"})
        row["also_rests_on"] = [{"source_id": p["source"], "span": (held.get(p["source"]) or "")[p["start"]:p["end"]],
                                 "offsets": [p["start"], p["end"]]} for p in provs[1:]] or None
        rows[sha] = row
        bound += 1
    B.save(ctx.slug, doc) if hasattr(B, "save") else (ctx.case / "bindings.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"outcome": "%d sentence(s) bound to their passages" % bound}


def _open_units(ctx: Ctx) -> list[dict]:
    """The coverage units (coverage_check's own, as its preflight row counts them) that the page neither uses, adds
    nor declares."""
    import bindings as B
    import coverage_check as C
    import lean_coverage as LC
    import omissions as O
    import premise as PM
    import ruling as R
    rows = B.load(ctx.slug).get("bindings") or {}
    held = R.held_texts(ctx.slug)
    srcs = {s["id"]: s for s in C._sources(ctx.slug)}
    spans = C.bound_ranges(rows, held)
    units = []
    for sid in C.relied_on(ctx.slug, rows, PM.load(ctx.slug) or {}):
        if sid in held:
            got, _cut = LC.split_units(C.units_of(srcs.get(sid) or {"id": sid}, held[sid], spans.get(sid)))
            units += got
    acc = C.account(units, rows, held, O.load(ctx.case), C.load(ctx.case).get("declarations") or {})
    return [u for u in acc if u["state"] == "none"]


def code_coverage(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    import coverage_check as C
    import ruling as R
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    premise = json.loads((ctx.case / "premise.json").read_text(encoding="utf-8"))
    scope = json.dumps(premise.get("scope") or {}, ensure_ascii=False)
    ask = _ask_for(ctx, step, ST.STEP_MODEL)
    open_units = _open_units(ctx)
    n, stated = 0, []
    outs = [o.get("what") for o in (premise.get("scope") or {}).get("out") or [] if o.get("what")]
    in_scope = []
    for u in open_units:
        dec = M.coverage_decision(issue.get("question") or "", scope, u["text"], ask, outs)
        if dec["decision"] == "state":
            stated.append((u, dec["sentence"]))
        elif dec["decision"] == "in_scope":
            in_scope.append({"unit": u["key"], "why": dec["why"]})     # left open: the page must use or declare it
        else:
            C.declare(ctx.slug, u["key"], dec["decision"], dec["why"], ST.STEP_MODEL, element=dec.get("element") or "")
        n += 1
    if in_scope:
        log = ctx.case / "rulings" / "coverage_in_scope.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            for r in in_scope:
                fh.write(json.dumps(dict(r, at=now()), ensure_ascii=False) + "\n")
    from orch.page import Page
    page = Page.load(ctx.page_json)
    if stated:
        # A finding the model says to state goes at the end of the findings section, bound to its own span.
        nums = _cite_numbers(ctx)
        blk = [b for b in page.blocks() if b.get("section") == "findings" and b.get("tag") == "p"]
        if not blk:
            raise RunStop("coverage: the page has no findings paragraph to state a finding in")
        for u, sentence in stated:
            s = _with_marker(sentence, [nums[u["source"]]])
            blk[-1]["sentences"].append(s)
            page.doc.setdefault("provenance", {})[s] = [{"source": u["source"], "start": u["at"][0],
                                                         "end": u["at"][1]}]
        page.save(ctx.page_json)
        code_bind(ctx, step, only=[_with_marker(x, [nums[u["source"]]]) for u, x in stated])
    _rerender(ctx, Page.load(ctx.page_json))
    return {"outcome": "%d coverage decision(s), %d left in scope" % (n, len(in_scope))}


def code_judgements(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    from orch.page import Page
    import ruling as R
    import judgements as J
    doc = J.load(ctx.case)        # the tool's own reader: no file = no decisions (ruling 1 after attempt 11)
    page = Page.load(ctx.page_json)
    held = R.held_texts(ctx.slug)
    nums = _cite_numbers(ctx)
    ask = _ask_for(ctx, step, ST.STEP_MODEL)
    import omissions as O_
    stated, declared_not_one = 0, 0
    for key, c in sorted((doc.get("candidates") or {}).items()):
        if not c.get("relevant"):
            continue
        a, b = c["at"]
        text = (held.get(c["source"]) or "")[a:b]
        try:
            js = M.judgement_sentence(text, ask)
        except M.NotOneSentence as e:     # a relevant judgement is declared in code-written text, never dropped
            R.lean_no_place(ctx.case, {"source": c["source"], "at": [a, b], "origin": "judgement:%s" % key,
                                       "origins": ["judgement:%s" % key]}, held,
                            "the judgement's sentence was not one sentence after one re-ask (%s)" % str(e)[:200],
                            outcome=O_.NOT_ADDED_NOT_ONE)
            declared_not_one += 1
            continue
        s = _with_marker(js, [nums[c["source"]]])
        blk = next(x for x in page.blocks() if x.get("section") == "findings" and x.get("tag") == "p")
        blk["sentences"].append(s)
        page.doc.setdefault("provenance", {})[s] = [{"source": c["source"], "start": a, "end": b}]
        stated += 1
    page.save(ctx.page_json)
    ctx.page.write_text(page.render(), encoding="utf-8")
    code_bind(ctx, step)
    return {"outcome": "%d judgement(s) stated" % stated + (
        "; %d declared, not one sentence after one re-ask" % declared_not_one if declared_not_one else "")}


def code_apply(ctx: Ctx, step) -> dict:
    from orch import apply as AP
    from orch.page import Page
    import applied_check as AC
    from orch.page import norm, split
    page = Page.load(ctx.page_json)
    try:
        ops = AP.apply_all(ctx.case, page)
    except NotPlaced as e:
        raise RunStop("%s: a ruling could not be placed by code: %s" % (step.name, e))
    if ops:
        # WHAT A CHANGED SENTENCE RESTS ON, by rule: a ruling's replacement rests on the passages the sentence it
        # replaced rested on (the ruling was made against them); an omission ADD rests on its finding's span.
        prov = page.doc.setdefault("provenance", {})
        by_norm = {norm(k): v for k, v in prov.items()}
        for op in ops:
            if op["op"] == "replace":
                for s in split(op["new"]):
                    prov[s] = by_norm.get(norm(op["old"]), [])
            elif op["op"] == "insert" and op.get("source") and isinstance(op.get("at"), list):
                for s in split(op["new"]):
                    prov[s] = [{"source": op["source"], "start": op["at"][0], "end": op["at"][1]}]
        page.save(ctx.page_json)
        ctx.page.write_text(page.render(), encoding="utf-8")
        code_bind(ctx, step, only=AP.bind_changed(sorted(AP.produced(ops)), ops))
    res = AC.check(ctx.case, ctx.page.read_text(encoding="utf-8"))
    if res["mismatches"]:
        raise RunStop("%s: applied_check found %d mismatch(es)" % (step.name, len(res["mismatches"])))
    # GAP-016: a reference an applied ruling left pointing at nothing is ruled (ruling.py dangling) and that
    # ruling applied, once; anything still dangling stops the run.
    rejected: list = []
    if ops and AC.dangling(ctx.case, ctx.page.read_text(encoding="utf-8")) and not _depth.get("dangling"):
        _depth["dangling"] = True
        try:
            r = subprocess.run([ST.PY, ST.W + "ruling.py", "dangling", ctx.slug], cwd=str(ctx.root),
                               env=ctx.env(step), capture_output=True, text=True)
            if r.returncode != 0:
                raise RunStop("%s: ruling.py dangling exited %d" % (step.name, r.returncode))
            more = code_apply(ctx, step)
            ops = ops + [{"op": "ruling", "n": more.get("applied", 0)}]
            page = Page.load(ctx.page_json)             # the nested apply saved a newer page
        finally:
            _depth.pop("dangling", None)
        left, rejected = dangling_unruled(ctx.case, AC.dangling(ctx.case, ctx.page.read_text(encoding="utf-8")))
        if rejected:
            lp = ctx.case / DANGLING_RULED_LOG
            lp.parent.mkdir(parents=True, exist_ok=True)
            with lp.open("a", encoding="utf-8") as fh:
                for f in rejected:
                    fh.write(json.dumps(dict(f, step=step.name, at=now()), ensure_ascii=False) + "\n")
        if left:
            raise RunStop("%s: references still point at nothing after the dangling ruling" % step.name)
    _rerender(ctx, page)
    out = {"outcome": "%d record(s) applied" % len(ops), "changed": bool(ops), "applied": len(ops)}
    if rejected:
        out["dangling_ruled_reject"] = rejected        # logged in the step's record (run_paid.json)
    return out


DANGLING_RULED_LOG = "orchestrator/dangling_ruled.jsonl"


def dangling_unruled(case: Path, found: list[dict]) -> tuple[list[dict], list[dict]]:
    """Advisor's ruling B after orchestrator trial 1 attempt 21: after the dangling ruling, a finding a recorded
    "reject" covers -- that exact finding: the term, the later sentence, and the applied ruling it came from --
    counts as ruled and is logged; the run stops only on findings no ruling covers. Code never dismisses a finding
    without a ruling: an amend or cut that still leaves the term dangling, a reject of another term, sentence or
    applied ruling, or no record at all, stays a finding."""
    rejects = set()
    lp = case / "rulings" / "rulings.jsonl"
    for line in (lp.read_text(encoding="utf-8").splitlines() if lp.exists() else []):
        r = json.loads(line) if line.strip() else {}
        if r.get("ruling_kind") != "dangling" or r.get("ruling") != "reject":
            continue
        sent = (r.get("inputs") or {}).get("sentence")
        for c in r.get("covers") or []:
            rejects.add((c.get("term"), sent, c.get("after_ruling"), r.get("id")))
    by_key = {(t, s, a): rid for t, s, a, rid in rejects}
    left, ruled = [], []
    for f in found:
        rid = by_key.get((f.get("term"), f.get("later_sentence"), f.get("log")))
        if rid:
            ruled.append({"term": f["term"], "later_sentence": f["later_sentence"], "after_ruling": f["log"],
                          "ruled_by": "rulings/rulings.jsonl id %s (reject)" % rid})
        else:
            left.append(f)
    return left, ruled


_depth: dict = {}


AUDIT_ROUNDS = 3


def code_audit(ctx: Ctx, step) -> dict:
    """Apply the audit's amends and cuts; re-audit (lean's incremental re-audit reads only what changed) until a
    round changes nothing, at most AUDIT_ROUNDS rounds in all; then the consistency audit of the last run."""
    changed_any, rounds = False, 1
    out = code_apply(ctx, step)
    while out.get("changed") and rounds < AUDIT_ROUNDS:
        changed_any = True
        run_cmds(ctx, step)
        rounds += 1
        out = code_apply(ctx, step)
    sampled = consistency_audit(ctx, step)
    return {"outcome": "%d audit round(s)" % rounds, "changed": changed_any or bool(out.get("changed")),
            "consistency": sampled}


NO_RULINGS = "no rulings to sample"


def rounds_to_sample(case: Path, slug: str) -> list[str]:
    """Advisor's ruling 1 after attempt 18: every audit round of the step (each run folder under <case>/audit) that
    has rulings and has not been sampled yet (no consistency.jsonl line with step "audit-<run>"). A withdrawn round
    or a changed prompt is NOT filtered here: consistency.py refuses it, and the refusal stops the run."""
    import consistency as CN
    done = {r.get("step") for r in CN.load(case / "rulings" / "consistency.jsonl")}
    out = []
    for run in sorted(p.name for p in (case / "audit").glob("*") if p.is_dir()):
        if "audit-%s" % run in done:
            continue
        rp = case / "audit" / run / "rulings.jsonl"
        if rp.exists() and any(l.strip() for l in rp.read_text(encoding="utf-8").splitlines()):
            out.append(run)
    return out


def consistency_audit(ctx: Ctx, step) -> dict:
    """Ruling 1 (above) and ruling 2 after attempt 18: each sampling's argv, exit code, stdout and stderr are kept in
    the run record; none to sample is recorded as NO_RULINGS, never skipped silently; a non-zero exit stops the run
    with the outputs kept."""
    runs = rounds_to_sample(ctx.case, ctx.slug)
    if not runs:
        return {"outcome": NO_RULINGS, "rounds": [], "calls": []}
    calls = []
    for run in runs:
        argv = [ST.PY, ST.W + "consistency.py", "audit", ctx.slug, run, "--cap", "%.2f" % step.cap_usd]
        r = subprocess.run(argv, cwd=str(ctx.root), env=ctx.env(step), capture_output=True, text=True)
        calls.append({"run": run, "argv": argv[1:], "rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr})
        if r.returncode != 0:
            e = RunStop("audit: consistency audit of round %s exited %d" % (run, r.returncode))
            e.consistency = {"outcome": "stopped", "rounds": runs, "calls": calls}
            raise e
    return {"outcome": "sampled %d round(s)" % len(runs), "rounds": runs, "calls": calls}


def code_corrections(ctx: Ctx, step) -> dict:
    """Ruling 2026-11-07 (3): a page sentence whose bound passage shares a figure or a 5-word run with a held
    correction notice leaves the page under the fail-safe, unless it re-binds against the notice's corrected text."""
    from orch import corrections as CR
    from orch.page import Page
    import bindings as B
    import lean_failsafe as FS
    doc = B.load(ctx.slug)
    rows = doc.get("bindings") or {}
    log = ctx.case / "rulings" / "rulings.jsonl"
    page = Page.load(ctx.page_json)
    counts = CR.sweep(ctx.case, rows, page.sentences(), lambda it: FS.record(CR.PATH, it, log))
    if counts["rebound"]:
        B.save(ctx.slug, doc) if hasattr(B, "save") else (ctx.case / "bindings.json").write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    out = code_apply(ctx, step)
    return {"outcome": "%(checked)d check(s): %(removed)d removed, %(rebound)d re-bound" % counts,
            "counts": counts, "changed": out.get("changed")}


def code_overstatement(ctx: Ctx, step) -> dict:
    from orch import overstatement as O
    from orch.google import Gateway
    import bindings as B
    import ruling as R
    import audit_stage as A
    import lean_failsafe as FS
    gw = ctx.google or Gateway(ctx.slug)
    rows = B.load(ctx.slug).get("bindings") or {}
    log = ctx.case / "rulings" / "rulings.jsonl"
    counts = O.run(ctx.case, rows, R.held_texts(ctx.slug), A.locate, gw,
                   lambda it: FS.record(O.PATH, it, log))
    out = code_apply(ctx, step)
    return {"outcome": "%(pairs)d pair(s): %(yes)d yes, %(no)d no" % counts, "counts": counts,
            "changed": out.get("changed")}


def models_reported(entries: list[dict], slug: str) -> dict:
    """{step: {model id the API reported: responses}} over this issue's ledger rows; a row with no reported id is
    counted under "(not reported)" so a gap is visible, never hidden."""
    out: dict = {}
    for e in entries:
        if e.get("issue") != slug:
            continue
        step = e.get("step") or "(no step)"
        m = e.get("model") or "(not reported)"
        out.setdefault(step, {})
        out[step][m] = out[step].get(m, 0) + 1
    return out


def record_models_reported(ctx: Ctx) -> dict:
    """Write models_reported into the run's manifest (advisor's ruling after attempt 8: alias drift is visible)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("spend_ledger", ctx.root / "backend/scripts/spend_ledger.py")
    S = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(S)
    rep = models_reported(S.entries(), ctx.slug)
    p = ctx.case / "orchestrator" / "manifest.json"
    if p.exists():
        m = json.loads(p.read_text(encoding="utf-8"))
        m["models_reported"] = rep
        p.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return rep


def source_table(case: Path) -> dict:
    """Every run's report shows the sources found, held and not held, with reasons (advisor, after attempt 8):
    the source list, the finds of no checkable type, and the proposals no registry confirmed."""
    p = Path(case) / "sources.json"
    doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    rows = []
    for s in doc.get("sources") or []:
        acc = s.get("access") or {}
        nh = acc.get("not_held") or {}
        held = acc.get("state") == "full_text_held" and not nh
        rows.append({"id": s.get("id"), "title": s.get("title"), "type": s.get("type"),
                     "held": held, "state": acc.get("state"),
                     "reason": None if held else "%s: %s" % (nh.get("line") or "not held",
                                                             nh.get("why") or acc.get("reason") or "")})
    rows += [{"id": None, "title": x.get("title"), "type": "none of these", "held": False, "state": None,
              "reason": "not_of_a_type: %s" % (x.get("why") or "")} for x in doc.get("not_of_a_type") or []]
    unresolved = [{"title": (u.get("proposal") or {}).get("title"), "reason": u.get("why")}
                  for u in doc.get("unresolved_proposals") or []]
    return {"found": len(rows), "held": sum(1 for r in rows if r["held"]),
            "not_held": sum(1 for r in rows if not r["held"]), "sources": rows,
            "proposals_not_confirmed": len(unresolved), "unconfirmed": unresolved}


def git_env() -> dict:
    """The shell's own environment for git: every WHU_* variable removed (attempt 5: the commit inherited WHU_LEAN and
    the step's variables, and the pre-commit hook's tests ran under them)."""
    return {k: v for k, v in os.environ.items() if not k.startswith("WHU_")}


def code_commit(ctx: Ctx, step) -> dict:
    if ctx.mode not in ("paid", REHEARSE):
        return {"outcome": "no commit (%s mode)" % ctx.mode}
    paths = [ctx.rel(ctx.case)]
    env = git_env()
    subprocess.run(["git", "-C", str(ctx.root), "add", "--", *paths], check=True, env=env)
    names = subprocess.run(["git", "-C", str(ctx.root), "diff", "--cached", "--name-only"], capture_output=True,
                           text=True, env=env).stdout.split()
    if any(not n.startswith(paths[0]) for n in names):
        raise RunStop("commit: staged paths outside the case folder")
    if names:
        subprocess.run(["git", "-C", str(ctx.root), "commit", "-m", "%s (orchestrator): %s" % (ctx.slug, step.name)],
                       check=True, env=env)
    if names and ctx.mode == REHEARSE:
        pass                                   # the Sandbox's own clone: committed, never pushed
    elif names:
        push = subprocess.run(["git", "-C", str(ctx.root), "push", "origin", "main"], capture_output=True, text=True,
                              env=env)
        if "main -> main" not in push.stdout + push.stderr:
            raise RunStop("commit: the push did not show 'main -> main'")
    head = subprocess.run(["git", "-C", str(ctx.root), "rev-parse", "HEAD"], capture_output=True,
                          text=True, env=env).stdout.strip()
    if step.name == "commit_3b":
        ctx.first = head
    return {"outcome": "committed %s" % head[:12], "head": head}


def code_belief(ctx: Ctx, step) -> dict:
    """Fred's term B3: one web-search call proposes outlets stating the belief; code fetches and checks each."""
    from orch import premise_reading as PRD
    if ctx.ask is not None:
        ask = _kept(ctx, ctx.ask)
    else:
        sys.path.insert(0, str(ctx.root / "backend" / "scripts" / "signal"))
        import factcheck_draft as fc
        fc.enter_issue(ctx.slug)

        def ask(p, max_tokens, role):           # a re-ask (ruling 1) repeats the search call
            r = fc.call("You find published pages that state a belief. JSON only.", p, search=True,
                        label="belief-outlet", max_tokens=max_tokens, raw=True)
            if r is None:
                raise RunStop("belief: no reply")
            ctx.replies.append({"role": role, "max_tokens": max_tokens, "text": r})
            return r
        ask = _counting(ctx, ask)
    pages = Path(os.environ.get("WHU_PRIVATE_ROOT") or (Path.home() / "Projects" / "whu-study-private")) / \
        "belief_pages" / ctx.slug

    def save(sha, body):                          # the fetched page, privately (it is the outlet's text)
        pages.mkdir(parents=True, exist_ok=True)
        (pages / ("%s.html" % sha)).write_bytes(body)
    got = PRD.belief_outlets(ctx.case, ask, ST.GATE_MODEL, save=save)
    return {"outcome": "%d outlet(s) verified of %d proposed" % (got.get("verified", 0), got.get("proposed", 0)),
            "belief": got}


def code_premise_reading(ctx: Ctx, step) -> dict:
    """Fred's term B4: direction and the kill-condition test from held sources, each quotation checked by code."""
    from orch import premise_reading as PRD
    got = PRD.direction_and_kill(ctx.case, ctx.slug, _ask_for(ctx, step, ST.CURRENT), ST.CURRENT)
    return {"outcome": "direction %s; kill condition %s" % (got.get("direction") or "not verified",
                                                           got.get("kill") or "not verified"), "reading": got}


def code_quotations(ctx: Ctx, step) -> dict:
    """Fred's term B2: quotations.json written by code from held text alone."""
    import quotations as Q
    got = Q.match_held(ctx.slug, ctx.page)
    return {"outcome": "%d quotation(s) matched verbatim, %d unmatched" % (got["matched"], len(got["unmatched"])),
            "unmatched": [q[:120] for q in got["unmatched"]]}


def code_preflight(ctx: Ctx, step) -> dict:
    old = json.loads((ctx.case / "orchestrator" / "manifest.json").read_text(encoding="utf-8"))
    diff = MF.changed(old, MF.build(ctx.root, ST.STEPS, {"mode": ctx.mode, "slug": ctx.slug}))
    if diff:
        raise RunStop("preflight: the harness changed during the run: %s" % "; ".join(diff[:5]))
    r = subprocess.run([ST.PY, ST.W + "publish.py", "check", ctx.slug], cwd=str(ctx.root), env=ctx.env(step),
                       capture_output=True, text=True)
    ready = r.stdout.strip().endswith("Ready.")
    # every STOP row in full (the tail alone cut them off; found by the offline rehearsal, 2026-11-24)
    stops = [" ".join(ln.split()) for ln in r.stdout.splitlines() if ln.lstrip().startswith("STOP")]
    return {"outcome": "Ready." if ready else "Not Ready", "stops": stops, "tail": r.stdout[-3000:]}


def code_archive(ctx: Ctx, step) -> dict:
    return {"outcome": "archive left to the paid run (no private archive in %s mode)" % ctx.mode}


STEP_CODE = {"provenance": code_provenance, "premise": code_premise, "discover": code_discover,
             "acquire": code_acquire, "draft": code_draft, "bind": code_bind, "coverage": code_coverage,
             "judgements": code_judgements, "commit": code_commit, "apply": code_apply, "audit": code_audit,
             "overstatement": code_overstatement, "corrections": code_corrections, "preflight": code_preflight,
             "archive": code_archive, "belief": code_belief, "premise_reading": code_premise_reading,
             "quotations": code_quotations}


def _checkpoint(ctx: Ctx) -> None:
    """The completed step's checkpoint (orch/checkpoint.py; Fred's term A2): paid and rehearse runs."""
    if ctx.mode not in ("paid", REHEARSE):
        return
    from orch import checkpoint as CP
    rows = CH.rows(ctx.case)
    if rows:
        CP.save(ctx.case, ctx.slug, len(rows) - 1, rows[-1]["step"], rows[-1]["hashes"], ctx.root)


def prepare_resume(ctx: Ctx, record_name: str) -> dict:
    """Verify the last checkpoint against the chain, restore the case from it, keep the previous run record and
    harness manifest beside the new ones, and return the plan run() resumes with (orch/checkpoint.py)."""
    from orch import checkpoint as CP
    rp = ctx.case / "orchestrator" / record_name
    if not rp.exists():
        raise CP.ResumeRefused("no previous run record (%s) to resume from" % rp.name)
    record = json.loads(rp.read_text(encoding="utf-8"))
    pl = CP.plan(ctx.case, ctx.slug, record, list(ST.NAMES), {s.name for s in ST.STEPS if s.repeat_group},
                 ST.MAX_REPEATS)
    old_manifest = (ctx.case / "orchestrator" / "manifest.json").read_text(encoding="utf-8") \
        if (ctx.case / "orchestrator" / "manifest.json").exists() else None
    CP.restore(ctx.case, ctx.slug, pl["checkpoint"], chain=pl["chain"])
    runs = ctx.case / "orchestrator" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    n = len(list(runs.glob("*.json"))) + 1
    (runs / ("%02d-%s" % (n, record_name))).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                                                       encoding="utf-8")
    if old_manifest is not None:
        (runs / ("%02d-manifest.json" % n)).write_text(old_manifest, encoding="utf-8")
    m = MF.build(ctx.root, ST.STEPS, {"mode": ctx.mode, "slug": ctx.slug, "resumed_at": pl["resume_at"]})
    (ctx.case / "orchestrator" / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n",
                                                             encoding="utf-8")
    pl["previous_record"] = "orchestrator/runs/%02d-%s" % (n, record_name)
    return pl


def run(ctx: Ctx, resume: dict | None = None) -> dict:
    """Every step in order; the repeat group (12-18) re-runs at most MAX_REPEATS times when a step in it changed
    the page. Returns {"result", "steps"}."""
    order = list(ST.STEPS)
    i = 0
    result = "Not Ready"
    import tempfile
    fd, log = tempfile.mkstemp(prefix="whu-orch-malformed-", suffix=".jsonl")
    os.close(fd)
    ctx.malformed_log = Path(log)          # outside the case folder: a run record input, not a case file
    from orch import registry_http as RH
    fd, ulog = tempfile.mkstemp(prefix="whu-orch-unavailable-", suffix=".jsonl")
    os.close(fd)
    ctx.unavailable_log = Path(ulog)
    if ctx.mode == "rehearse":             # the offline rehearsal's HTTP cache, under the retry wrapper
        rehearsal_module().install_http()
    RH.install(ctx.unavailable_log)        # this process; the steps' subprocesses through orch/site (env)
    # Ruling after attempt 22: every model-provider call is retried (provider_retry.call) and an outage is logged
    # here, in this process (os.environ) and in every step's subprocess (Ctx.env).
    fd, mlog = tempfile.mkstemp(prefix="whu-orch-model-unavailable-", suffix=".jsonl")
    os.close(fd)
    ctx.model_log = Path(mlog)
    _prev_mlog = os.environ.get(MODEL_LOG_ENV)
    os.environ[MODEL_LOG_ENV] = str(ctx.model_log)
    try:
        with RunLock(ctx.slug, ctx.mode, path=Path(os.environ.get("WHU_ORCH_LOCK") or
                                                     ctx.root / "backend/data/whatholdsup/orchestrator.lock")) as lk:
            ctx.lock = lk
            changed_in_group = False
            if resume:                       # the loop's state after the last completed step (orch/checkpoint.py)
                i, ctx.repeats, changed_in_group = resume["index"], resume["repeats"], resume["changed_in_group"]
                ctx.first, ctx.frozen = resume["first"], dict(resume["frozen"])
                ctx.log = [dict(s, resumed_from=resume["previous_record"]) for s in resume["log"]]
                if ctx.page_json.exists():
                    from orch import accounting as AA
                    from orch.page import Page
                    ctx.page_prev = AA.on_page(Page.load(ctx.page_json))
            while i < len(order):
                step = order[i]
                try:
                    r = run_step(ctx, step)
                except Exception:
                    _stop_if_unavailable(ctx, step)
                    raise
                try:
                    _stop_if_unavailable(ctx, step)
                except RunStop as e:
                    # an outage during a step that otherwise finished: the step did not complete (some of its calls
                    # got no reply), so it is the failed step a resume restarts at, and it gets no checkpoint
                    if ctx.log and ctx.log[-1].get("step") == step.name and not ctx.log[-1].get("failed"):
                        ctx.log[-1]["failed"] = "RunStop: %s" % e
                    raise
                _checkpoint(ctx)
                if step.repeat_group and isinstance(r.get("code"), dict) and r["code"].get("changed") \
                        and step.name != ST.BY_NAME["findings"].name:
                    changed_in_group = True
                if step.name == "changecheck" and changed_in_group and ctx.repeats < ST.MAX_REPEATS:
                    ctx.repeats += 1
                    changed_in_group = False
                    i = ST.NAMES.index("findings")
                    continue
                if step.name == "preflight":
                    result = r["code"]["outcome"]
                i += 1
    except (RunStop, StepFailed, Busy) as e:
        result = "Not Ready: %s" % e
    except Exception as e:                      # a refused paid call in trial mode lands here, recorded
        result = "Not Ready: %s: %s" % (type(e).__name__, e)
    except SystemExit as e:                     # a stage library's refusal (attempt 4: run_paid.json was lost)
        result = "Not Ready: SystemExit: %s" % e
    finally:
        RH.uninstall()
        if _prev_mlog is None:
            os.environ.pop(MODEL_LOG_ENV, None)
        else:
            os.environ[MODEL_LOG_ENV] = _prev_mlog
    events = list(getattr(ctx, "malformed", None) or []) + _stage_malformed(ctx.malformed_log)
    outages = RH.outages(ctx.unavailable_log)
    model_out = PR().outages(ctx.model_log)
    for p in (ctx.unavailable_log, ctx.model_log):
        try:
            p.unlink()
        except OSError:
            pass
    return {"result": result, "steps": ctx.log, "malformed_replies": malformed_summary(events),
            "registry_outages": outages, "model_outages": model_out}


SITE = Path(__file__).resolve().parent / "orch" / "site"


MODEL_LOG_ENV = "WHU_ORCH_MODEL_LOG"
MODEL_UNAVAILABLE = "model unavailable; run again later"


def PR():
    """provider_retry, loaded by path (the shared module object; see provider_retry.py)."""
    m = sys.modules.get("provider_retry")
    if m is None:
        import importlib.util
        s = importlib.util.spec_from_file_location("provider_retry", ROOT / "backend" / "scripts" / "provider_retry.py")
        m = importlib.util.module_from_spec(s)
        sys.modules["provider_retry"] = m
        s.loader.exec_module(m)
    return m


def _stop_if_unavailable(ctx, step) -> None:
    """A registry still unavailable after the retries, anywhere in the step: the run stops (ruling 2, attempt 12).
    A model provider still unavailable after its retries, likewise (ruling after attempt 22): read from the log,
    so a stage that caught the error and carried on still stops the run -- a check that could not run never
    passes. Both are outage stops under revised ruling 3."""
    mo = PR().outages(getattr(ctx, "model_log", None) or "")
    if mo:
        raise RunStop("%s: %s (%s)" % (step.name, MODEL_UNAVAILABLE, "; ".join(
            "%s %s: %s" % (o.get("provider"), o.get("what"), (o.get("error") or "")[:100]) for o in mo[:3])))
    from orch import registry_http as RH
    out = RH.outages(getattr(ctx, "unavailable_log", None) or "")
    if out:
        raise RunStop("%s: registry unavailable; run again later (%s)" % (
            step.name, "; ".join("%s: %s" % (o["url"][:100], o["error"][:80]) for o in out[:3])))


def rehearse_main(a) -> int:
    """Build a Sandbox, put a fresh case for --slug in it (BASE_SLUG's issue.json, its question), and run the
    orchestrator INSIDE the copy in rehearse mode, so every module -- the orchestrator's own and every stage's --
    resolves paths to the copy. Returns the run's exit code; the copy is deleted, the state folder kept."""
    import shutil
    import tempfile
    from orch.sandbox import Sandbox
    base = next((ROOT / "issues").glob("WHU-*-%s" % a.base_slug))
    state = Path(a.state) if a.state else Path(tempfile.mkdtemp(prefix="whu-rehearse-state-"))
    state.mkdir(parents=True, exist_ok=True)
    with Sandbox(a.slug) as sb:
        case = sb.root / "issues" / ("WHU-OT1-RH-%s" % a.slug)
        case.mkdir(parents=True)
        issue = json.loads((base / "issue.json").read_text(encoding="utf-8"))
        issue.update({"id": "WHU-OT1-RH", "slug": a.slug,
                      "_round_note": "Offline rehearsal copy of %s (orch/rehearsal.py); never kept." % a.base_slug})
        (case / "issue.json").write_text(json.dumps(issue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        caps = sb.root / "backend" / "data" / "spend" / "caps.json"
        c = json.loads(caps.read_text(encoding="utf-8"))
        c.setdefault("per_issue", {})[a.slug] = float(issue.get("run_cap_usd") or 10)
        caps.write_text(json.dumps(c, indent=2) + "\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("WHU_ORCH_")}
        env.update({"WHU_LEAN": "1", "WHU_ORCH_MODE": REHEARSE, "WHU_REHEARSE_STATE": str(state),
                    "WHU_PRIVATE_ROOT": str(state / "private"), "WHU_REHEARSE_BASE": str(base)})
        env.pop("WHU_LIBRARY_ROOT", None)
        if a.plan:
            env["WHU_REHEARSE_PLAN"] = str(Path(a.plan).resolve())
        if a.offline:
            env["WHU_REHEARSE_OFFLINE"] = "1"
        argv = [str(sb.root / "backend" / "venv" / "bin" / "python3"),
                str(sb.root / "backend" / "scripts" / "whatholdsup" / "orchestrator.py"), "run", a.slug, "--mode",
                REHEARSE]
        with (state / "orchestrator.log").open("w", encoding="utf-8") as fh:
            rc = subprocess.run(argv, cwd=str(sb.root), env=env, stdout=fh, stderr=subprocess.STDOUT).returncode
        rec = case / "orchestrator" / "run_rehearse.json"
        first = json.loads(rec.read_text(encoding="utf-8")) if rec.exists() else {"result": "no run record"}
        out = first
        if a.then_resume_plan:
            (state / "consumed.json").unlink(missing_ok=True)       # the second plan's entries start unconsumed
            env["WHU_REHEARSE_PLAN"] = str(Path(a.then_resume_plan).resolve())
            with (state / "orchestrator-resume.log").open("w", encoding="utf-8") as fh:
                rc = subprocess.run(argv + ["--resume"], cwd=str(sb.root), env=env, stdout=fh,
                                    stderr=subprocess.STDOUT).returncode
            out = json.loads(rec.read_text(encoding="utf-8")) if rec.exists() else {"result": "no run record"}
            out["first_run_result"] = first.get("result")
        keep = state / "case"
        if keep.exists():
            shutil.rmtree(keep)
        shutil.copytree(case, keep)                 # the rehearsal's case folder, for reading (state is private)
    summary = {"rc": rc, "result": out.get("result"), "first_run_result": out.get("first_run_result"),
               "resumed": out.get("resumed"),
               "steps": [{"step": s.get("step"), "failed": (s.get("failed") or "")[:300]} for s in
                         out.get("steps") or []],
               "malformed_replies": {k: (out.get("malformed_replies") or {}).get(k)
                                     for k in ("malformed", "reasks", "narration", "multi_sentence")},
               "model_outages": len(out.get("model_outages") or []),
               "registry_outages": len(out.get("registry_outages") or []), "state": str(state)}
    if a.out:
        Path(a.out).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return rc


def is_trial_issue(issue: dict) -> bool:
    """A paid run whose outputs are discarded by rule: an orchestrator trial ("round" starts "orchestrator
    trial"), or an issue that says "library": "trial" (a seeded-defect copy)."""
    return (str(issue.get("round") or "").lower().startswith("orchestrator trial")
            or issue.get("library") == "trial")


def trial_library(slug: str, root: Path = ROOT) -> str:
    """Ruling 5 after attempt 11 (2026-11-23): a trial issue holds its documents in the separate trial library,
    so discarded runs never mix with real holdings. Returns the library root in use, for the run record."""
    import source_store as store
    case = next((root / "issues").glob("WHU-*-%s" % slug))
    issue = json.loads((case / "issue.json").read_text(encoding="utf-8"))
    if is_trial_issue(issue):
        store.use_library(store.LIB_TRIAL)
    return str(store.LIB)


def write_run_manifest(slug: str) -> dict:
    """Every orchestrated run, whatever its result (advisor's ruling 2026-11-24): the bindings file and every stored
    document by hash, in orchestrator/provenance_manifest.json (committed with the run's records), and the files
    copied to the private study folder. A failure is recorded in the run record, never hidden."""
    import run_manifest as RM
    try:
        man = RM.build(slug)
        return {"path": RM.ORCH_MANIFEST, "files": len(man["files"]), "copied": man.get("copied"),
                "private_copy": man["private_copy"]}
    except BaseException as e:      # noqa: BLE001 -- recorded; the check fails a Ready run that has no manifest
        return {"error": "%s: %s" % (type(e).__name__, e)}


def _stage_malformed(path: Path) -> list[dict]:
    """The stages' malformed replies and re-asks (factcheck_draft.call in lean mode), then the log is removed."""
    out = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    except (OSError, ValueError):
        pass
    try:
        path.unlink()
    except OSError:
        pass
    return out


# ---------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("slug"); r.add_argument("--mode", choices=("paid", "trial", REHEARSE),
                                                                       required=True)
    r.add_argument("--resume", action="store_true",
                   help="restart at the previous run's failed step from the verified checkpoint (orch/checkpoint.py)")
    h = sub.add_parser("rehearse", help="the offline rehearsal: every step at $0 in a scratch copy")
    h.add_argument("base_slug", help="the issue whose issue.json the rehearsal copies (its question)")
    h.add_argument("--slug", default="whu-lean-orch-t1-rehearsal")
    h.add_argument("--plan", help="faults and reply shapes (JSON); see orch/rehearsal.py")
    h.add_argument("--state", help="where the rehearsal's events, unknown prompts and log go (kept)")
    h.add_argument("--offline", action="store_true", help="serve HTTP from the recorded cache only")
    h.add_argument("--out", help="write the summary (counts only) here")
    h.add_argument("--then-resume-plan", help="after the run, resume it in the same copy under this plan")
    p = sub.add_parser("replay"); p.add_argument("slug", nargs="+"); p.add_argument("--out")
    s = sub.add_parser("status"); s.add_argument("slug")
    e = sub.add_parser("estimate"); e.add_argument("slug", nargs="+"); e.add_argument("--out")
    a = ap.parse_args(argv)
    if os.environ.get("WHU_LEAN") != "1":
        print("refusing: the orchestrator runs lean WHU only (WHU_LEAN=1)")
        return 2
    if a.cmd == "rehearse":
        return rehearse_main(a)
    if a.cmd == "run":
        if a.mode == REHEARSE and not (ROOT / SANDBOX_MARKER).exists():
            print("refusing: rehearse mode runs only inside a Sandbox (orchestrator.py rehearse), never in the "
                  "repository")
            return 2
        if a.mode == "paid" and not os.environ.get(PAID_RULING_ENV, "").strip():
            print("refusing: no paid run until the advisor rules on one (set %s to the ruling's deviations row)"
                  % PAID_RULING_ENV)
            return 2
        if a.mode == "trial":
            from orch.sandbox import Sandbox
            with Sandbox(a.slug) as sb:
                out = run(Ctx(a.slug, "trial", root=sb.root))
            print(json.dumps({"result": out["result"], "steps": [x["step"] for x in out["steps"]]}, indent=1))
            return 0
        lib = trial_library(a.slug)
        ctx = Ctx(a.slug, a.mode)
        record_name = "run_paid.json" if a.mode == "paid" else "run_rehearse.json"
        resumed = None
        if getattr(a, "resume", False):
            from orch import checkpoint as CP
            try:
                resumed = prepare_resume(ctx, record_name)
            except CP.ResumeRefused as e:
                print("refusing to resume: %s" % e)
                return 2
        out = run(ctx, resume=resumed)
        if resumed:
            out["resumed"] = {"at": resumed["resume_at"], "checkpoint": resumed["checkpoint"].name,
                              "previous_record": resumed["previous_record"], "prior_result": resumed["prior_result"],
                              "verified_files": len(resumed["hashes"])}
        out["library_root"] = lib
        out["sources"] = source_table(ctx.case)          # found / held / not held, with reasons (advisor)
        out["models_reported"] = record_models_reported(ctx)   # the model id each response reported (advisor)
        out["provenance_manifest"] = write_run_manifest(a.slug)
        rec = ctx.case / "orchestrator" / record_name
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(json.dumps(dict(out, ruling=os.environ.get(PAID_RULING_ENV), ended=now()), indent=1,
                                  ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"result": out["result"], "steps": [x["step"] for x in out["steps"]],
                          "sources": out["sources"]}, indent=1, ensure_ascii=False))
        return 0 if out["result"] == "Ready." else 1
    if a.cmd == "status":
        case = next((ROOT / "issues").glob("WHU-*-%s" % a.slug))
        bad = CH.check(case, a.slug)
        print("chain: %s" % ("ok" if not bad else "; ".join(bad[:10])))
        return 0 if not bad else 1
    if a.cmd == "replay":
        from orch import replay as RP
        res = RP.replay_all(a.slug)
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(RP.summary(res), indent=1))
        return 0
    if a.cmd == "estimate":
        from orch import estimate as ES
        res = ES.estimate_all(a.slug)
        if a.out:
            Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(res["summary"], indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
