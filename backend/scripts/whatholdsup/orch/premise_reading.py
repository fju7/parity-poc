"""The premise rows a drafting session used to fill by hand, filled by bounded model steps checked by code (Fred's
terms B3 and B4 after orchestrator trial 1 attempt 23, 2026-11-24). Attempt 23's preflight stopped on them: the
orchestrator's premise step writes only the rows fixed before any source.

B3 -- "belief shown to be held" and "carried in general coverage?" (premise.json belief.carried_by,
public_record_check.carried_in_general_coverage). One model call with web search PROPOSES published outlets that
state the belief. CODE then fetches each page itself (the honest client, tls.USER_AGENT; robots.txt respected; a
challenge, sign-in or paywall page is a wall and is never worked around) and checks that the page exists and contains
the belief's key words. What is recorded is the model's reading, named as such, with the URL, the fetch time and the
sha256 of the bytes. If no proposed page verifies, nothing is written and the rows stop the page.

B4 -- "what the sources show" (advisor's ruling 1 after the A/B build), "direction recorded" and "kill condition tested"
(premise.json what_the_sources_show, direction, kill_condition_tested). One model call,
no search, is given the belief, the kill condition and passages of the HELD sources (source_store.held: never a
blocked one), and answers both, each with the passage it relies on quoted. CODE checks each quotation verbatim in that
source's held text; an answer whose quotation is not there is not written, and its row stops the page.

premise.json keeps offsets and hashes; the quotation text goes to rulings/premise_checks.jsonl with the call's
record, as the omission records do (no source text in the case's JSON records).
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

LOG = "rulings/premise_checks.jsonl"

# The check pilot's markers (study/whu-reliability/check_pilot/pipeline_v3.py CHALLENGE_MARKERS / SIGNIN_MARKERS),
# held equal to them by test.
CHALLENGE_MARKERS = ("just a moment", "cf-chl", "challenge-platform", "captcha", "are you a robot",
                     "verify you are human", "awswaf", "attention required", "_incapsula_", "datadome", "px-captcha",
                     "client challenge", "/_fs-ch-", "checking your browser", "validating your request",
                     "verifying you are human", "browser check", "bot protection")
SIGNIN_MARKERS = ("sign in to continue", "log in to continue", "please sign in", "please log in",
                  "subscribe to continue", "purchase this article", "buy this article", "institutional login",
                  "access through your institution")
SIGNIN_PATH = re.compile(r"/(login|signin|sign-in|sso|auth|idp|shibboleth|subscribe|paywall)\b", re.I)

STOP_WORDS = frozenset("""a an and are as at be been but by can could do does for from had has have how if in into is
it its may might more most no not of on or our so such than that the their them then there these they this those to
was we were what when where which while who will with would you your also very much many any some all each other
only own same both just over under about between through during before after above below up down out off again
further once here why""".split())
KEY_WORDS_SHARE = 0.6       # the page must contain at least this share of the belief's key words
KEY_WORDS_MIN = 4

BELIEF_PROMPT = """A fact-check is about to say what readers already believe on a question. Find up to {n} pages,
published by general news, public-information or advocacy outlets (not journals, not systematic reviews, not the
sources a fact-check would cite), that state the belief below as their own view or as what people commonly hold.
Search the web. Give only pages you opened. JSON only:
{{"outlets": [{{"outlet": "<publisher name>", "url": "<the page's URL>", "sentence": "<the page's sentence that states the belief, copied exactly>"}}]}}

BELIEF:
{belief}
"""

# ONE RE-ASK (advisor's ruling D on P117, 2026-11-25). On WHU-OT1-02zc the step proposed three outlets and code
# confirmed none, and none was a wall: one URL redirected to another page, two pages carried too few of the belief's
# key words. A different proposal could avoid those, so when round 1 confirms nothing the step asks once more for
# DIFFERENT outlets, naming the refused ones; code also drops any round-2 candidate that repeats a refused URL or
# outlet. verify_outlet is unchanged; both rounds are logged ("round": 1 | 2).
REASK_TAIL = """
These pages were proposed before and could not be confirmed; give DIFFERENT outlets and pages, none of these:
{refused}
"""

READING_PROMPT = """You read the passages below from the sources a fact-check holds, and answer three things about the
premise the fact-check set before reading them. Answer only from the passages; for each, quote the passage you rely on,
copied character for character (at most 300 characters), with the id of the source it comes from.

