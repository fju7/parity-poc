#!/usr/bin/env python3
"""Prepare the study's scoring: verify, blind, sample, snapshot, project cost.
No model is called and nothing is judged.

    prepare_scoring.py verify   --questions WHU-S01,WHU-S02,WHU-S03
    prepare_scoring.py blind    --questions ...
    prepare_scoring.py sample   --questions ...
    prepare_scoring.py snapshot                      (free HTTP GETs only)
    prepare_scoring.py cost

Protocol (frozen at 5d83e9b): Measures M1 and M2, Blinding, AI judges,
Analysis plan; budget ruling (rev 26).

WHERE THINGS GO. Everything that holds answer, key or source text is written
under ~/Projects/whu-study-private/scoring/ (PRIVATE) and never to the
repository. The repository gets this code and, under study/whu-reliability/
scoring/, manifests of sha256 values, the sampling log (seed, rule, and every
drawn sentence id with its sha256) and the cost projection's arithmetic.

VERIFY. Every tool answer against answers_manifest.txt, every key file against
keys_manifest.txt, and every key source against its question's sources.sha256.
Any mismatch stops with exit 2 and nothing else runs. WHU's answer is the
issue's page as committed; its sha256 and commit are written to
scoring/whu_answers_manifest.txt, and a page that differs from its last commit
stops the run.

BLIND. WHU: export_whu.py (markers from bindings) then blind.py's rules, as in
prep. Tools: adapt.py takes the report out of the capture file and makes each
citation marker a link, then blind.py. Gemini WHU-S03/S04 from
gemini.raw.html, the recorded copy (deviations.md, 2026-10-22). Process
sentences are marked not samplable by blind.py, for every system.

SAMPLE (M1). Per answer, the pool is its samplable claim-like sentences
(identifiability.claim_like: a number or a citation marker, 8 to 70 words,
"what M1 samples"). M1_PER_ANSWER of them, or all if fewer, are drawn with
random.Random("<SEED>/<question>/<system>/M1").sample(pool sorted by index, k),
where SEED is the freeze commit's 40-character hash read as a hexadecimal
integer (protocol, "The seed rule"). One generator per answer, so the draw for
an answer does not depend on which other answers exist (WHU-S04 is added
later without changing the others). A drawn sentence with no citation marker
is UNCITED: a failure, reported separately, and not sent to a judge. Item ids
are opaque; the map from item to system is PRIVATE. The judging order is
shuffled with random.Random("<SEED>/order/M1").

SAMPLE (M2). Every conclusion of the question's frozen key, for every answer:
nothing is drawn (protocol M2). A key conclusion's quotations are passed as one
"quote" field, each with its location.

SNAPSHOT. snapshot.py, unchanged, on every distinct address the drawn items
cite (the "#:~:text" fragment dropped: it is not sent to a server). What it
cannot reach is listed for the advisor in PRIVATE/m1/operator_fetch.json.
An item is INCOMPLETE_SOURCES while any cited source is unreachable.

COST. From the held snapshots' sizes (characters, at the Anthropic
characters-per-token ratio measured on prep round 2's snapshots) and the output
tokens measured in prep (M1 v3, runs/prep2) and the M2 v2 behaviour check
(runs/prefreeze/m2/replies_v2), at the prices in spend_ledger.PRICES and
judge_m1.OPENAI_PRICE. Writes scoring/cost_projection.json with every term.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import statistics as st
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
PRIVATE = Path.home() / "Projects" / "whu-study-private"
SCORING = PRIVATE / "scoring"
LOG = STUDY / "scoring"
sys.path.insert(0, str(STUDY / "blinding"))
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FREEZE = "5d83e9b8025312923f3fb8ea2d5de3b47c212362"
SEED = int(FREEZE, 16)
QUESTIONS = {"WHU-S01": "tb-dna-testing", "WHU-S02": "teen-depression-therapy-format",
             "WHU-S03": "public-involvement-climate-policy", "WHU-S04": "city-growth-climate-coping",
             # The extension (protocol, extension rule; draws f440d56, S05 re-drawn 2ef75c7).
             "WHU-S05": "undernutrition-tb-risk", "WHU-S06": "arts-youth-offending",
             "WHU-S07": "urban-form-transport-emissions", "WHU-S08": "settlement-planning-climate-resilience"}
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini"]
TOOL_FILE = {"Claude": "claude", "ChatGPT": "chatgpt", "Gemini": "gemini"}
# Claude's captures saved with the report panel's "Download as Markdown"
# (escaped [n] markers and the report's own numbered Sources list), not page data.
CLAUDE_SOURCES_LIST = ("WHU-S05", "WHU-S06", "WHU-S07", "WHU-S08")
M1_PER_ANSWER = 20
REPEAT_SHARE = 0.20
UNCITED = "UNCITED"
MARK = re.compile(r"\[(\d+)\]")


def sha(b) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(p: Path, obj) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, indent=1, ensure_ascii=False)
    p.write_text(data, encoding="utf-8")
    return sha(data)


def qs(a) -> list[str]:
    out = [q.strip() for q in a.questions.split(",") if q.strip()]
    bad = [q for q in out if q not in QUESTIONS]
    if bad:
        raise SystemExit("unknown question(s): %s" % ", ".join(bad))
    return out


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------

def check_manifest(manifest: Path, base: Path) -> tuple[int, list[str]]:
    ok, bad = 0, []
    for line in manifest.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        want, rel = line.split(None, 1)
        p = base / rel.strip()
        got = sha(p.read_bytes()) if p.exists() else "(missing)"
        if got == want:
            ok += 1
        else:
            bad.append("%s: %s, manifest %s" % (rel.strip(), got[:12], want[:12]))
    return ok, bad


def whu_page(slug: str) -> Path:
    import publish as P
    return P.ROOT / P.issue_cfg(slug)["page"]


def verify(a) -> int:
    questions = qs(a)
    rows, bad = [], []
    n, b = check_manifest(STUDY / "answers_manifest.txt", PRIVATE / "answers")
    rows.append(("tool answers (answers_manifest.txt)", n)); bad += b
    n, b = check_manifest(STUDY / "keys_manifest.txt", PRIVATE / "keys")
    rows.append(("key files (keys_manifest.txt)", n)); bad += b
    for q in QUESTIONS:
        n, b = check_manifest(PRIVATE / "keys" / q / "sources.sha256", PRIVATE / "keys" / q)
        rows.append(("%s key sources (sources.sha256)" % q, n)); bad += b
    whu = []
    for q in questions:
        page = whu_page(QUESTIONS[q])
        rel = str(page.relative_to(ROOT))
        commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT).returncode != 0
        if dirty or not commit:
            bad.append("%s: WHU page %s %s" % (q, rel, "differs from its last commit" if dirty else "is not committed"))
        issue_dir = str(page.parent.parent.relative_to(ROOT))
        at = subprocess.run(["git", "log", "-1", "--format=%H", "--", issue_dir], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
        whu.append("%s  %s  %s  (commit %s; issue at %s)" % (sha(page.read_bytes()), q, rel, commit, at))
    for label, n in rows:
        print("  %-45s %3d ok" % (label, n))
    if bad:
        print("\n  STOP: %d mismatch(es)" % len(bad))
        for x in bad:
            print("    " + x)
        return 2
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "whu_answers_manifest.txt").write_text(
        "# WHU reliability study: WHU's answers, sha256 manifest (written by prepare_scoring.py verify)\n"
        "# WHU's answer is the issue page as committed, once the run is at \"ready for operator acceptance\".\n"
        "#\n# sha256  question  page  (last commit touching the page; last commit touching the issue)\n"
        + "\n".join(whu) + "\n")
    print("  %-45s %3d written to scoring/whu_answers_manifest.txt" % ("WHU pages", len(whu)))
    return 0


# --------------------------------------------------------------------------
# blind
# --------------------------------------------------------------------------

def tool_answer(q: str, system: str) -> tuple[str, list[str] | None, str]:
    """(markdown blind.py reads, Gemini Works cited URLs or None, record file)."""
    import adapt
    d = PRIVATE / "answers" / q
    f = TOOL_FILE[system]
    if system == "Gemini" and q in ("WHU-S03", "WHU-S04"):
        rec = d / "gemini.raw.html"
        return adapt.gemini_html(rec.read_text(encoding="utf-8")), None, rec.name
    rec = d / (f + ".md")
    md = rec.read_text(encoding="utf-8")
    if system == "ChatGPT":
        body = adapt.chatgpt_lenticular(md) if q in ("WHU-S01", "WHU-S02") else adapt.chatgpt_bracketed(md)
        return body, None, rec.name
    if system == "Gemini":
        return adapt.report_section(md), adapt.works_cited(md), rec.name
    if q in CLAUDE_SOURCES_LIST:
        body, cited = adapt.claude_sources(md)
        return body, cited, rec.name
    return adapt.report_section(md), None, rec.name


def blind_one(q: str, system: str) -> dict:
    import blind
    out = SCORING / "blinded" / q
    out.mkdir(parents=True, exist_ok=True)
    if system == "WHU":
        import export_whu
        slug = QUESTIONS[q]
        text, srows = export_whu.export(slug)
        src = out / (slug + ".export.txt")
        src.write_text(text, encoding="utf-8")
        with open(out / (slug + ".sentences.jsonl"), "w", encoding="utf-8") as fh:
            for r in srows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        refs = []
        for line in text.split("\n\nReferences\n", 1)[1].splitlines():
            u = line.split()[-1] if line.split() else ""
            refs.append(u if u.startswith("http") else None)
        record, blinded, _f = (whu_page(slug).name, *blind.blind(src))
        rows = blind.sentence_rows(src, "WHU")
    else:
        md, cited, record = tool_answer(q, system)
        src = out / ("%s.adapted.md" % system.lower())
        src.write_text(md, encoding="utf-8")
        body, refs = blind.from_markdown(md)          # refs: the URLs as numbered, before any rule
        blinded, _f = blind.blind(src)
        if cited is not None:
            if refs:
                raise SystemExit("%s %s: links in the body as well as its own reference list" % (q, system))
            refs = list(cited)
            refs_t, _ = blind.apply_rules(blind._typography("\n".join(refs)))
            blinded += "\n\nReferences\n" + "\n".join("[%d] %s" % (i + 1, r) for i, r in enumerate(refs_t.splitlines()))
        rows = blind.sentence_rows(src, system)
    (out / ("%s.blind.txt" % system.lower())).write_text(blinded, encoding="utf-8")
    with open(out / ("%s.sentences.jsonl" % system.lower()), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_json(out / ("%s.refs.json" % system.lower()), refs)
    marked = [r for r in rows if MARK.search(r["text"])]
    beyond = sum(1 for r in marked for n in MARK.findall(r["text"]) if not 1 <= int(n) <= len(refs))
    return {"question": q, "system": system, "record": record,
            "blinded_sha256": sha(blinded), "blinded_chars": len(blinded),
            "sentences": len(rows), "samplable": sum(r["samplable"] for r in rows),
            "with_marker": len(marked), "references": len(refs), "markers_outside_reference_list": beyond}


def do_blind(a) -> int:
    rows = [blind_one(q, s) for q in qs(a) for s in SYSTEMS]
    lines = ["# WHU reliability study: blinded answers, sha256 manifest (prepare_scoring.py blind)",
             "# The blinded texts are held at ~/Projects/whu-study-private/scoring/blinded/<question>/<system>.blind.txt.",
             "#", "# sha256  question  system  record  chars  sentences  samplable  with-marker  references"]
    for r in rows:
        lines.append("%s  %s  %-7s  %-18s %6d  %4d  %4d  %4d  %3d" % (
            r["blinded_sha256"], r["question"], r["system"], r["record"], r["blinded_chars"], r["sentences"],
            r["samplable"], r["with_marker"], r["references"]))
        print("  %s %-7s %6d chars  %4d sentences  %4d samplable  %4d with marker  %3d refs%s" % (
            r["question"], r["system"], r["blinded_chars"], r["sentences"], r["samplable"], r["with_marker"],
            r["references"], ("  (%d marker(s) beyond the reference list)" % r["markers_outside_reference_list"])
            if r["markers_outside_reference_list"] else ""))
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "blinded_manifest.txt").write_text("\n".join(lines) + "\n")
    return 0


# --------------------------------------------------------------------------
# sample
# --------------------------------------------------------------------------

def opaque(prefix: str, key: str) -> str:
    return "%s-%s" % (prefix, sha("%d/%s" % (SEED, key))[:10])


def key_conclusions(q: str) -> list[dict]:
    k = json.loads((PRIVATE / "keys" / q / "key.json").read_text(encoding="utf-8"))
    out = []
    for c in k["conclusions"]:
        quote = "; ".join('"%s" (%s)' % (x["text"], x["location"]) for x in c.get("quotes") or [])
        out.append({"id": "%s-C%d" % (q, c["n"]), "statement": c["statement"], "direction": c["direction"],
                    "size": c["size"], "certainty": c["certainty"], "scope": c["scope"], "quote": quote,
                    "fields_not_passed": sorted(set(c) - {"n", "statement", "direction", "size", "certainty",
                                                          "scope", "quotes", "role"})})
    return out


def do_sample(a) -> int:
    ident = _load("identifiability_ps", STUDY / "blinding" / "identifiability.py")
    import adapt
    m1, uncited, keymap, log_answers = [], [], {}, []
    for q in qs(a):
        for s in SYSTEMS:
            d = SCORING / "blinded" / q
            rows = [json.loads(l) for l in (d / ("%s.sentences.jsonl" % s.lower())).read_text(encoding="utf-8").splitlines()]
            refs = json.loads((d / ("%s.refs.json" % s.lower())).read_text(encoding="utf-8"))
            pool = sorted((r for r in rows if ident.claim_like(r)), key=lambda r: r["idx"])
            k = min(M1_PER_ANSWER, len(pool))
            rule = "%d/%s/%s/M1" % (SEED, q, s)
            drawn = sorted(random.Random(rule).sample(pool, k), key=lambda r: r["idx"])
            entry = {"question": q, "system": s, "sentences": len(rows),
                     "samplable": sum(r["samplable"] for r in rows), "claim_like_pool": len(pool),
                     "k": k, "rng_seed_string": "<SEED>/%s/%s/M1" % (q, s), "drawn": []}
            for r in drawn:
                sid = "%s/%s/%d" % (q, s, r["idx"])
                nums = [int(n) for n in MARK.findall(r["text"])]
                cites, seen = [], set()
                for n in nums:
                    u = refs[n - 1] if 1 <= n <= len(refs) else None
                    u = adapt.fragment_free(u) if u else None
                    if (n, u) in seen:
                        continue
                    seen.add((n, u))
                    cites.append({"label": "[%d]" % n, "url": u} if u else
                                 {"label": "[%d]" % n, "url": None, "note": "marker outside the reference list"})
                item = opaque("M1", sid)
                keymap[item] = {"sentence": sid, "question": q, "system": s}
                rec = {"item": item, "claim": r["text"], "context": r["context"], "citations": cites,
                       "reference": ""}
                (m1 if cites else uncited).append(rec)
                entry["drawn"].append({"sentence": sid, "idx": r["idx"], "sha256": sha(r["text"]),
                                       "item": item, "markers": len(nums), "label": None if cites else UNCITED})
            log_answers.append(entry)
            print("  %s %-7s pool %3d of %3d samplable; drew %2d (%d uncited)"
                  % (q, s, len(pool), entry["samplable"], k, sum(1 for x in entry["drawn"] if x["label"])))
    random.Random("%d/order/M1" % SEED).shuffle(m1)
    h_items = write_json(SCORING / "m1" / "items.json", m1)
    h_unc = write_json(SCORING / "m1" / "uncited.json", uncited)
    h_map = write_json(SCORING / "m1" / "key_map.json", keymap)
    # M2: every key conclusion, for every answer.
    answers, conclusions, items, m2map = {}, [], [], {}
    for q in qs(a):
        cs = key_conclusions(q)
        conclusions += [{k: v for k, v in c.items() if k != "fields_not_passed"} for c in cs]
        for s in SYSTEMS:
            aid = opaque("A", "%s/%s" % (q, s))
            f = SCORING / "m2" / "answers" / (aid + ".txt")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text((SCORING / "blinded" / q / ("%s.blind.txt" % s.lower())).read_text(encoding="utf-8"),
                         encoding="utf-8")
            answers[aid] = {"file": "answers/%s.txt" % aid}
            m2map[aid] = {"question": q, "system": s}
            for c in cs:
                items.append({"item": opaque("M2", "%s/%s" % (aid, c["id"])), "answer": aid, "conclusion": c["id"]})
    # One answer's conclusions stay together (its block is cached); answers are shuffled.
    order = sorted(answers)
    random.Random("%d/order/M2" % SEED).shuffle(order)
    items.sort(key=lambda it: (order.index(it["answer"]), it["conclusion"]))
    h_m2 = write_json(SCORING / "m2" / "items.json", {"answers": answers, "conclusions": conclusions, "items": items})
    h_m2map = write_json(SCORING / "m2" / "key_map.json", m2map)
    not_passed = sorted({f for q in qs(a) for c in key_conclusions(q) for f in c["fields_not_passed"]})
    log = {"written": now(), "by": "prepare_scoring.py sample", "freeze_commit": FREEZE,
           "seed": str(SEED), "seed_rule": "the freeze commit's 40-character hash read as a hexadecimal integer",
           "m1": {"per_answer": M1_PER_ANSWER, "pool": "identifiability.claim_like (samplable; a number or a "
                  "citation marker; 8 to 70 words)", "generator": "random.Random('<SEED>/<question>/<system>/M1')"
                  ".sample(pool sorted by sentence index, k)", "order": "random.Random('<SEED>/order/M1').shuffle",
                  "answers": log_answers},
           "m2": {"rule": "every conclusion of the frozen key, for every answer; nothing drawn",
                  "conclusions_per_question": {q: len(key_conclusions(q)) for q in qs(a)},
                  "items": len(items), "answer_order": "random.Random('<SEED>/order/M2').shuffle",
                  "key_fields_not_passed_to_the_judge": not_passed},
           "private_files_sha256": {"m1/items.json": h_items, "m1/uncited.json": h_unc, "m1/key_map.json": h_map,
                                    "m2/items.json": h_m2, "m2/key_map.json": h_m2map}}
    write_json(LOG / "sampling_log.json", log)
    print("  M1: %d items to judge, %d uncited; M2: %d items (%s conclusions)"
          % (len(m1), len(uncited), len(items), "+".join(str(len(key_conclusions(q))) for q in qs(a))))
    return 0


# --------------------------------------------------------------------------
# snapshot
# --------------------------------------------------------------------------

def licence_barred() -> set[str]:
    out = set()
    for q, slug in QUESTIONS.items():
        p = next((d for d in (ROOT / "issues").iterdir() if d.name.endswith("-" + slug)), None)
        if not p or not (p / "sources.json").exists():
            continue
        for s in json.loads((p / "sources.json").read_text())["sources"]:
            if s.get("licence_forbids_machine_reading") or (s.get("access") or {}).get("licence_forbids_machine_reading"):
                if s.get("url"):
                    out.add(s["url"].split("#", 1)[0])
    return out


def citation_text() -> dict[str, str]:
    """A citation for each address, where an answer gives one: WHU's sources.json title."""
    out = {}
    for slug in QUESTIONS.values():
        p = next((d for d in (ROOT / "issues").iterdir() if d.name.endswith("-" + slug)), None)
        if p and (p / "sources.json").exists():
            for s in json.loads((p / "sources.json").read_text())["sources"]:
                if s.get("url"):
                    out.setdefault(s["url"].split("#", 1)[0], s.get("title") or "")
    return out


