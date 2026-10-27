#!/usr/bin/env python3
"""Machine-only spec (a): quote-checked M1 re-judging, WHU's items only.

    quotecheck_m1.py run [--dry-run]     # judge (paid; --dry-run builds and checks only)
    quotecheck_m1.py analyse             # quote check and rates (free)

Spec (machine_only_plan.md, sha256 5c5059f3...), scope narrowed to WHU's M1
items by Fred's budget ruling (Option B, deviations.md 2026-10-24). Items:
every WHU M1 item with a Stage 1 first read from both judges; items the
runner could not deliver whole (INCOMPLETE_SOURCES) stay excluded.

JUDGING is judge_m1.py's, imported, not changed: the same judges and model
ids, the same source delivery (whole up to MAX_SOURCE_TOKENS, else chunk()),
the frozen M1 v3 prompt (sha256 checked), the same refusal rule and the same
OpenAI call. The only change to the text sent is the plan's instruction,
read from machine_only_plan.md and appended after the prompt's last line.
Before any paid call every item's delivery is rebuilt and compared with its
Stage 1 record (sources, extent, tokens, chunking); a difference stops the
run. Items are judged grouped by their cited sources, so the document block
is cached across items; order changes cost, not what any call receives.

CAPS, checked before every call: this run's $40 (ledger issue
whu-reliability-judging-quotecheck), the judging day cap (judge_m1's
day_cap_stop), and the study total check ($375 less WHU's actual ledger
spend over the eight study issues, against all judging ledger issues).

QUOTE CHECK. Each evidence passage is looked for in the FULL held text of the
item's cited sources (not only what was delivered), after normalising
whitespace, quote marks (curly and straight) and dashes (hyphen, en dash, em
dash, minus sign) and nothing else: no case folding, no tag stripping. A
passage with "..." or "…" is checked as written. A Supported label is
demonstrated when at least one passage is found; with none found, or with
evidence missing or not a list of strings, it becomes SUPPORT_NOT_DEMONSTRATED,
an M1 failure. ("Partially supported" in the plan has no M1 v3 label.)

SCORING is analyse.py's (via cross_company.py, with the abstract-only
correction). WHU quote-checked against Claude Research as labelled in Stage 1:
two-judge combined, and cross-company (OpenAI judge for both).

Raw replies and passages: ~/Projects/whu-study-private/scoring/m1_quotecheck/.
Committed result quotecheck_m1.json: counts only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


J = _load("judge_m1", STUDY / "scripts" / "judge_m1.py")
C = _load("cross_company", HERE / "cross_company.py")
A = C.A
S = J.S

PLAN = STUDY / "machine_only_plan.md"
PLAN_SHA256 = "5c5059f332e0637cb139777487c37cd16762db56d6d939b7b921e7fa89c71461"
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "m1"
OUTDIR = Path.home() / "Projects" / "whu-study-private" / "scoring" / "m1_quotecheck"
SCRIPT = "study/whu-reliability/results/machine_only/quotecheck_m1.py"
LEDGER_ISSUE = "whu-reliability-judging-quotecheck"
# --ext (advisor's ruling, 2026-10-27): WHU's WHU-S05 to S08 items, their
# Stage 1 reads in replies_ext/, a new ledger issue with its own $40 run cap
# (the study total check unchanged), re-judge replies in replies_ext/ and the
# counts in quotecheck_m1_ext.json. Without it, the S01-S04 run as committed.
EXT_QUESTIONS = ["WHU-S05", "WHU-S06", "WHU-S07", "WHU-S08"]
STAGE1_TAG = ""
REPLIES = "replies"
RESULT = "quotecheck_m1.json"
RUN_CAP = 40.0
STUDY_TOTAL = 375.0          # raised from $350 by Fred (Option A), 2026-10-27; was $300 to 2026-10-24
# WHU's deduction is its actual ledger spend over the eight study issues (was a
# fixed $46.39, S01-S04 only, deviations.md 2026-10-23); $99.07 on 2026-10-27.
WHU_ISSUES = ("tb-dna-testing", "teen-depression-therapy-format", "public-involvement-climate-policy",
              "city-growth-climate-coping", "undernutrition-tb-risk", "arts-youth-offending",
              "urban-form-transport-emissions", "settlement-planning-climate-resilience")
SYSTEM = "WHU"
SND = "SUPPORT_NOT_DEMONSTRATED"
NEEDS_EVIDENCE = {"Supported"}


def appended_instruction() -> str:
    t = PLAN.read_bytes()
    if hashlib.sha256(t).hexdigest() != PLAN_SHA256:
        raise SystemExit("STOP: machine_only_plan.md is not the frozen plan")
    m = re.search(r"^## \(a\).*?^> (.+?)$", t.decode("utf-8"), re.S | re.M)
    return m.group(1).strip()


# --------------------------------------------------------------------------
# The quote check
# --------------------------------------------------------------------------

QUOTES = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"',
          "„": '"', "‟": '"'}
DASHES = {"‐": "-", "‑": "-", "–": "-", "—": "-", "−": "-"}


def qnorm(s: str) -> str:
    for a, b in {**QUOTES, **DASHES}.items():
        s = s.replace(a, b)
    return " ".join(s.split())


def has_ellipsis(p: str) -> bool:
    return "..." in p or "…" in p


def evidence_of(obj) -> tuple[list[str] | None, str | None]:
    """(passages, problem). None passages: missing or unparseable."""
    if not isinstance(obj, dict) or "evidence" not in obj:
        return None, "missing"
    ev = obj["evidence"]
    if isinstance(ev, str):
        ev = [ev]
    if not isinstance(ev, list) or not ev or not all(isinstance(x, str) and x.strip() for x in ev):
        return None, "unparseable"
    return ev, None


def check_reply(rec: dict, texts: dict) -> dict:
    """The quote check of one reply against the full held texts."""
    held = [qnorm(texts[s["source_id"]]) for s in rec["sources"]]
    held_j = [J.norm(texts[s["source_id"]]) for s in rec["sources"]]
    ev, problem = evidence_of(rec.get("parsed"))
    out = {"passages": [], "evidence_problem": problem}
    for p in ev or []:
        found = any(qnorm(p) in h for h in held)
        out["passages"].append({"text": p, "found": found, "ellipsis": has_ellipsis(p),
                                "words": len(p.split()),
                                # sensitivity only: judge_m1's looser norm (NFKC, case)
                                "found_judge_m1_norm": found or any(J.norm(p) in h for h in held_j)})
    out["demonstrated"] = any(x["found"] for x in out["passages"])
    return out


def checked_label(label, qc: dict):
    if label in NEEDS_EVIDENCE and not qc["demonstrated"]:
        return SND
    return label


# --------------------------------------------------------------------------
# Judging
# --------------------------------------------------------------------------

def stage1(item: str, judge: str) -> dict | None:
    p = RUN / ("replies" + STAGE1_TAG) / judge / (item + ".json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def item_set() -> list[dict]:
    km = json.loads((RUN / "key_map.json").read_text(encoding="utf-8"))
    items = json.loads((RUN / "items.json").read_text(encoding="utf-8"))
    out = []
    for it in items:
        if km[it["item"]]["system"] != SYSTEM or km[it["item"]]["question"] not in A.QUESTIONS:
            continue
        reps = [stage1(it["item"], j) for j in A.JUDGES]
        if all(r and r.get("attempts") for r in reps):
            out.append(it)
    return out


def parse(text: str):
    obj, problems = J.parse(text)
    if obj is not None and set(obj) == {"label", "span", "reason", "evidence"}:
        problems = [p for p in problems if not p.startswith("keys ")]
    return obj, problems


def caps_stop(worst: float) -> str | None:
    why = J.day_cap_stop(worst)
    if why:
        return why
    mine = J.spent(LEDGER_ISSUE)
    if mine + worst > RUN_CAP:
        return "RUN CAP: %s has spent $%.3f of $%.2f; next call up to $%.3f" % (LEDGER_ISSUE, mine, RUN_CAP, worst)
    allj = sum(float(e.get("usd") or 0) for e in S.entries()
               if (e.get("issue") or "").startswith(J.JUDGING_ISSUE_PREFIX))
    whu = whu_spent()
    if allj + worst > STUDY_TOTAL - whu:
        return "STUDY TOTAL: judging has spent $%.3f of $%.2f ($%.0f less WHU's $%.2f); next call up to $%.3f" % (
            allj, STUDY_TOTAL - whu, STUDY_TOTAL, whu, worst)
    return None


def whu_spent() -> float:
    """WHU's actual spend: the ledger summed over the eight study issues."""
    return sum(float(e.get("usd") or 0) for e in S.entries() if e.get("issue") in WHU_ISSUES)


