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

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def fmt(self, arg: str, step) -> str:
        cap = "%.2f" % step.cap_usd
        return (arg.replace("{slug}", self.slug).replace("{page}", self.rel(self.page))
                .replace("{gate}", self.rel(self.gate)).replace("{cap}", cap).replace("{first}", self.first or "")
                .replace("{stamp}", ""))

    def env(self, step) -> dict:
        e = {k: v for k, v in os.environ.items() if not k.startswith("WHU_ORCH_")}
        e.update({"WHU_LEAN": "1", "WHU_ORCH_MODE": self.mode, "WHU_ORCH_STEP": step.name,
                  "WHU_ORCH_TOKEN": self.lock.token if self.lock else "", "WHU_ORCH_ISSUE": self.slug,
                  "WHU_ORCH_ALLOW": json.dumps(ST.allow_for(step)), "WHU_ORCH_STEP_START": now(),
                  "WHU_ORCH_STEP_CAP": str(step.cap_usd), "WHU_ORCH_STEP_CALLS": str(step.max_calls)})
        if self.lock:
            e["WHU_ORCH_LOCK"] = str(self.lock.path)
        return e


# ---------------------------------------------------------------------------------------------------------------
# running one step
# ---------------------------------------------------------------------------------------------------------------

def run_cmds(ctx: Ctx, step) -> list[dict]:
    out = []
    env = ctx.env(step)
    for tmpl in step.cmds:
        argv = [ctx.fmt(a, step) for a in tmpl]
        r = subprocess.run(argv, cwd=str(ctx.root), env=env, capture_output=True, text=True)
        out.append({"argv": argv[1:], "rc": r.returncode, "tail": (r.stdout + r.stderr)[-1500:]})
        if r.returncode != 0 and step.name != "preflight":
            raise RunStop("%s: %s exited %d" % (step.name, " ".join(argv[1:3]), r.returncode))
    return out


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
    try:
        result["cmds"] = run_cmds(ctx, step) if step.cmds and step.code not in ("premise",) else []
        if step.code:
            result["code"] = STEP_CODE[step.code](ctx, step)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    after = CH.snapshot(ctx.case, ctx.slug)
    bad = CH.violations(CH.diff(before, after), ST.owns_for(step, ctx.slug))
    bad += ["frozen field changed: %s" % b for b in CH.frozen_breaks(ctx.case, ctx.frozen)]
    if bad:
        raise RunStop("%s: %s: %s" % (step.name, CH.STOP, "; ".join(bad[:6])))
    for name, (fn, after_step, _why) in CH.FROZEN.items():
        if after_step == step.name:
            ctx.frozen[name] = fn(ctx.case)
    CH.append(ctx.case, step.name, after, ctx.frozen, {"mode": ctx.mode})
    result["end"] = now()
    ctx.log.append(result)
    _study_log(ctx, result)
    return result


def _study_log(ctx: Ctx, r: dict) -> None:
    p = ctx.case / "study_log.md"
    if not p.exists():
        p.write_text("| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |\n"
                     "|---|---|---|---|---|---|\n", encoding="utf-8")
    import importlib.util
    sp = importlib.util.spec_from_file_location("spend_ledger", ctx.root / "backend/scripts/spend_ledger.py")
    S = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(S)
    usd = S.spent(ctx.slug, since=r["start"])
    outcome = (r.get("code") or {}).get("outcome") if isinstance(r.get("code"), dict) else None
    with p.open("a", encoding="utf-8") as fh:
        fh.write("| %s (orchestrator) | %s | %s | $%.4f | 0 | %s |\n"
                 % (r["step"], r["start"], r.get("end", ""), usd, outcome or "done"))


# ---------------------------------------------------------------------------------------------------------------
# step code
# ---------------------------------------------------------------------------------------------------------------

def _ask_for(ctx: Ctx, step, model: str):
    """The model access a step gets: the injected one (tests), or a metered, guarded Caller."""
    if ctx.ask is not None:
        return ctx.ask
    import audit_stage as A
    caller = A.Caller(cap=step.cap_usd, ledger_issue=ctx.slug, model=model)
    return lambda prompt, max_tokens, role: caller(prompt, max_tokens, role)[0]


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