def do_snapshot(a) -> int:
    run = SCORING / "m1"
    items = json.loads((run / "items.json").read_text(encoding="utf-8"))
    urls = []
    for it in items:
        for c in it["citations"]:
            if c.get("url") and c["url"] not in urls:
                urls.append(c["url"])
    barred = licence_barred() & set(urls)
    if barred:
        print("  STOP: %d cited address(es) carry licence_forbids_machine_reading; not fetched" % len(barred))
        return 2
    have = set()
    mf = run / "sources" / "manifest.json"
    if mf.exists():
        # Every address with a row, held or not: one still unreachable has been
        # through retrieve_sources.py's routes, and its record is kept, not
        # replaced by a fresh first fetch (round 3, WHU-S04).
        have = {r["url"] for r in json.loads(mf.read_text())}
    todo = [{"item": "U%03d" % i, "urls": [u]} for i, u in enumerate(urls) if u not in have]
    if todo:
        write_json(run / "fetch_list.json", todo)
        old = json.loads(mf.read_text()) if mf.exists() else []
        subprocess.run([sys.executable, str(HERE / "snapshot.py"), str(run / "fetch_list.json"), str(run)], check=True)
        new = json.loads(mf.read_text())
        by = {r["url"]: r for r in old}
        by.update({r["url"]: r for r in new})
        write_json(mf, [by[u] for u in urls if u in by])
    return snapshot_report()


