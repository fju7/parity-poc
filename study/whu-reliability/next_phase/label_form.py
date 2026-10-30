#!/usr/bin/env python3
"""Check 5's labelling form (validity plan §5): local only, never published. ARCHIVED 2026-10-30: see ARCHIVED.

    label_form.py draw          the probability sample (free; writes the private sample file once, never redraws)
    label_form.py serve         http://127.0.0.1:8765 (this computer only); labels appended to fred.jsonl

Sample: strata system x judge agreement (the two existing judges' first-read labels, after analyse.py's refusal rule,
equal or not), from round 1's M1 items both judges labelled (ChatGPT's are all UNCITED by code) and all 91 M2 items.
Agree strata: 8 (M1) or 1 (M2) drawn without replacement, random.Random("%d/check5/%s/%s/%s" % (SEED, measure,
system, stratum)); disagree strata: all. Order: random.Random("%d/check5/order" % SEED); each stratum's items in a
random order at positions (j + u) / n, all sorted by position, so every prefix holds the strata in proportion.

Blinding: the page gets the item's text only (M1: the drawn sentence, the context the judges saw, the cited sources'
held text; M2: the blinded answer and the key conclusion). Never the system, a judge label, a judge quote or the
stratum. Private files: ~/Projects/whu-study-private/validity/check5/{sample.json, fred.jsonl}.
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN_FREEZE = "b4cf31ad19046a63073461fc5195415bc496594b"
SEED = int(PLAN_FREEZE, 16)
PRIVATE = Path.home() / "Projects" / "whu-study-private" / "validity" / "check5"
SAMPLE, LABELS = PRIVATE / "sample.json", PRIVATE / "fred.jsonl"
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "quarterly" / "round1"
DRAW = {"M1": 8, "M2": 1}
PORT = 8765


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def frame() -> list[dict]:
    AR = _load("analyse_round1_lf", HERE.parent / "quarterly" / "analyse_round1.py")
    m1, m2 = AR.round1_rows()
    out = []
    A = AR.A
    valid = {"M1": A.M1_PASS | A.M1_FAIL, "M2": A.M2_PASS | A.M2_FAIL}
    for measure, rows in (("M1", m1), ("M2", m2)):
        for r in rows:
            # each judge's OWN first-read label (no refusal-rule fill), both countable: round1_ai_only's
            # "labelled_by_both" frame (M1 216, M2 91)
            l = {j: (r["raw"].get(j) or {}).get("label") for j in ("claude", "openai")}
            if r["uncited"] or l["claude"] not in valid[measure] or l["openai"] not in valid[measure]:
                continue
            out.append({"item": r["item"], "measure": measure, "system": r["system"], "question": r["question"],
                        "stratum": "agree" if l["claude"] == l["openai"] else "disagree",
                        "claude": l["claude"], "openai": l["openai"]})
    return out


def draw() -> int:
    if SAMPLE.exists():
        print("the sample exists (%s); it is never redrawn" % SAMPLE)
        return 0
    f = frame()
    strata: dict = {}
    for r in f:
        strata.setdefault((r["measure"], r["system"], r["stratum"]), []).append(r)
    chosen, sizes = [], {}
    for key in sorted(strata):
        pool = sorted(strata[key], key=lambda r: r["item"])
        m, s, st = key
        k = len(pool) if st == "disagree" else min(DRAW[m], len(pool))
        got = random.Random("%d/check5/%s/%s/%s" % (SEED, m, s, st)).sample(pool, k)
        sizes["%s/%s/%s" % key] = {"N": len(pool), "n": k}
        chosen += got
    rng = random.Random("%d/check5/order" % SEED)
    by: dict = {}
    for r in chosen:
        by.setdefault((r["measure"], r["system"], r["stratum"]), []).append(r)
    placed = []
    for key in sorted(by):
        rs = by[key][:]
        rng.shuffle(rs)
        u = rng.random()
        placed += [((j + u) / len(rs), r) for j, r in enumerate(rs)]
    placed.sort(key=lambda x: (x[0], x[1]["item"]))
    items = [dict(r, n=i + 1) for i, (_p, r) in enumerate(placed)]
    PRIVATE.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text(json.dumps({"seed": "SEED=%s" % PLAN_FREEZE, "drawn_at": datetime.now(timezone.utc).isoformat(
        timespec="seconds"), "strata": sizes, "items": items}, indent=1))
    print(json.dumps(sizes, indent=1))
    print("%d items (M1 %d, M2 %d) -> %s" % (len(items), sum(r["measure"] == "M1" for r in items),
                                             sum(r["measure"] == "M2" for r in items), SAMPLE))
    return 0


# ---------------------------------------------------------------------------------------------------------------

def content(it: dict) -> dict:
    """What the page shows: text only, nothing that names the system, a judge or the stratum."""
    if it["measure"] == "M1":
        run = RUN / "m1"
        row = next(r for r in json.loads((run / "items.json").read_text()) if r["item"] == it["item"])
        man = {m["url"]: m for m in json.loads((run / "sources" / "manifest.json").read_text())}
        srcs = []
        for k, c in enumerate(row["citations"], 1):
            m = man.get(c.get("url") or "")
            if m and m["extent"] != "unreachable":
                srcs.append({"n": k, "extent": m["extent"],
                             "text": (run / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8")})
            else:
                srcs.append({"n": k, "extent": "not held", "text": ""})
        return {"measure": "M1", "claim": row["claim"], "context": row.get("context") or "", "sources": srcs}
    spec = json.loads((RUN / "m2" / "items.json").read_text())
    row = next(r for r in spec["items"] if r["item"] == it["item"])
    c = next(x for x in spec["conclusions"] if x["id"] == row["conclusion"])
    return {"measure": "M2", "answer": (RUN / "m2" / spec["answers"][row["answer"]]["file"]).read_text(encoding="utf-8"),
            "conclusion": {k: c.get(k) or "not stated" for k in ("statement", "direction", "size", "certainty",
                                                                 "scope", "quote")}}


def labelled() -> dict:
    out = {}
    if LABELS.exists():
        for line in LABELS.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["n"]] = r                    # the last save for an item counts
    return out


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Label items</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#666;--line:#ddd;--card:#fff;--acc:#2a5db0;--hit:#ffe58a}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--fg:#e8e6e1;--muted:#9a9a9a;--line:#333;--card:#1f1f1f;--acc:#7aa7ff;--hit:#6b5a00}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.muted{color:var(--muted);font-size:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin:12px 0}
.claim{font-size:18px;font-weight:600}.ctx{color:var(--muted);font-size:14px;white-space:pre-wrap}
.src{max-height:55vh;overflow:auto;white-space:pre-wrap;font:13px/1.45 ui-monospace,Menlo,monospace;border-top:1px solid var(--line);padding-top:8px}
.opts label{display:block;padding:6px 8px;border-radius:6px;cursor:pointer}.opts label:hover{background:var(--line)}
.sub{margin-left:28px}button{font:inherit;padding:8px 16px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}mark{background:var(--hit);color:inherit}
input[type=search]{font:inherit;padding:6px 8px;width:260px;max-width:100%;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;margin:0}dt{color:var(--muted)}
</style></head><body><div class="wrap">
<header><div><b>Label items</b> <span class="muted" id="pos"></span></div>
<div><button id="prev">&larr; Back</button> <button id="next">Skip &rarr;</button></div></header>
<div id="item"></div></div>
<script>
let N=0,cur=1,done={};
async function j(u,o){const r=await fetch(u,o);return r.json()}
function esc(s){return (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
async function load(n){cur=n;const d=await j('/api/item/'+n);const s=await j('/api/status');N=s.total;done=s.done;
document.getElementById('pos').textContent='Item '+n+' of '+N+' · '+Object.keys(done).length+' saved';
const prev=done[n]||{};let h='';
if(d.measure==='M1'){
 h+='<div class="card"><div class="muted">Sentence</div><div class="claim">'+esc(d.claim)+'</div>';
 h+='<div class="muted" style="margin-top:8px">Text just before it (context only)</div><div class="ctx">'+esc(d.context)+'</div></div>';
 h+='<div class="card"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b>Cited source'+(d.sources.length>1?'s':'')+'</b><input type="search" id="find" placeholder="Find in source"></div>';
 d.sources.forEach(s=>{h+='<div class="muted">Source ['+s.n+'] · '+esc(s.extent)+'</div><div class="src">'+(s.text?esc(s.text):'(not held)')+'</div>'});
 h+='</div><div class="card opts"><b>Does the cited source support this sentence?</b>';
 h+=opt('Supported')+opt('Not supported')+'<div class="sub">'+['not stated','overstates','contradicts','wrong source'].map(x=>opt2(x)).join('')+'</div>'+opt("Can't tell");
}else{
 const c=d.conclusion;h+='<div class="card"><b>Key conclusion</b><dl>';
 for(const k of ['statement','direction','size','certainty','scope','quote'])h+='<dt>'+k+'</dt><dd>'+esc(c[k])+'</dd>';
 h+='</dl></div><div class="card"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b>The answer</b><input type="search" id="find" placeholder="Find in answer"></div><div class="src">'+esc(d.answer)+'</div></div>';
 h+='<div class="card opts"><b>Compared with the key conclusion, the answer…</b>'+['Matches','Overstates','Understates','Omits','Contradicts',"Can't tell"].map(opt).join('');
}
h+='<label style="margin-top:8px"><input type="checkbox" id="know"> I think I know which system wrote this</label>';
h+='<div style="margin-top:10px"><button class="primary" id="save">Save and next</button></div></div>';
document.getElementById('item').innerHTML=h;
if(prev.label){const e=document.querySelector('input[name=lab][value="'+prev.label+'"]');if(e)e.checked=true}
if(prev.why){const e=document.querySelector('input[name=why][value="'+prev.why+'"]');if(e)e.checked=true}
document.getElementById('know').checked=!!prev.think_i_know;
const srcs=[...document.querySelectorAll('.src')],orig=srcs.map(x=>x.innerHTML);
document.getElementById('find').addEventListener('input',e=>{const q=e.target.value.trim();srcs.forEach((x,i)=>{x.innerHTML=orig[i];
 if(q.length<3)return;const re=new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');x.innerHTML=orig[i].replace(re,m=>'<mark>'+m+'</mark>')});
 const m=document.querySelector('mark');if(m)m.scrollIntoView({block:'center'})});
document.getElementById('save').onclick=save;window.scrollTo(0,0)}
function opt(v){return '<label><input type="radio" name="lab" value="'+v+'"> '+v+'</label>'}
function opt2(v){return '<label><input type="radio" name="why" value="'+v+'"> '+v+'</label>'}
async function save(){const l=document.querySelector('input[name=lab]:checked');if(!l){alert('Pick a label first');return}
 const w=document.querySelector('input[name=why]:checked');
 if(l.value==='Not supported'&&!w){alert('Pick what kind of "not supported"');return}
 await j('/api/label',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({n:cur,label:l.value,why:l.value==='Not supported'?w.value:null,think_i_know:document.getElementById('know').checked})});
 load(cur<N?cur+1:cur)}
document.getElementById('prev').onclick=()=>load(Math.max(1,cur-1));
document.getElementById('next').onclick=()=>load(Math.min(N,cur+1));
j('/api/status').then(s=>{let n=1;while(s.done[n]&&n<s.total)n++;load(n)});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        items = json.loads(SAMPLE.read_text())["items"]
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html")
        if self.path == "/api/status":
            return self._send(200, json.dumps({"total": len(items), "done": {str(k): {"label": v["label"], "why": v.get(
                "why"), "think_i_know": v.get("think_i_know")} for k, v in labelled().items()}}))
        if self.path.startswith("/api/item/"):
            n = int(self.path.rsplit("/", 1)[1])
            it = next((x for x in items if x["n"] == n), None)
            return self._send(200, json.dumps(content(it))) if it else self._send(404, "{}")
        self._send(404, "{}")

    def do_POST(self):
        if self.path != "/api/label":
            return self._send(404, "{}")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        items = {x["n"]: x for x in json.loads(SAMPLE.read_text())["items"]}
        it = items[int(body["n"])]
        ok = {"M1": {"Supported", "Not supported", "Can't tell"},
              "M2": {"Matches", "Overstates", "Understates", "Omits", "Contradicts", "Can't tell"}}[it["measure"]]
        if body.get("label") not in ok:
            return self._send(400, json.dumps({"error": "label"}))
        rec = {"n": it["n"], "item": it["item"], "measure": it["measure"], "label": body["label"], "why": body.get("why"),
               "think_i_know": bool(body.get("think_i_know")), "by": "Fred",
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with LABELS.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        self._send(200, json.dumps({"ok": True}))


ARCHIVED = ("ARCHIVED 2026-10-30 (advisor ruling): check 5 is not run in this phase (no qualified reviewer; open). "
            "The drawn sample, never labelled, is in ~/Projects/whu-study-private/validity/check5/archive/. "
            "Check 5b (next_phase/figure_check.py) replaces it.")


def serve() -> int:
    print("STOP: " + ARCHIVED)
    return 2
    if not SAMPLE.exists():
        print("no sample yet: run `label_form.py draw` first")
        return 2
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("Open http://127.0.0.1:%d in your browser (this computer only). Ctrl+C to stop; labels are kept in %s"
          % (PORT, LABELS))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    raise SystemExit(draw() if cmd == "draw" else serve() if cmd == "serve" else (print(__doc__) or 2))