def resolve_proposals(proposals: list[dict], search) -> tuple[list[dict], list[dict]]:
    """(sources, unresolved). A proposal is kept only if a registry resolves it, or it was found on an agency's
    own site (AGENCY_HOSTS). Never an identifier the registry did not give. Publisher terms (the study rule after
    WHU-S05) by code: a blocked publisher's copy is never the URL; the Europe PMC copy is used when the registry
    gives one, else the source is recorded not held, "publisher terms"."""
    from urllib.parse import urlparse
    out, unresolved = [], []
    for i, p in enumerate(proposals, 1):
        host = urlparse(p.get("url") or "").netloc.lower()
        host = host[4:] if host.startswith("www.") else host
        got = search(p["title"], p.get("first_author"), p.get("year"),
                     "trial" if p["type"] == "registry" else "article")
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
        elif host and any(host == h or host.endswith("." + h) for h in AGENCY_HOSTS):
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
        reply = ctx.ask(prompt, 4000, "discover")
    else:
        sys.path.insert(0, str(ctx.root / "backend" / "scripts" / "signal"))
        import factcheck_draft as fc
        fc.enter_issue(ctx.slug)
        reply = fc.call("You find primary sources for a fact-check. JSON only.", prompt, search=True,
                        label="discover", max_tokens=4000)
        if reply is None:
            raise RunStop("discover: no reply")
        searched = dict(fc.LAST_SEARCH)
    proposals = M.discover_proposals(reply, set(types), 8)
    search = ctx.search
    if search is None:
        from orch import resolve as RV
        search = RV.search
    sources, unresolved = resolve_proposals(proposals, search)
    if not sources:
        raise RunStop("discover: no proposal resolved to a source")
    for s in sources:
        s["also_called"] = [s["title"][:80]]
    doc = {"sources": sources,
           "search": {"searched": ["web search: %s" % q for q in searched.get("queries") or []] +
                      ["registry: Europe PMC"],
                      "not_searched": list(NOT_SEARCHED)},
           "unresolved_proposals": unresolved}
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
    held = [s["id"] for s in doc.get("sources") or [] if (s.get("access") or {}).get("state") == "full_text_held"]
    if not held:
        raise RunStop("acquire: no source is held; a source a script cannot fetch needs a person (Not Ready)")
    return {"outcome": "%d held" % len(held)}


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


def _with_marker(text: str, nums: list[int]) -> str:
    if not nums:
        return text
    mark = " [%s]" % ", ".join(str(n) for n in sorted(set(nums)))
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
    import html as H
    doc = json.loads((ctx.case / "sources.json").read_text(encoding="utf-8"))
    out = ['<div class="sources">']
    for n, s in enumerate(doc.get("sources") or [], 1):
        text = ". ".join(x for x in (s.get("authors"), s.get("title"), s.get("container"),
                                     str(s["year"]) if s.get("year") else None) if x) + "."
        link = s.get("url") or ("https://doi.org/%s" % s["doi"] if s.get("doi") else "")
        out.append('<div class="src"><span class="tag">[%d]</span> %s</div>'
                   % (n, '<a href="%s">%s</a>' % (H.escape(link), H.escape(text)) if link else H.escape(text)))
    out.append("</div>")
    return "\n".join(out)