# The last answer of an automated fetch that a person's browser may well get
# past: a refusal, a challenge page or an empty script shell.
BLOCKED = ("HTTP 401", "HTTP 403", "HTTP 405", "HTTP 429", "HTTP 503", "bot wall", "readable characters",
           "access-denied")


def still_unreachable(m: dict) -> dict:
    """A row for operator_fetch.json: what was tried, and the two marks."""
    import snapshot as SN
    r = m.get("retrieval") or {}
    tried = [t for x in (r.get("earlier_passes") or []) + [r] for t in (x.get("tried") or [])]
    advisor = [t for t in tried if t.get("route") == "d" and t.get("by")]   # not the "not tried" marks
    last = [t for t in tried if t.get("route") in ("a", "b")] or [{"result": m.get("extent_why") or ""}]
    texts = [" ".join(str(t.get(k) or "") for k in ("result", "why")) for t in last]
    blocks = any(any(b in t for b in BLOCKED) for t in texts)
    ev = r.get("oa_evidence") or {}
    article = any(h in m["url"] for h in SN.ARTICLE_HOSTS) or bool((ev.get("ids") or {}))
    free = ("yes: an open-access record (Unpaywall is_oa or Europe PMC free full text)"
            if ev.get("is_oa") or ev.get("epmc_free") else
            "likely: not an article record (an organisation, government or news page)" if not article else "unknown")
    return {"source_id": m["source_id"], "url": m["url"], "why": m.get("extent_why"),
            "tried": [{k: t.get(k) for k in ("route", "url", "result", "version") if t.get(k) is not None} for t in tried],
            "blocks_automation": blocks, "free_to_read": free,
            "free_to_read_but_blocks_automation": blocks and not free.startswith("unknown"),
            "advisor_tried": advisor[-1].get("result") if advisor else None}