0. WHAT THE SOURCES SHOW: one sentence saying what the held sources show on the question, in their own certainty
   words, and never more than the quoted passage supports.
1. DIRECTION: does the evidence CONFIRM the belief, CORRECT it (it is wrong), or NARROW it (true only in part, or only
   for some programmes, people or outcomes)?
2. KILL CONDITION: was the kill condition met? "killed" if the passages show it, "narrowed" if they show it in part,
   "survived" if they show the opposite.

Reply with ONE JSON object and nothing else:
{{"sources_show": "<one sentence>", "sources_show_quote": {{"source": "<id>", "quote": "<verbatim>"}},
 "direction": "confirms" | "corrects" | "narrows", "direction_quote": {{"source": "<id>", "quote": "<verbatim>"}},
 "direction_why": "<one sentence>",
 "kill_result": "survived" | "narrowed" | "killed", "kill_quote": {{"source": "<id>", "quote": "<verbatim>"}},
 "kill_note": "<one sentence>"}}

BELIEF:
{belief}

KILL CONDITION:
{kill}

PASSAGES:
{passages}
"""
DIRECTIONS = ("confirms", "corrects", "narrows")
KILL_RESULTS = ("survived", "narrowed", "killed")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(case: Path, row: dict) -> None:
    p = case / LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(row, at=now()), ensure_ascii=False) + "\n")


def _premise(case: Path) -> dict:
    return json.loads((case / "premise.json").read_text(encoding="utf-8"))


def _save_premise(case: Path, d: dict) -> None:
    (case / "premise.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ B3: the belief, in published outlets

def key_words(belief: str) -> list[str]:
    """The belief's content words (lower case, 4+ letters, not a stop word), in order, once each."""
    out = []
    for w in re.findall(r"[a-z][a-z'-]{3,}", (belief or "").lower()):
        w = w.strip("'-")
        if w and w not in STOP_WORDS and w not in out:
            out.append(w)
    return out


def visible_text(body: bytes) -> str:
    t = body.decode("utf-8", "replace")
    t = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", t, flags=re.I | re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as H
    return " ".join(H.unescape(t).split())


def is_wall(status: int, headers: dict, body: bytes, final_url: str) -> str | None:
    """Why the page is a wall (challenge, sign-in, paywall), or None."""
    h = {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}
    if h.get("cf-mitigated") == "challenge" or h.get("x-amzn-waf-action") in ("challenge", "captcha"):
        return "challenge (headers)"
    low = body[:20000].decode("utf-8", "replace").lower()
    if status in (401, 402, 403, 429, 503):
        return "HTTP %d" % status
    if len(body) < 100000 and any(m in low for m in CHALLENGE_MARKERS):
        return "challenge page"
    if SIGNIN_PATH.search(urllib.parse.urlsplit(final_url or "").path) or (
            len(body) < 60000 and any(m in low for m in SIGNIN_MARKERS)):
        return "sign-in or paywall"
    return None


def fetch(url: str, timeout: int = 30) -> dict:
    """{"status", "headers", "body", "final_url"} with the honest client (tls.urlopen, tls.USER_AGENT)."""
    import urllib.error
    import urllib.request
    import tls
    req = urllib.request.Request(url, headers={"User-Agent": tls.USER_AGENT, "Accept-Language": "en"})
    try:
        r = tls.urlopen(req, timeout=timeout)
        body = r.read()
        hdrs = dict(r.headers.items()) if getattr(r, "headers", None) else {}
        return {"status": getattr(r, "status", None) or r.getcode(), "headers": hdrs, "body": body,
                "final_url": getattr(r, "url", None) or url}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": dict(e.headers.items()) if e.headers else {},
                "body": e.read() if hasattr(e, "read") else b"", "final_url": url}