def code_draft(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    from orch.page import Page
    issue = json.loads((ctx.case / "issue.json").read_text(encoding="utf-8"))
    passages = _passages(ctx)
    reply = _ask_for(ctx, step, ST.DRAFT_MODEL)(M.draft_prompt(issue.get("question") or "", passages), 12000,
                                                "draft")
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
    for u in open_units:
        dec = M.coverage_decision(issue.get("question") or "", scope, u["text"], ask)
        if dec["decision"] == "state":
            stated.append((u, dec["sentence"]))
        else:
            C.declare(ctx.slug, u["key"], dec["decision"], dec["why"], ST.STEP_MODEL)
        n += 1
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
    return {"outcome": "%d coverage decision(s)" % n}


def code_judgements(ctx: Ctx, step) -> dict:
    from orch import model_steps as M
    from orch.page import Page
    import ruling as R
    doc = json.loads((ctx.case / "judgements.json").read_text(encoding="utf-8"))
    page = Page.load(ctx.page_json)
    held = R.held_texts(ctx.slug)
    nums = _cite_numbers(ctx)
    ask = _ask_for(ctx, step, ST.STEP_MODEL)
    stated = 0
    for key, c in sorted((doc.get("candidates") or {}).items()):
        if not c.get("relevant"):
            continue
        a, b = c["at"]
        text = (held.get(c["source"]) or "")[a:b]
        s = _with_marker(M.judgement_sentence(text, ask), [nums[c["source"]]])
        blk = next(x for x in page.blocks() if x.get("section") == "findings" and x.get("tag") == "p")
        blk["sentences"].append(s)
        page.doc.setdefault("provenance", {})[s] = [{"source": c["source"], "start": a, "end": b}]
        stated += 1
    page.save(ctx.page_json)
    ctx.page.write_text(page.render(), encoding="utf-8")
    code_bind(ctx, step)
    return {"outcome": "%d judgement(s) stated" % stated}


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
        if AC.dangling(ctx.case, ctx.page.read_text(encoding="utf-8")):
            raise RunStop("%s: references still point at nothing after the dangling ruling" % step.name)
    _rerender(ctx, page)
    return {"outcome": "%d record(s) applied" % len(ops), "changed": bool(ops), "applied": len(ops)}


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
    runs = sorted(p.name for p in (ctx.case / "audit").glob("*") if p.is_dir())
    if runs:
        r = subprocess.run([ST.PY, ST.W + "consistency.py", "audit", ctx.slug, runs[-1], "--cap",
                            "%.2f" % step.cap_usd], cwd=str(ctx.root), env=ctx.env(step), capture_output=True,
                           text=True)
        if r.returncode != 0:
            raise RunStop("audit: consistency audit exited %d" % r.returncode)
    return {"outcome": "%d audit round(s)" % rounds, "changed": changed_any or bool(out.get("changed"))}


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


def code_commit(ctx: Ctx, step) -> dict:
    if ctx.mode != "paid":
        return {"outcome": "no commit (%s mode)" % ctx.mode}
    paths = [ctx.rel(ctx.case)]
    subprocess.run(["git", "-C", str(ctx.root), "add", "--", *paths], check=True)
    names = subprocess.run(["git", "-C", str(ctx.root), "diff", "--cached", "--name-only"], capture_output=True,
                           text=True).stdout.split()
    if any(not n.startswith(paths[0]) for n in names):
        raise RunStop("commit: staged paths outside the case folder")
    if names:
        subprocess.run(["git", "-C", str(ctx.root), "commit", "-m", "%s (orchestrator): %s" % (ctx.slug, step.name)],
                       check=True)
        push = subprocess.run(["git", "-C", str(ctx.root), "push", "origin", "main"], capture_output=True, text=True)
        if "main -> main" not in push.stdout + push.stderr:
            raise RunStop("commit: the push did not show 'main -> main'")
    head = subprocess.run(["git", "-C", str(ctx.root), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    if step.name == "commit_3b":
        ctx.first = head
    return {"outcome": "committed %s" % head[:12]}


def code_preflight(ctx: Ctx, step) -> dict:
    old = json.loads((ctx.case / "orchestrator" / "manifest.json").read_text(encoding="utf-8"))
    diff = MF.changed(old, MF.build(ctx.root, ST.STEPS, {"mode": ctx.mode, "slug": ctx.slug}))
    if diff:
        raise RunStop("preflight: the harness changed during the run: %s" % "; ".join(diff[:5]))
    r = subprocess.run([ST.PY, ST.W + "publish.py", "check", ctx.slug], cwd=str(ctx.root), env=ctx.env(step),
                       capture_output=True, text=True)
    ready = r.stdout.strip().endswith("Ready.")
    return {"outcome": "Ready." if ready else "Not Ready", "tail": r.stdout[-3000:]}


def code_archive(ctx: Ctx, step) -> dict:
    return {"outcome": "archive left to the paid run (no private archive in %s mode)" % ctx.mode}


STEP_CODE = {"provenance": code_provenance, "premise": code_premise, "discover": code_discover,
             "acquire": code_acquire, "draft": code_draft, "bind": code_bind, "coverage": code_coverage,
             "judgements": code_judgements, "commit": code_commit, "apply": code_apply, "audit": code_audit,
             "overstatement": code_overstatement, "preflight": code_preflight, "archive": code_archive}


def run(ctx: Ctx) -> dict:
    """Every step in order; the repeat group (12-18) re-runs at most MAX_REPEATS times when a step in it changed
    the page. Returns {"result", "steps"}."""
    order = list(ST.STEPS)
    i = 0
    result = "Not Ready"
    try:
        with RunLock(ctx.slug, ctx.mode, path=Path(os.environ.get("WHU_ORCH_LOCK") or
                                                     ctx.root / "backend/data/whatholdsup/orchestrator.lock")) as lk:
            ctx.lock = lk
            changed_in_group = False
            while i < len(order):
                step = order[i]
                r = run_step(ctx, step)
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
    return {"result": result, "steps": ctx.log}


# ---------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("slug"); r.add_argument("--mode", choices=("paid", "trial"),
                                                                       required=True)
    p = sub.add_parser("replay"); p.add_argument("slug", nargs="+"); p.add_argument("--out")
    s = sub.add_parser("status"); s.add_argument("slug")
    e = sub.add_parser("estimate"); e.add_argument("slug", nargs="+"); e.add_argument("--out")
    a = ap.parse_args(argv)
    if os.environ.get("WHU_LEAN") != "1":
        print("refusing: the orchestrator runs lean WHU only (WHU_LEAN=1)")
        return 2
    if a.cmd == "run":
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
        out = run(Ctx(a.slug, "paid"))
        print(json.dumps({"result": out["result"], "steps": [x["step"] for x in out["steps"]]}, indent=1))
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