def how_held(m: dict | None) -> str:
    """"script" (the uniform scripted route: first fetch, a, b or c), "operator"
    (route d, the advisor's browser) or "unreachable"."""
    if not m or m["extent"] == "unreachable":
        return "unreachable"
    return "operator" if (m.get("retrieval") or {}).get("route") == "d" else "script"


def reachability(items: list[dict], keymap: dict, man: dict) -> dict:
    """Citation reachability per system (round 3): of the drawn cited items, how
    many have every cited source held by script, how many need a source the
    advisor fetched, and how many are still incomplete; and the same for the
    distinct sources each system's drawn items cite. A system whose unreachable
    share of cited items is above 20% is flagged (protocol M1, Unreachable)."""
    per = {}
    for it in items:
        s = keymap[it["item"]]["system"]
        p = per.setdefault(s, {"cited_items": 0, "items_all_sources_by_script": 0, "items_needing_operator_fetch": 0,
                               "items_unreachable": 0, "_src": {}})
        hs = [how_held(man.get(c["url"])) if c.get("url") else "unreachable" for c in it["citations"]]
        for c, h in zip(it["citations"], hs):
            if c.get("url"):
                p["_src"][c["url"]] = h
        p["cited_items"] += 1
        if "unreachable" in hs:
            p["items_unreachable"] += 1
        elif "operator" in hs:
            p["items_needing_operator_fetch"] += 1
        else:
            p["items_all_sources_by_script"] += 1
    out = {}
    for s in SYSTEMS:
        p = per.get(s)
        if not p:
            continue
        src = p.pop("_src")
        n = p["cited_items"]
        p.update({"share_reachable_by_script": round(p["items_all_sources_by_script"] / n, 4),
                  "share_reachable_after_operator_fetch": round((n - p["items_unreachable"]) / n, 4),
                  "share_unreachable": round(p["items_unreachable"] / n, 4),
                  "flag_unreachable_over_20pct": p["items_unreachable"] / n > 0.20,
                  "sources": {"distinct": len(src), "by_script": sum(v == "script" for v in src.values()),
                              "by_operator_fetch": sum(v == "operator" for v in src.values()),
                              "unreachable": sum(v == "unreachable" for v in src.values())}})
        out[s] = p
    return out