def robots_allows(url: str, get=fetch) -> tuple[bool, str]:
    """robots.txt read as the check pilot reads it: 4xx allows; 5xx, unreadable or a challenge disallows."""
    import urllib.robotparser
    import tls
    p = urllib.parse.urlsplit(url)
    try:
        r = get("%s://%s/robots.txt" % (p.scheme, p.netloc))
    except Exception as e:
        return False, "robots.txt could not be read (%s)" % type(e).__name__
    if is_wall(r["status"], r["headers"], r["body"], r["final_url"]) and r["status"] not in (401, 402, 403, 404):
        return False, "robots.txt answered with a wall"
    if 400 <= r["status"] < 500:
        return True, "robots.txt HTTP %d: allowed" % r["status"]
    if r["status"] != 200:
        return False, "robots.txt HTTP %d: not allowed" % r["status"]
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r["body"].decode("utf-8", "replace").splitlines())
    ok = rp.can_fetch(tls.USER_AGENT, url)
    return ok, "robots.txt %s it" % ("allows" if ok else "disallows")


def verify_outlet(belief: str, cand: dict, get=fetch, save=None) -> dict:
    """One proposed outlet, checked by code: {"ok": bool, "why", ...the record fields}."""
    url = (cand.get("url") or "").strip()
    out = {"outlet": (cand.get("outlet") or "").strip()[:200], "url": url}
    if not url.startswith(("http://", "https://")) or not out["outlet"]:
        return dict(out, ok=False, why="no outlet name or no http(s) URL")
    allowed, why = robots_allows(url, get)
    if not allowed:
        return dict(out, ok=False, why=why)
    try:
        r = get(url)
    except Exception as e:
        return dict(out, ok=False, why="the page could not be fetched (%s: %s)" % (type(e).__name__, str(e)[:120]))
    wall = is_wall(r["status"], r["headers"], r["body"], r["final_url"])
    if wall:
        return dict(out, ok=False, why="a wall (%s): not worked around" % wall)
    if r["status"] != 200 or not r["body"]:
        return dict(out, ok=False, why="HTTP %s" % r["status"])
    text = visible_text(r["body"]).lower()
    kws = key_words(belief)
    found = [w for w in kws if re.search(r"(?<![a-z])%s" % re.escape(w), text)]
    need = max(KEY_WORDS_MIN, int(len(kws) * KEY_WORDS_SHARE + 0.999))
    sha = hashlib.sha256(r["body"]).hexdigest()
    if save:
        save(sha, r["body"])
    rec = dict(out, final_url=r["final_url"], fetched_at=now(), sha256=sha, bytes=len(r["body"]),
               key_words=len(kws), key_words_found=found, robots=why)
    if len(found) < min(need, len(kws)) or len(kws) < KEY_WORDS_MIN:
        return dict(rec, ok=False, why="the page has %d of the belief's %d key words (needs %d)"
                    % (len(found), len(kws), need))
    return dict(rec, ok=True, why="the page exists and has %d of the belief's %d key words" % (len(found), len(kws)))