def run(dry: bool) -> int:
    if hashlib.sha256(J.PROMPT.read_bytes()).hexdigest() != J.PROMPT_SHA256:
        print("STOP: the M1 prompt is not the frozen v3")
        return 6
    extra = appended_instruction()
    manifest = {r["url"]: r for r in json.loads((RUN / "sources" / "manifest.json").read_text())}
    tok_file = RUN / "sources" / "tokens.json"
    tokens = json.loads(tok_file.read_text()) if tok_file.exists() else {}
    keys = J.env_keys()
    import anthropic
    raw = anthropic.Anthropic(api_key=keys["ANTHROPIC_API_KEY"])
    client = S.metered(raw, script=SCRIPT, issue=LEDGER_ISSUE, role="m1-quotecheck-claude")
    J.SCRIPT = SCRIPT      # the OpenAI ledger line names this script

    def count(text: str) -> int:
        return raw.messages.count_tokens(model=J.CLAUDE_MODEL, messages=[{"role": "user", "content": text}]).input_tokens

    # Build every item's documents first, as judge_m1 does, and compare with Stage 1.
    built = []
    for it in item_set():
        cites = it.get("citations") or [{"label": "", "url": u} for u in it["urls"]]
        spans = [s for s in [it.get("span")] + list(it.get("spans") or []) if s]
        docs = []
        for u in [c["url"] for c in cites if c.get("url")]:
            m = manifest[u]
            text = (RUN / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8")
            if m["source_id"] not in tokens:
                tokens[m["source_id"]] = count(text)
            d = {"source_id": m["source_id"], "url": u, "extent": m["extent"],
                 "abstract_only": bool(m.get("abstract_only")), "tokens": tokens[m["source_id"]],
                 "text_sha256": m["text_sha256"], "chunked": False, "text": text}
            if d["tokens"] > J.MAX_SOURCE_TOKENS:
                d["text"], d["chunk"] = J.chunk(text, it["claim"], J.MAX_SOURCE_TOKENS, count, spans)
                d["chunked"] = True
            if J.delivery_problems(text, d["text"], it["claim"], spans):
                print("STOP: %s would not be delivered whole now, though Stage 1 judged it" % it["item"])
                return 5
            docs.append(d)
        meta = [{k: v for k, v in d.items() if k != "text"} for d in docs]
        for j in A.JUDGES:
            if meta != stage1(it["item"], j)["sources"]:
                print("STOP: %s's delivery differs from its Stage 1 %s record" % (it["item"], j))
                return 5
        prefix, rest = J.build(it, docs)
        rest = rest.rstrip("\n") + "\n\n" + extra + "\n"
        built.append((it, docs, prefix, rest))
    built.sort(key=lambda b: (tuple(d["source_id"] for d in b[1]), b[0]["item"]))
    print("items %d (delivery identical to Stage 1); appended: %r" % (len(built), extra))
    if dry:
        return 0

    prompt_sha = hashlib.sha256(J.PROMPT.read_bytes()).hexdigest()
    for it, docs, prefix, rest in built:
        n_in = count(prefix + rest)
        for judge in A.JUDGES:
            out = OUTDIR / REPLIES / judge / (it["item"] + ".json")
            if out.exists():
                continue
            attempts = []
            for attempt in (1, 2):              # the second only after a refusal
                if judge == "claude":
                    p = S.PRICES[J.CLAUDE_MODEL]
                    worst = (n_in * p["cache_write"] + J.CLAUDE_MAX_OUT * p["output"]) / 1e6
                else:
                    worst = (n_in * J.OPENAI_PRICE["input"] + J.OPENAI_MAX_OUT * J.OPENAI_PRICE["output"]) / 1e6
                why = caps_stop(worst)
                if why:
                    print("STOP: " + why)
                    return 3
                t0 = time.time()
                for net in range(3):
                    try:
                        if judge == "claude":
                            text, usage, usd, refused = J.call_claude(client, prefix, rest, J.CLAUDE_MODEL)
                        else:
                            text, usage, usd, refused = J.call_openai(keys["OPENAI_API_KEY"], prefix, rest, LEDGER_ISSUE)
                        break
                    except J.OutOfCredit as e:
                        print("STOP: OUT OF CREDIT at %s (%s)" % (it["item"], e))
                        return 7
                    except Exception as e:
                        if net == 2:
                            raise
                        print("  network retry %s %s: %s" % (judge, it["item"], str(e)[:160]))
                        time.sleep(10)
                attempts.append({"attempt": attempt, "seconds": round(time.time() - t0, 1),
                                 "usage": usage, "usd": round(usd, 6), "refused": refused, "raw": text})
                if not refused:
                    break
            last = attempts[-1]
            obj, problems = (None, []) if last["refused"] else parse(last["raw"])
            rec = {"item": it["item"], "judge": judge, "model": last["usage"].get("model"),
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "prompt_sha256": prompt_sha, "prompt_version": J.PROMPT_VERSION + "+spec(a)",
                   "appended": extra, "plan_sha256": PLAN_SHA256,
                   "sources": [{k: v for k, v in d.items() if k != "text"} for d in docs],
                   "chunked": any(d["chunked"] for d in docs), "input_tokens_counted": n_in,
                   "attempts": attempts, "usd": round(sum(x["usd"] for x in attempts), 6),
                   "judge_label": (obj or {}).get("label"),
                   "label": J.final_label((obj or {}).get("label"), last["refused"], docs),
                   "parsed": obj, "form_problems": problems, "reference": it["reference"]}
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
            print("%-14s %-7s %-12s $%.4f%s" % (it["item"], judge, rec["label"], rec["usd"],
                                                 ("  FORM: " + "; ".join(problems)) if problems else ""))
    print("%s spent: $%.4f" % (LEDGER_ISSUE, J.spent(LEDGER_ISSUE)))
    return 0


# --------------------------------------------------------------------------
# Analysis (free)
# --------------------------------------------------------------------------

def analyse() -> int:
    items = {it["item"] for it in item_set()}
    replies = {}
    for j in A.JUDGES:
        for f in sorted((OUTDIR / REPLIES / j).glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            replies.setdefault(r["item"], {})[j] = r
    missing = sorted(i for i in items if set(replies.get(i, {})) != set(A.JUDGES))
    if missing:
        print("STOP: %d items lack a re-judge reply from both judges" % len(missing))
        return 2
    texts = {}
    for i in items:
        for r in replies[i].values():
            for s in r["sources"]:
                texts.setdefault(s["source_id"], (RUN / "sources" / (s["source_id"] + ".txt")).read_text(encoding="utf-8"))

    labels = {j: {} for j in A.JUDGES}
    checked = {j: {} for j in A.JUDGES}
    pas = {"checked": 0, "found": 0, "not_found": 0, "not_found_with_ellipsis": 0,
           "found_with_ellipsis": 0, "not_found_but_found_under_judge_m1_norm": 0,
           "over_60_words": 0, "replies_over_3_passages": 0}
    ev_problems = {}
    differ = {j: 0 for j in A.JUDGES}
    downgraded = {j: 0 for j in A.JUDGES}
    downgraded_why = {"no passage found": 0, "evidence missing": 0, "evidence unparseable": 0}
    private = {}
    for i in sorted(items):
        for j in A.JUDGES:
            r = replies[i][j]
            qc = check_reply(r, texts)
            private.setdefault(i, {})[j] = qc
            lab = r["label"]
            labels[j][lab] = labels[j].get(lab, 0) + 1
            if lab != stage1(i, j)["label"]:
                differ[j] += 1
            if lab in NEEDS_EVIDENCE:
                ps = qc["passages"]
                pas["checked"] += len(ps)
                pas["found"] += sum(p["found"] for p in ps)
                pas["not_found"] += sum(not p["found"] for p in ps)
                pas["not_found_with_ellipsis"] += sum(not p["found"] and p["ellipsis"] for p in ps)
                pas["found_with_ellipsis"] += sum(p["found"] and p["ellipsis"] for p in ps)
                pas["not_found_but_found_under_judge_m1_norm"] += sum(not p["found"] and p["found_judge_m1_norm"] for p in ps)
                pas["over_60_words"] += sum(p["words"] > 60 for p in ps)
                pas["replies_over_3_passages"] += len(ps) > 3
                if qc["evidence_problem"]:
                    ev_problems[qc["evidence_problem"]] = ev_problems.get(qc["evidence_problem"], 0) + 1
            new = checked_label(lab, qc)
            if new == SND:
                downgraded[j] += 1
                downgraded_why["evidence " + qc["evidence_problem"] if qc["evidence_problem"] else "no passage found"] += 1
            checked[j][i] = new
    (OUTDIR / ("quote_checks%s.json" % STAGE1_TAG)).write_text(json.dumps(private, indent=1, ensure_ascii=False), encoding="utf-8")

    def scored(mode: str) -> dict:
        """mode: stage1 | labelled (re-judge as labelled) | checked (quote-checked)."""
        rows = A.items_m1()
        C.abstract_correct(rows)
        valid = A.M1_PASS | A.M1_FAIL | A.M1_EXCL | {SND}
        for r in rows:
            if mode == "stage1" or r["item"] not in items:
                continue
            raw = {}
            for j in A.JUDGES:
                rep = replies[r["item"]][j]
                raw[j] = {**rep, "label": checked[j][r["item"]] if mode == "checked" else rep["label"]}
            r["raw"], r["repeat"] = raw, {}
            C.abstract_correct([r])
            r["labels"] = A.per_judge_labels(r["raw"], valid)
        fb = C.fallbacks([r for r in rows if r["system"] in ("WHU", "Claude")], valid)
        v = A.view_scores(rows, A.M1_FAIL | {SND}, A.M1_PASS)
        out = {"refusal_fallbacks_WHU_or_Claude": fb}
        for name, sc in (("two_judge_combined", v["combined"]),
                         ("cross_company_openai_judge", [x for x in v["openai_judge"] if x[1] in ("WHU", "Claude")])):
            av = A.analyse_view(sc)
            out[name] = {"WHU": {k: av["systems"]["WHU"][k] for k in ("failures", "countable", "rate", "ci95")},
                         "Claude": {k: av["systems"]["Claude"][k] for k in ("failures", "countable", "rate", "ci95")},
                         "H1_WHU_vs_Claude": av["vs_whu"]["Claude"]}
        return out

    res = {"label": "Machine-only spec (a), quote-checked M1 re-judge, WHU only (Option B): AI judges only",
           "scope": "WHU M1 items with a Stage 1 first read from both judges; Claude Research as labelled in Stage 1",
           "items": len(items), "appended_instruction_sha256": hashlib.sha256(appended_instruction().encode()).hexdigest(),
           "seed": str(A.SEED), "bootstrap_resamples": A.B,
           "label_counts_rejudge": labels,
           "labels_differing_from_stage1": differ,
           "passages_on_supported_labels": pas,
           "evidence_problems_on_supported_labels": ev_problems,
           "downgraded_to_support_not_demonstrated": {"by_judge": downgraded, "by_reason": downgraded_why},
           "rates": {m: scored(m) for m in ("stage1", "labelled", "checked")},
           "spend": {"ledger_issue": LEDGER_ISSUE, "usd": round(J.spent(LEDGER_ISSUE), 4),
                     "calls": sum(1 for e in S.entries() if e.get("issue") == LEDGER_ISSUE)}}
    (HERE / RESULT).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("label_counts_rejudge", "labels_differing_from_stage1",
                                          "passages_on_supported_labels", "downgraded_to_support_not_demonstrated",
                                          "spend")}, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyse"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ext", action="store_true", help="WHU-S05 to S08 (advisor's ruling, 2026-10-27)")
    a = ap.parse_args()
    if a.ext:
        global LEDGER_ISSUE, STAGE1_TAG, REPLIES, RESULT
        LEDGER_ISSUE, STAGE1_TAG = "whu-reliability-judging-quotecheck-ext", "_ext"
        REPLIES, RESULT = "replies_ext", "quotecheck_m1_ext.json"
        A.QUESTIONS, A.HEALTH, A.TAGS = list(EXT_QUESTIONS), {"WHU-S05"}, ("_ext",)
    return run(a.dry_run) if a.cmd == "run" else analyse()


if __name__ == "__main__":
    raise SystemExit(main())