def snapshot_report() -> int:
    run = SCORING / "m1"
    items = json.loads((run / "items.json").read_text(encoding="utf-8"))
    keymap = json.loads((run / "key_map.json").read_text(encoding="utf-8"))
    man = {r["url"]: r for r in json.loads((run / "sources" / "manifest.json").read_text())}
    cites = citation_text()
    need, per = {}, {}
    for it in items:
        km = keymap[it["item"]]
        p = per.setdefault((km["question"], km["system"]), {"items": 0, "held": 0, "incomplete": 0,
                                                            "abstract_only": 0, "no_url": 0})
        p["items"] += 1
        ext = []
        for c in it["citations"]:
            if not c.get("url"):
                ext.append("none")
                continue
            m = man[c["url"]]
            ext.append(m["extent"])
            if m["extent"] == "unreachable":
                n = need.setdefault(c["url"], dict(still_unreachable(m), citation=cites.get(c["url"], ""), items=[]))
                n["items"].append(it["item"])
                p.setdefault("_unreachable", set()).add(c["url"])
        if "none" in ext:
            p["no_url"] += 1; p["incomplete"] += 1
        elif "unreachable" in ext:
            p["incomplete"] += 1
        else:
            p["held"] += 1
            p["abstract_only"] += any(e == "abstract only" for e in ext)
    write_json(run / "operator_fetch.json", sorted(need.values(), key=lambda r: r["source_id"]))
    reach = reachability(items, keymap, man)
    unc = json.loads((run / "uncited.json").read_text(encoding="utf-8"))
    for it in unc:
        km = keymap[it["item"]]
        per.setdefault((km["question"], km["system"]), {"items": 0, "held": 0, "incomplete": 0,
                                                        "abstract_only": 0, "no_url": 0})
    rows = []
    for (q, s), p in sorted(per.items()):
        p["uncited"] = sum(1 for it in unc if keymap[it["item"]]["question"] == q and keymap[it["item"]]["system"] == s)
        p["unreachable_sources"] = len(p.pop("_unreachable", ()))
        rows.append(dict(question=q, system=s, **p))
        print("  %s %-7s cited items %2d: held %2d (abstract only %d), incomplete %2d (no URL %d); uncited %d; "
              "unreachable sources %d" % (q, s, p["items"], p["held"], p["abstract_only"], p["incomplete"],
                                          p["no_url"], p["uncited"], p["unreachable_sources"]))
    srcs = list(man.values())
    lines = ["# WHU reliability study: M1 source snapshots, sha256 manifest (prepare_scoring.py snapshot-report)",
             "# Snapshots are held at ~/Projects/whu-study-private/scoring/m1/sources/<source_id>.txt.",
             "# route: a script (TLS fix), b curl on the operator's Mac, c open-access location; '-' first fetch;",
             "# 'a, bytes re-read': the first fetch's bytes, whose PDF text a crashed pdftotext had left empty;",
             "# d: fetched by the advisor in the desktop app's built-in browser (free pages only; round 3).",
             "#", "# source_id  extent  text_chars  text_sha256  raw_sha256  route  version"]
    for r in sorted(srcs, key=lambda r: r["source_id"]):
        rt = r.get("retrieval") or {}
        lines.append("%s  %-13s %8s  %s  %s  %s  %s" % (r["source_id"], r["extent"], r.get("text_chars", "-"),
                                                       r.get("text_sha256", "-"), r.get("raw_sha256", "-"),
                                                       rt.get("route") or ("a, bytes re-read" if r.get("reextracted") else "-"),
                                                       rt.get("version") or "-"))
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "snapshots_manifest.txt").write_text("\n".join(lines) + "\n")
    write_json(LOG / "snapshot_counts.json", {"written": now(), "per_answer": rows,
                                              "routes": {k: sum(1 for r in srcs if (r.get("retrieval") or {}).get("route") == k)
                                                     for k in ("a", "b", "c", "d")},
                                          "reachability": reach,
                                          "versions": {v: sum(1 for r in srcs if (r.get("retrieval") or {}).get("version") == v)
                                                       for v in sorted({(r.get("retrieval") or {}).get("version")
                                                                        for r in srcs} - {None})},
                                          "first_fetch_bytes_reread_to_held": sum(
                                              1 for r in srcs if r.get("reextracted") and r["extent"] != "unreachable"),
                                          "still_unreachable_free_but_blocking": sum(
                                              1 for n in need.values() if n["free_to_read_but_blocks_automation"]),
                                          "still_unreachable_free_but_blocking_not_tried_by_advisor": sum(
                                              1 for n in need.values() if n["free_to_read_but_blocks_automation"]
                                              and not n["advisor_tried"]),
                                          "sources": {"distinct": len(srcs),
                                                          "full_text": sum(r["extent"] == "full text" for r in srcs),
                                                          "abstract_only": sum(r["extent"] == "abstract only" for r in srcs),
                                                          "unreachable": sum(r["extent"] == "unreachable" for r in srcs)}})
    print("  sources: %d distinct; full text %d, abstract only %d, unreachable %d (listed in %s)"
          % (len(srcs), sum(r["extent"] == "full text" for r in srcs), sum(r["extent"] == "abstract only" for r in srcs),
             sum(r["extent"] == "unreachable" for r in srcs), run / "operator_fetch.json"))
    return 0