def belief_outlets(case: Path, ask, model: str, get=fetch, save=None, n: int = 3) -> dict:
    """B3. ASK(prompt, max_tokens, role) -> reply text (a web-search call). Writes belief.carried_by and
    public_record_check.carried_in_general_coverage only for outlets code verified."""
    from orch import model_steps as M
    d = _premise(case)
    belief = ((d.get("belief") or {}).get("statement") or "").strip()
    if not belief:
        return {"verified": 0, "why": "no belief stated"}
    def _cands(reply):
        cs = (reply or {}).get("outlets") if isinstance(reply, dict) else None
        return [c for c in (cs or []) if isinstance(c, dict)][:n]

    def _record(rnd, c, v):
        _log(case, {"check": "belief-outlet", "round": rnd, "by": "model reading (%s, web search)" % model,
                    "proposed": {"outlet": c.get("outlet"), "url": c.get("url"), "sentence": c.get("sentence")},
                    "code": {k: v.get(k) for k in ("ok", "why", "sha256", "final_url", "key_words",
                                                   "key_words_found", "robots", "fetched_at")}})

    reply = M.ask_json(ask, BELIEF_PROMPT.format(n=n, belief=belief), M.LIMITS["belief"], "belief-outlet")
    cands = _cands(reply)
    checked = [verify_outlet(belief, c, get, save) for c in cands]
    for c, v in zip(cands, checked):
        _record(1, c, v)
    rounds = [{"round": 1, "proposed": len(cands), "verified": sum(1 for v in checked if v["ok"])}]
    if not any(v["ok"] for v in checked):
        refused = [(c, v) for c, v in zip(cands, checked)]
        seen_urls = {_url_key(c.get("url")) for c, _v in refused} - {""}
        seen_outlets = {_outlet_key(c.get("outlet")) for c, _v in refused} - {""}
        listing = "\n".join("- %s (%s): %s" % (c.get("outlet") or "?", c.get("url") or "?", v.get("why"))
                            for c, v in refused) or "- (none proposed)"
        r2 = {"round": 2, "proposed": 0, "verified": 0, "excluded": 0}
        try:
            reply2 = M.ask_json(ask, BELIEF_PROMPT.format(n=n, belief=belief) + REASK_TAIL.format(refused=listing),
                                M.LIMITS["belief"], "belief-outlet-reask")
        except M.Unusable as e:
            reply2 = None
            r2["unusable"] = str(e)[:200]
        for c in _cands(reply2):
            if _url_key(c.get("url")) in seen_urls or _outlet_key(c.get("outlet")) in seen_outlets:
                _record(2, c, {"ok": False, "why": "excluded by code: refused in round 1, not checked again"})
                r2["excluded"] += 1
                continue
            v = verify_outlet(belief, c, get, save)
            _record(2, c, v)
            cands.append(c)
            checked.append(v)
            r2["proposed"] += 1
            r2["verified"] += 1 if v["ok"] else 0
        rounds.append(r2)
    good = [v for v in checked if v["ok"]]
    if good:
        b = d.setdefault("belief", {})
        b["carried_by"] = [{"outlet": v["outlet"], "url": v["url"], "final_url": v["final_url"],
                            "fetched_at": v["fetched_at"], "sha256": v["sha256"],
                            "key_words_found": v["key_words_found"], "key_words": v["key_words"],
                            "by": "a model's reading (%s, web search), verified by code: the page was fetched "
                                  "with the honest client and contains the belief's key words" % model}
                           for v in good]
        g = good[0]
        d.setdefault("public_record_check", {})["carried_in_general_coverage"] = (
            "Yes: %s (%s), fetched %s, sha256 %s; the page contains %d of the belief's %d key words. A model's "
            "reading (web search), checked by code." % (g["outlet"], g["url"], g["fetched_at"][:10], g["sha256"][:16],
                                                        len(g["key_words_found"]), g["key_words"]))
        _save_premise(case, d)
    return {"proposed": len(cands), "verified": len(good), "rounds": rounds,
            "refused": ["%s: %s" % ((v.get("url") or "")[:80], v["why"]) for v in checked if not v["ok"]]}


def _url_key(u) -> str:
    u = str(u or "").strip().lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def _outlet_key(o) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(o or "").lower()))


# ------------------------------------------------------------------ B4: direction and kill condition, from held text