# --------------------------------------------------------------------------
# cost
# --------------------------------------------------------------------------

def do_cost(a) -> int:
    J = _load("judge_m1_ps", HERE / "judge_m1.py")
    P, O = J.S.PRICES[J.CLAUDE_MODEL], J.OPENAI_PRICE
    prep = STUDY / "runs" / "prep2"
    tok = json.loads((prep / "sources" / "tokens.json").read_text())
    pm = json.loads((prep / "sources" / "manifest.json").read_text())
    ratios = [r["text_chars"] / tok[r["source_id"]] for r in pm if r["source_id"] in tok and r.get("text_chars")]
    cpt = st.median(ratios)

    def replies(pat):
        return [json.load(open(f)) for f in sorted((STUDY / "runs").glob(pat))]
    m1c, m1o = replies("prep2/replies/claude/*.json"), replies("prep2/replies/openai/*.json")
    m2c, m2o = replies("prefreeze/m2/replies_v2/claude/*.json"), replies("prefreeze/m2/replies_v2/openai/*.json")
    u = lambda rs, k: st.mean([(r["attempts"][0]["usage"].get(k) or 0) for r in rs if r.get("attempts")])
    # Measured prices: each recorded call's usd against its tokens at the listed prices.
    def claude_usd(us):
        return (us.get("input", 0) * P["input"] + us.get("cache_write", 0) * P["cache_write"]
                + us.get("cache_read", 0) * P["cache_read"] + us.get("output", 0) * P["output"]) / 1e6
    def openai_usd(us):
        c = us.get("cache_read", 0)
        return ((us.get("input", 0) - c) * O["input"] + c * O["cached_input"] + us.get("output", 0) * O["output"]) / 1e6
    price_check = {
        "claude": max(abs(claude_usd(r["attempts"][0]["usage"]) - r["attempts"][0]["usd"]) for r in m1c + m2c),
        "openai": max(abs(openai_usd(r["attempts"][0]["usage"]) - r["attempts"][0]["usd"]) for r in m1o + m2o)}
    # OpenAI tokens per Claude token on the same M1 prompt (measured per item in prep2).
    oc = {r["item"]: r for r in m1o}
    otc = st.median([oc[r["item"]]["attempts"][0]["usage"]["input"]
                     / sum(r["attempts"][0]["usage"].get(k, 0) for k in ("input", "cache_read", "cache_write"))
                     for r in m1c if r["item"] in oc and r.get("attempts")])
    m1_rest_tokens = u(m1c, "input")                       # prompt after the documents, measured (uncached part)
    prompt_head = (STUDY / "prompts" / "m1_citation_support.md").read_text().split("{documents}")[0]
    head_tokens = len(prompt_head) / cpt
    out_c1, out_o1 = u(m1c, "output"), u(m1o, "output")
    out_c2, out_o2 = u(m2c, "output"), u(m2o, "output")

    run = SCORING / "m1"
    items = json.loads((run / "items.json").read_text(encoding="utf-8"))
    keymap = json.loads((run / "key_map.json").read_text(encoding="utf-8"))
    man = {r["url"]: r for r in json.loads((run / "sources" / "manifest.json").read_text())}
    held = [r["text_chars"] for r in man.values() if r["extent"] != "unreachable" and r.get("text_chars")]
    median_chars = st.median(held) if held else 0

    def m1_item(it, pending_as):
        docs = 0.0
        for c in it["citations"]:
            m = man.get(c.get("url") or "")
            chars = (m or {}).get("text_chars") if m and m["extent"] != "unreachable" else None
            if chars is None:
                if pending_as is None:
                    return None
                chars = pending_as
            docs += min(chars / cpt, J.MAX_SOURCE_TOKENS)
        prefix = head_tokens + docs
        c1 = (prefix * P["cache_write"] + m1_rest_tokens * P["input"] + out_c1 * P["output"]) / 1e6
        c2 = (prefix * P["cache_read"] + m1_rest_tokens * P["input"] + out_c1 * P["output"]) / 1e6
        o_prefix, o_rest = prefix * otc, m1_rest_tokens * otc
        o1 = ((o_prefix + o_rest) * O["input"] + out_o1 * O["output"]) / 1e6
        o2 = (o_prefix * O["cached_input"] + o_rest * O["input"] + out_o1 * O["output"]) / 1e6
        return {"claude": c1 + REPEAT_SHARE * c2, "openai": o1 + REPEAT_SHARE * o2, "doc_tokens": docs}

    per_answer = {}
    for it in items:
        km = keymap[it["item"]]
        key = "%s/%s" % (km["question"], km["system"])
        pa = per_answer.setdefault(key, {"items": 0, "held_items": 0, "claude_held": 0.0, "openai_held": 0.0,
                                         "claude_all": 0.0, "openai_all": 0.0, "doc_tokens_held": 0.0})
        pa["items"] += 1
        h = m1_item(it, None)
        al = m1_item(it, median_chars)
        if h:
            pa["held_items"] += 1
            pa["claude_held"] += h["claude"]; pa["openai_held"] += h["openai"]; pa["doc_tokens_held"] += h["doc_tokens"]
        pa["claude_all"] += al["claude"]; pa["openai_all"] += al["openai"]
    m1_held = sum(p["claude_held"] + p["openai_held"] for p in per_answer.values())
    m1_all = sum(p["claude_all"] + p["openai_all"] for p in per_answer.values())

    m2 = json.loads((SCORING / "m2" / "items.json").read_text(encoding="utf-8"))
    m2map = json.loads((SCORING / "m2" / "key_map.json").read_text(encoding="utf-8"))
    concl = {c["id"]: c for c in m2["conclusions"]}
    m2_head = (STUDY / "prompts" / "m2_conclusion_calibration.md").read_text()
    head, tail = m2_head.split("{answer}", 1)
    m2_rows, m2_total = {}, 0.0
    by_answer = {}
    for it in m2["items"]:
        by_answer.setdefault(it["answer"], []).append(it)
    for aid, its in by_answer.items():
        A = (len(head) + len((SCORING / "m2" / m2["answers"][aid]["file"]).read_text(encoding="utf-8"))) / cpt
        rests = [(len(tail) + sum(len(str(concl[i["conclusion"]].get(k) or "")) for k in
                  ("statement", "direction", "size", "certainty", "scope", "quote"))) / cpt for i in its]
        c = o = 0.0
        for n, R in enumerate(rests):
            c += ((A * (P["cache_write"] if n == 0 else P["cache_read"])) + R * P["input"] + out_c2 * P["output"]) / 1e6
            o += ((A + R) * otc * O["input"] + out_o2 * O["output"]) / 1e6
            c += REPEAT_SHARE * (A * P["cache_read"] + R * P["input"] + out_c2 * P["output"]) / 1e6
            o += REPEAT_SHARE * (A * otc * O["cached_input"] + R * otc * O["input"] + out_o2 * O["output"]) / 1e6
        m2_rows[aid] = {"question": m2map[aid]["question"], "system": m2map[aid]["system"],
                        "conclusions": len(its), "answer_tokens": round(A), "claude": round(c, 4), "openai": round(o, 4)}
        m2_total += c + o
    qn = sorted({r["question"] for r in m2_rows.values()})
    # WHU-S04 is not drawn yet: its judging is projected as the mean of the questions drawn.
    s04 = "WHU-S04" not in qn
    m1_q = {q: sum(p["claude_all"] + p["openai_all"] for k, p in per_answer.items() if k.startswith(q)) for q in qn}
    m2_q = {q: sum(r["claude"] + r["openai"] for r in m2_rows.values() if r["question"] == q) for q in qn}
    m1_s04 = st.mean(m1_q.values()) if s04 else 0.0
    m2_s04 = st.mean(m2_q.values()) if s04 else 0.0
    ledger = {}
    for e in J.S.entries():
        if e.get("issue") in QUESTIONS.values():
            ledger[e["issue"]] = ledger.get(e["issue"], 0.0) + float(e.get("usd") or 0)
    whu = {q: round(ledger.get(QUESTIONS[q], 0.0), 2) for q in QUESTIONS}
    judging = m1_all + m2_total + m1_s04 + m2_s04
    out = {
        "written": now(), "no_model_called": True,
        "inputs": {
            "chars_per_token": {"value": round(cpt, 3), "how": "median over prep round 2's %d snapshots of text "
                                "characters / Anthropic count_tokens (runs/prep2/sources/tokens.json)" % len(ratios)},
            "openai_tokens_per_claude_token": {"value": round(otc, 3), "how": "median over prep round 2's M1 items: "
                                               "OpenAI input tokens / Claude input+cache tokens, same prompt"},
            "m1_prompt_after_documents_tokens": round(m1_rest_tokens), "m1_prompt_before_documents_tokens": round(head_tokens),
            "output_tokens_mean": {"m1_claude": round(out_c1), "m1_openai_incl_reasoning": round(out_o1),
                                   "m2_claude": round(out_c2), "m2_openai_incl_reasoning": round(out_o2)},
            "prices_usd_per_million": {"claude-opus-5-5": P, J.OPENAI_MODEL: O},
            "price_check_max_abs_usd_difference_on_recorded_calls": {k: round(v, 6) for k, v in price_check.items()},
            "repeat_share": REPEAT_SHARE, "max_source_tokens": J.MAX_SOURCE_TOKENS,
            "pending_source_size_assumed_chars": round(median_chars),
        },
        "rules": [
            "M1, Claude: first read = (prompt head + documents) at cache-write price + prompt after the documents at "
            "input price + output; the 20% repeat reads the documents from cache (cache-read price).",
            "M1, OpenAI: first read = all input at the input price + output; the repeat reads the documents at the "
            "cached-input price (its cache hits only an identical prompt, which the repeat is).",
            "M2, Claude: the answer block is written to cache by an answer's first conclusion and read by the rest; "
            "repeats read it from cache.",
            "M2, OpenAI: every conclusion is a different prompt, so no cache except on the repeat.",
            "A document is capped at 150,000 tokens (longer ones are chunked to that).",
            "Items whose sources are pending the operator are projected at the median held snapshot size.",
            "WHU-S04 is projected as the mean of the questions drawn so far, for M1 and for M2.",
        ],
        "m1": {"per_answer": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in p.items()}
                              for k, p in sorted(per_answer.items())},
               "held_only_usd": round(m1_held, 2), "all_items_usd": round(m1_all, 2)},
        "m2": {"per_answer": dict(sorted(m2_rows.items(), key=lambda kv: (kv[1]["question"], kv[1]["system"]))),
               "usd": round(m2_total, 2)},
        "whu_s04_projected": {"m1_usd": round(m1_s04, 2), "m2_usd": round(m2_s04, 2)} if s04 else None,
        "judging_usd": round(judging, 2),
        "whu_measured_usd": whu,
        "whu_s04_note": "WHU-S04 is still running; its figure is spend so far, not its final cost.",
        "study_total_usd": round(judging + sum(whu.values()), 2),
        "over_300": judging + sum(whu.values()) > 300,
    }
    write_json(LOG / "cost_projection.json", out)
    print(json.dumps({k: out[k] for k in ("judging_usd", "whu_measured_usd", "study_total_usd", "over_300")}, indent=1))
    print("  M1 held-only $%.2f, all items $%.2f; M2 $%.2f; S04 slot M1 $%.2f M2 $%.2f"
          % (m1_held, m1_all, m2_total, m1_s04, m2_s04))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["verify", "blind", "sample", "snapshot", "snapshot-report", "cost"])
    ap.add_argument("--questions", default="WHU-S01,WHU-S02,WHU-S03")
    a = ap.parse_args()
    if a.step == "verify":
        return verify(a)
    rc = verify(a)
    if rc:
        return rc
    return {"blind": do_blind, "sample": do_sample, "snapshot": do_snapshot,
            "snapshot-report": lambda a: snapshot_report(), "cost": do_cost}[a.step](a)


if __name__ == "__main__":
    raise SystemExit(main())