def _held_passages(slug: str, query: str, budget: int = 12000) -> tuple[dict, dict]:
    """({passage id: text}, {source id: held text}) from the held sources only."""
    import passage_index as P
    import ruling as R
    held = R.held_texts(slug)
    out = {}
    per = max(1, budget // max(1, len(held)))
    for sid, text in sorted(held.items()):
        used = 0
        idx = P.index_of(text)
        # the passages that score for the belief and kill condition; if none does, the source's opening passages
        # (a short or plainly worded source must not leave the step with nothing to read)
        ranked = [p for p, _s in idx.top(query, k=40)] or list(idx.passages)[:40]
        for p in ranked:
            t = text[p.start:p.end]
            if used + len(t) > per:
                break
            out["%s#%d" % (sid, p.idx)] = (sid, " ".join(t.split()))
            used += len(t)
    return out, held


def _verified(quote: dict, held: dict) -> dict | None:
    """{"source", "offsets", "span_sha256", "document": held source} if QUOTE is verbatim in its source's held text."""
    import audit_stage as A
    import passage_index as P
    if not isinstance(quote, dict):
        return None
    sid, q = str(quote.get("source") or ""), (quote.get("quote") or "").strip().strip('"\u201c\u201d')
    if sid not in held or len(q) < 20 or len(q) > 400 or not A.quoted_in(q, held[sid]):
        return None
    sp = P.find_span(held[sid], q)
    span = held[sid][sp[0]:sp[1]] if sp else q
    return {"source": sid, "offsets": list(sp) if sp else None,
            "span_sha256": hashlib.sha256(span.encode("utf-8")).hexdigest()}


def direction_and_kill(case: Path, slug: str, ask, model: str) -> dict:
    """B4. ASK(prompt, max_tokens, role) -> reply text. Writes direction and kill_condition_tested only where the
    quotation is verbatim in the held text of the source named."""
    from orch import model_steps as M
    d = _premise(case)
    belief = ((d.get("belief") or {}).get("statement") or "").strip()
    kill = (d.get("kill_condition") or "").strip() if isinstance(d.get("kill_condition"), str) else ""
    passages, held = _held_passages(slug, belief + " " + kill)
    if not passages:
        return {"direction": None, "kill": None, "why": "no held passage"}
    body = "\n\n".join("[%s] %s" % (sid, t) for _pid, (sid, t) in passages.items())
    reply = M.ask_json(ask, READING_PROMPT.format(belief=belief, kill=kill, passages=body), M.LIMITS["premise_reading"], "premise-reading")
    out = {"direction": None, "kill": None, "sources_show": None}
    r = reply if isinstance(reply, dict) else {}
    show = " ".join(str(r.get("sources_show") or "").split())
    sq = _verified(r.get("sources_show_quote"), held) if 20 <= len(show) <= 600 else None
    dq = _verified(r.get("direction_quote"), held) if r.get("direction") in DIRECTIONS else None
    kq = _verified(r.get("kill_quote"), held) if r.get("kill_result") in KILL_RESULTS else None
    by = "a model's reading (%s, from held sources), the quotation verified verbatim by code" % model
    _log(case, {"check": "premise-reading", "by": by, "reply": r,
                "code": {"sources_show_quote_verbatim": bool(sq), "direction_quote_verbatim": bool(dq),
                         "kill_quote_verbatim": bool(kq)}})
    if sq:
        # advisor's ruling 1 after the A/B build: "what the sources show", the same model-answers-code-verifies rule
        d["what_the_sources_show"] = {"statement": show, "sources": [sq["source"]], "by": by, "written_at": now(),
                                      "evidence": sq}
        out["sources_show"] = True
    if dq:
        d["direction"] = dict(d.get("direction") or {}, value=r["direction"], by=by, written_at=now(),
                              evidence=dq, why=str(r.get("direction_why") or "")[:300])
        out["direction"] = r["direction"]
    if kq:
        d["kill_condition_tested"] = {"by": by, "on": now()[:10], "result": r["kill_result"],
                                      "note": str(r.get("kill_note") or "")[:300], "evidence": kq,
                                      "_result_values": list(KILL_RESULTS)}
        out["kill"] = r["kill_result"]
    if sq or dq or kq:
        _save_premise(case, d)
    return out
