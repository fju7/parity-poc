# "Check an AI answer": internal pilot

Status: written 2026-10-28, before any pilot code. Internal only. Exploratory: outside the
reliability study's H1 and H2, and it changes no study record, result or rule. The test, the
sample and the pass bar below are fixed by the commit that adds this file, before any run.
Budget: Fred's approval of 2026-10-28 (option B), `--cap 35` on ledger issue `whu-check-pilot`.

## 1. What it is

A tool that takes an AI research answer with citations and says, for each factual claim in it,
whether the source it cites backs the claim. It is built from the reliability study's own code,
so the pilot can be tested against the study's own labels.

## 2. Input

A pasted AI answer with its citations, in any capture format the study handled
(`study/whu-reliability/blinding/adapt.py`):

| Format | adapt.py | Answers in the study |
|---|---|---|
| inline Markdown links (the report section) | `report_section` | Claude Research S01-S04 |
| ChatGPT page-data markers 【…】 with the capture's citation table | `chatgpt_lenticular` | ChatGPT S01, S02 |
| ChatGPT `[[k]](url)` | `chatgpt_bracketed` | ChatGPT S03, S04 |
| Gemini Markdown export, "Works cited" list | `report_section` + `works_cited` | Gemini S01, S02 |
| Gemini HTML export | `gemini_html` | Gemini S03, S04 |
| Claude "Download as Markdown", numbered "## Sources" | `claude_sources` | Claude S05-S08 |
| Perplexity "Download as Markdown", `[^n]` and "## References" | `perplexity_sources` | Perplexity S01-S04 |

A pasted answer without a capture header is read as if it were the report section (the code
prefixes the "## Report" heading `report_section` looks for). The format is named by the caller
or, if not named, detected from the text by the first rule that applies: an HTML document
(Gemini HTML); 【…】 markers; `[[k]](url)`; `[^n]` markers with a "References" heading; a
"Works cited" heading; a numbered "Sources" heading; otherwise inline links. No wording is
changed; an answer the adapter cannot read stops with the adapter's own error.

## 3. Pipeline (the study's code, reused, not copied)

1. **Adapt** the answer (table above).
2. **Sentences and citations**, as `prepare_scoring.py` did: `blind.from_markdown` numbers the
   links, `blind.blind` and `blind.sentence_rows` split the text into sentences with their
   ~400-character context (the blinding rules run, as they did for the study's judge). A
   claim is a sentence `identifiability.claim_like` accepts (samplable, 8 to 70 words, a number
   or a citation marker). Each claim's citations are its `[n]` markers looked up in the
   answer's reference list (`adapt.fragment_free` on each address).
3. **Limit.** The first 40 claims in the answer's order are checked; the rest are listed as not
   checked. (40 is the preview's limit.)
4. **Open-licence copies only.** For each cited address, the work's licence is read before
   anything is fetched: Europe PMC's `license` field (`find_access.epmc`, by the PMCID, PMID or
   DOI in the address, `find_access.ids_from_url`), else an Unpaywall open-access location whose
   `license` starts `cc` (`find_access.unpaywall`). Accepted licences: any Creative Commons
   licence (`cc0`, `cc by` and its variants). A work with none is not fetched and is not judged.
5. **Snapshot**, for a work with an open licence: `retrieve_sources.retrieve`, routes (a) the
   script, (b) curl, (c) open-access locations, in that order; held only if `snapshot.extent`
   calls the text full text or abstract only. Route (d) (a person's browser) is never used.
6. **Judge**: `judge_m1.py`'s M1 v3 prompt (`prompts/m1_citation_support.md`, its sha256
   checked against `judge_m1.PROMPT_SHA256` before any call), built by `judge_m1.build`, sent by
   `judge_m1.call_claude` (Claude judge, `judge_m1.CLAUDE_MODEL`, only), parsed by
   `judge_m1.parse`, labelled by `judge_m1.final_label`. Long sources by `judge_m1.chunk`, and
   `judge_m1.delivery_problems` as in the study. **First read only**: no second read, no
   consistency sample. A refused call is retried once unchanged, as in the study.
7. **Label** per claim, with the reason:

| Pilot label | When | Reason shown |
|---|---|---|
| BACKED | M1 label Supported | the judge's reason and its quoted span |
| NOT BACKED | Overstates, Understates, Absent, Wrong source, Contradicted | the M1 label, the judge's reason and span |
| NO SOURCE | the sentence has no citation marker (the study's UNCITED) | "no citation" |
| COULDN'T CHECK | any cited work with no open-licence copy, or not retrieved, or Unreachable, NOT_VERIFIABLE_ABSTRACT (Absent on an abstract only), INCOMPLETE_SOURCES (the delivery check), REFUSED, or a reply that does not parse | which source and why |

As in the study, a claim is never judged on part of its sources: if any cited work cannot be
checked, the claim is COULDN'T CHECK. This mapping is the study's own (`analyse.py`
`M1_PASS`/`M1_FAIL`; `scorecard/measures.py` supported / cited_not_supported / uncited).

## 4. Sample

8 study answers, 2 each from Claude Research, ChatGPT deep research, Gemini Deep Research and
Perplexity Deep Research, on WHU-S01 to WHU-S04 only (ChatGPT searched the web there).

Draw: `rng = random.Random("%d/check-pilot" % SEED)`, SEED the freeze commit
`5d83e9b8025312923f3fb8ea2d5de3b47c212362` read as a hexadecimal integer (written in decimal,
as `prepare_scoring.py` writes it). For each system in the order Claude, ChatGPT, Gemini,
Perplexity: `sorted(rng.sample(["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"], 2))`, one generator
for all four draws. The input for each answer is its study capture
(`~/Projects/whu-study-private/answers/<q>/`, `gemini.raw.html` for Gemini S03/S04), read in
the format `prepare_scoring.tool_answer` used; Perplexity's are the re-run captures the study
scored (not the set-aside personalised ones).

## 5. The test (fixed before any run)

**Same sentence.** The pilot's sentences for an answer are compared with the study's
`scoring/blinded/<q>/<system>.sentences.jsonl` (Perplexity: `scoring/perplexity/blinded/`) by
index and text. If they differ, that is reported, and sentences are matched by text only.

**The study's label** for a sentence is its Claude-judge first-read M1 label
(`scoring/m1/replies/claude/<item>.json`, `label`; Perplexity `scoring/perplexity/m1/replies/claude/`),
item to sentence by `key_map.json`; UNCITED for a drawn sentence in `uncited.json`; an item with
no reply because no cited source was held counts as COULDN'T CHECK. It is mapped to the four
labels by §3's table.

**Reported:**
- **Agreement**: of the sentences both the study drew and the pilot checked (within its 40), where
  neither label is COULDN'T CHECK, the share with the same label. Also, with its n: agreement
  counting COULDN'T CHECK as a label; agreement on cited sentences only (NO SOURCE left out); and
  the 4x4 table of study label against pilot label.
- **COULDN'T CHECK share**: of all claims the pilot checked (up to 40 per answer, all 8 answers),
  the share labelled COULDN'T CHECK, with the reasons counted (no open licence; not retrieved;
  abstract only; delivery check; refusal; unparsed).
- **Dollars per answer**: ledger spend on `whu-check-pilot` divided by 8, and per answer.

**Pass bar:** all three must hold.
1. Agreement at least 90% on the claims both labelled (the first agreement figure above).
2. COULDN'T CHECK on 20% of claims or fewer.
3. $5 per answer or less (total spend divided by 8).

Failing any of these is a result, not a reason to retune and re-run. The pilot is run once. A
second run is allowed only after a technical failure, logged with evidence first; nothing about
prompts, rules, limits or the sample changes between runs.

**Known expectations, stated before the run.** The open-licence rule will leave many sources
uncheckable (news pages, guideline pages, IPCC and other reports without a Creative Commons
licence; paywalled articles), so condition 2 may well fail; the study judged any held snapshot.
Agreement is measured only where both read the same source, but the study's snapshot and the
pilot's may be different copies (a different route or version).

## 6. Spend

Before any call: a $0 preparation pass (adapt, sentences, licences, snapshots, and
`count_tokens` on every prompt) prints the worst-case estimate, judge_m1's formula (every input
token at the cache-write price plus `CLAUDE_MAX_OUT` output tokens per call). If the estimate is
over $35, the pilot STOPs before any call. Before each call: `spend_ledger.check_cap`
(caps.json's day cap and the issue cap) and the run's `--cap 35` on `whu-check-pilot`; either
over means STOP. No override is used. Calls are metered through `spend_ledger.metered` on issue
`whu-check-pilot`.

## 7. Out of scope

No public endpoint for the pilot, no storage of anyone else's text, no sign-in. The pilot's
inputs are the study's own captures; its outputs stay in the private folder
(`~/Projects/whu-study-private/check_pilot/`), and only counts are committed.

## 8. Code

`study/whu-reliability/check_pilot/`: `pipeline.py` (steps 1-7, importing the study modules by
path), `run_pilot.py` (the sample, the estimate, the run, the comparison), and offline tests in
`backend/tests/test_whu_check_pilot.py` on one recorded answer with recorded sources and a
recorded judge reply.

## 9. v2, written after v1's estimate, before v1 ran

Advisor ruling of 2026-10-28 (Fred approved option B). Written before any v2 code and before v1's
paid run. v1 (§1-§8) is unchanged and runs as frozen; v2 is a separate run.

**Why.** v1's free preparation (2026-10-28) left 240 of its 299 claims COULDN'T CHECK: 225 cite an
address with no PMCID, PMID or DOI in it, so no licence could be read, and 15 cite Frontiers
addresses whose DOI `find_access.ids_from_url` reads with a trailing "/full". The study's helper is
not changed and the study's records stay as they are (§9.5).

**9.1 Identifiers.** The pilot's own copy of the identifier step (`pipeline.ids_v2`) takes
`find_access.ids_from_url`'s result and trims a trailing `/full`, `/abstract`, `/pdf`, `/epdf`,
`/html` or `/fulltext` from the DOI. If the address still yields no identifier:
1. the landing page is fetched (only where §9.3 allows) and a DOI is read from its
   `citation_doi`, `dc.identifier` (or `DC.identifier`) or `prism.doi` meta tag;
2. else a Crossref title lookup (`api.crossref.org/works?query.bibliographic=<title>&rows=1`), with
   the title taken from the answer's own reference entry (the link text of `[title](url)`); the hit
   is accepted only if `find_access.titles_agree` says the titles agree.

**9.2 Licence, for a work with a DOI or PMCID/PMID.** As v1 §3.4: Europe PMC's `license` field,
else an Unpaywall location with a Creative Commons licence. An openly licensed work is snapshotted
as v1 §3.5. A journal work with no open licence stays COULDN'T CHECK ("no open-licence copy").

**9.3 Web pages that are not journal works** (no DOI found by 9.1): fetched where the site's
robots.txt allows it for the snapshot's User-Agent (`snapshot.UA`; `urllib.robotparser`; a robots.txt
that answers 4xx allows, one that cannot be fetched or answers 5xx disallows), by routes (a) and (b),
and judged as v1 §3.6. A page robots.txt disallows is COULDN'T CHECK ("robots.txt disallows").

**9.4 Barred publishers, never fetched** (not the page, not the landing page): Elsevier (DOI prefix
10.1016; hosts sciencedirect.com, elsevier.com, thelancet.com, cell.com); Wiley-hosted works without a
Creative Commons licence (DOI 10.1002 or 10.1111; hosts onlinelibrary.wiley.com, cochranelibrary.com);
SAGE works without a Creative Commons licence (DOI 10.1177; host journals.sagepub.com); NCCN (host
nccn.org). An Elsevier or NCCN work is always COULDN'T CHECK; a Wiley or SAGE work with a Creative
Commons licence is read only from an open copy found by v1 §3.5's route (c). The reason names the bar.
The host test runs before any fetch; the DOI test as soon as a DOI is known.

**9.5 What stays as in v1.** The pipeline's other steps (§3), the labels and their mapping, the
40-claim limit, the Claude judge with M1 v3 on its first read, the test (§5) and the same three bars
(agreement at least 90%; COULDN'T CHECK at most 20%; $5 per answer or less). Failing is a result.

**9.6 Sample.** 8 answers from WHU-S01 to WHU-S04, drawn with
`random.Random("%d/check-pilot-v2" % SEED)` (SEED the freeze commit as a hexadecimal integer, written
in decimal), excluding v1's 8: for each system in the order Claude, ChatGPT, Gemini, Perplexity,
`sorted(rng.sample(<that system's questions not in v1>, 2))`. Each system has four questions and v1
took two, so the draw yields the other two for each system.

**9.7 Spend and order.** `--cap 35` on ledger issue `whu-check-pilot-v2`, run after v1, each run within
caps.json's $25 all-spend day cap (checked before every call, as v1 §6). Estimate printed first; over
$35 means STOP.

**9.8 The preview** (`backend/routers/whu_check.py`) switches to v2 once v2 has run, whatever its
result. The page's banner stays as written.

## 10. v3, written after v2 ran, before any v3 code

Fred's brief for session V (2026-10-29), with his rulings on the sample (§10.8) and the copy rule
(§10.3) given in that session. Written before any v3 code and before v3's estimate. v1 and v2 are
unchanged; v3 is a separate run.

**10.0 Why: v2's 77 "not retrieved" claims, diagnosed ($0).** From v2's results and manifests, plus
one GET per failing host (the request v2 had made) to read the reply. v2's `compare` put every
COULDN'T CHECK reason it did not recognise under "not retrieved", so the 77 include refusals by
rule. By the cause of each claim's failing citation (28 distinct sources; no claim had two causes):

| Cause | Claims | Sources | Example hosts |
|---|---|---|---|
| bot wall / CAPTCHA | 52 | 13 | researchgate.net, ipcc.ch, core.ac.uk (Cloudflare challenge, HTTP 403 `cf-mitigated: challenge`); jmir.org, ore.exeter.ac.uk (AWS WAF challenge, HTTP 202, empty body; Exeter's on robots.txt) |
| barred publisher (Elsevier DOI) | 12 | 7 | doi.org/10.1016/..., onlinelibrary.wiley.com (an Elsevier DOI) |
| HTTP error 403 (no challenge) | 4 | 2 | weiszlab.fas.harvard.edu |
| other: a wrong DOI matched, then barred | 3 | 2 | alert.psychnews.org (an Elsevier DOI), un.org (`10.1111/ele.14238/v1/review1`) |
| other: connection failed | 2 | 1 | core-prod.cambridgecore.org |
| other: CC work whose only open copy was on a barred host | 2 | 1 | researchportal.plymouth.ac.uk (10.1002/cl2.1376) |
| robots.txt disallows | 1 | 1 | facebook.com |
| page needs JavaScript | 1 | 1 | scribd.com (200, 231 readable characters) |
| PDF, timeout, redirect loop | 0 | 0 | - |

Expectation, stated before the run: v3 may not get past a bot wall (§10.3), and a headless browser
does not get past these challenges either, so most of the 52 can be recovered only by an open copy
found elsewhere (§10.3, step 4). Rendering would have recovered 1 claim and PDF extraction none.
The other large v2 cause, "no open licence" (70 claims), is what §10.3's repository rule addresses.

**10.1 Evidence shown.** Every BACKED or NOT BACKED verdict carries the passage the judge relied on:
M1's `span`, found word for word in the text that was judged (`judge_m1.norm`), quoted in under 60
words (a longer span is cut to its first 59 words, marked "..."), with its location (page number
for a PDF, else the nearest heading above it and the paragraph number) and a link (the copy's
address with a `#:~:text=` fragment of the passage's opening and closing words). A verdict whose
span is empty or not found in the text is shown as COULDN'T CHECK ("no passage to show"). The
reader is never shown more of a snapshot than this passage.

**10.2 Labels.** v1's four labels and mapping (§3.7) stand, with two labelled sub-kinds of a verdict:
"checked against the abstract only" (§10.4) and "checked against a passage you supplied" (§10.5).
Each COULDN'T CHECK carries exactly one reason from a fixed list (§10.9).

**10.3 Which copies may be fetched (Fred's rule, 2026-10-29).**
- (a) **Repository copies** (institutional and university repositories, PubMed Central / Europe PMC,
  arXiv and other preprint servers, author pages) may be fetched when free to read, licensed or not.
  A copy is a repository copy if Unpaywall gives its location `host_type: "repository"`, or it is
  Europe PMC's full text, or its host is on the pilot's list of repository and preprint hosts
  (`pipeline_v3.REPOSITORY_HOSTS`, in code, with the host patterns `eprints.`, `repository.`, `ore.`,
  `dspace.`, `researchportal.`, `/handle/`). The study accepted one such copy (WHU-S06, Caulfield,
  Bath Spa repository).
- (b) **A copy on a publisher's own site** (Unpaywall `host_type: "publisher"`, or the cited address
  of a work with a DOI that is not a repository copy) needs a Creative Commons licence (Europe PMC's
  `license` field or the Unpaywall location's `license`). Free to read is not enough.
- (c) **Web pages that are not journal works** (government, agencies, organisations, news), as v2
  §9.3 fetches them.
- (d) **Everywhere:** obey robots.txt for `snapshot.UA` (v2 §9.3's reading); obey any text-and-data-
  mining reservation under W3C TDMRep (a `tdm-reservation: 1` HTTP header, a
  `<meta name="tdm-reservation" content="1">` tag, or a matching entry with `tdm-reservation: 1` in
  the site's `/.well-known/tdmrep.json`); never the barred publishers (v2 §9.4: Elsevier;
  Wiley-hosted without a CC licence; SAGE without a CC licence; NCCN), not the page, the landing
  page, nor a barred work's abstract (§10.4); never past a bot wall, CAPTCHA, paywall or sign-in. A
  reply that is a challenge (HTTP 403 or 202 with a `cf-mitigated: challenge` or
  `x-amzn-waf-action: challenge` header, or a challenge or sign-in page by `snapshot.WALLS` and the
  pilot's own markers) ends that copy: it is not retried, rendered or worked around.
- (e) Snapshots stay private (`~/Projects/whu-study-private/check_pilot_v3/`) and are never
  republished; a reader sees only the passage (§10.1).

Each held copy records which of (a), (b), (c) admitted it. **Order** for one cited address:
1. Host bar (v2 §9.4), before any request.
2. Identifiers as v2 §9.1, but a DOI found from a landing page's meta tags or a Crossref title lookup
   is used only if Crossref's record for it has a title `find_access.titles_agree` accepts against the
   answer's own title for the link (v2 matched two unrelated pages to barred DOIs); where the answer
   gives no title, against the page's own `citation_title` (else its `<title>`) for a meta-tag DOI,
   and a Crossref title lookup is not made. (Amended 2026-10-30, before any v3 code: ChatGPT and
   Perplexity references often carry no title.) A DOI read from the address itself is used as is.
   The DOI bar applies as soon as a DOI is accepted.
3. The cited address, if (a), (b) or (c) admits it and (d) allows it: plain fetch (routes (a), (b));
   a PDF's text by `snapshot`'s pdftotext. If the reply is HTML with too little readable text
   (`snapshot.extent` "N readable characters") and is not a challenge, it is rendered once in headless
   Chromium (Playwright), where robots.txt allows, with no cookies, no sign-in, no clicks and a 20 s
   limit, and the rendered text is judged as the plain fetch's would be.
4. If that yields no full text: an open copy of the same work, by DOI, PMID or PMCID, else by title
   (Crossref, checked by `titles_agree`): Europe PMC full text, then Unpaywall locations, each
   admitted by (a) or (b) and allowed by (d).
5. Else the abstract (§10.4). Else COULDN'T CHECK with the reason of the step that ended it.

**10.4 Abstract fallback.** When no full text is held, the work's abstract from Europe PMC
(`abstractText`) or Crossref (`abstract`), by its identifier, is judged; the verdict is labelled
"checked against the abstract only" and counted separately. As in the study, "Absent" on an abstract
is COULDN'T CHECK ("only the abstract could be read, and it does not state this";
`judge_m1.NOT_VERIFIABLE_ABSTRACT`). Not for a barred publisher's work.

**10.5 A passage the user supplies.** For a COULDN'T CHECK claim the user may paste a passage (at most
300 words) and its source link. The claim is judged against that passage only (M1, Claude, first
read), labelled "checked against a passage you supplied", with the notice "Paste only text you have
the right to use." The passage is not written to disk, the job log or the ledger. It is not part of
the pilot's run (no study answer has one); it is built and tested offline only.

**10.6 Which claims are checked.** Claim-like sentences (v1 §3.2) are ranked: those stating a number,
then a cause and effect, then a conclusion, then the rest, in the answer's order within each rank
(`pipeline_v3.claim_rank`, word lists in code). The first 40 are checked unless the caller passes
the sentences the user ticked, which are checked instead (still at most 40). A summary line comes
first: claims checked of claim-like sentences found, and the count per label and sub-kind.

**10.7 The test.** As v1 §5, with the study's labels from the sample's own scoring (§10.8), and:
- **Agreement**: of sentences the study drew and the pilot checked where both labels are BACKED or
  NOT BACKED (both judged), the share that agree. v1's figure (NO SOURCE pairs included) and the 4x4
  table are reported too. Abstract-only and supplied-passage verdicts count as judged.
- **COULDN'T CHECK share**: of all claims checked, as v1, by reason (§10.9); abstract-only verdicts are
  reported separately and are not COULDN'T CHECK.
- **Passages**: the share of BACKED / NOT BACKED verdicts carrying a passage (by §10.1 it is 100%
  unless the code is wrong; it is counted, not assumed).
- **Dollars per answer** (ledger) and **seconds per answer** (wall clock from reading the answer to
  the last verdict, each answer, mean and max).

**Pass bars, fixed here; all must hold.** 1. COULDN'T CHECK at most 20% of claims checked.
2. Agreement at least 90% on claims both judged. 3. At most $2 per answer (spend / 8). 4. At most
120 s per answer on average. 5. 100% of BACKED / NOT BACKED verdicts carry a passage. Failing a bar
is a result, not a reason to retune and re-run (v1 §5's rule on re-runs stands).

**10.8 Sample (Fred's ruling, 2026-10-29).**
- **Primary (the bars apply to it):** 8 tool answers from quarterly round 1, fresh to the pilot: 3
  Claude, 3 Perplexity, 2 Gemini. ChatGPT is left out (its round-1 answers cite nothing; 0
  searches). Draw: `rng = random.Random("%d/check-pilot-v3" % SEED)`, SEED round 1's freeze commit
  `5f4a928b757d7f47c1ba8ed47600ced4a7a69f12` read as a hexadecimal integer, written in decimal; for
  each system in the order Claude, Perplexity, Gemini: `sorted(rng.sample(<its round-1 questions>,
  k))`, k = 3, 3, 2, one generator; Gemini's questions are WHU-Q1-01 to -03 (no Q1-04 answer,
  `prepare_round1.NO_ANSWER`). Inputs: the round-1 captures read as `prepare_round1.tool_answer` reads
  them (Claude `claude_sources_r1`; Perplexity `perplexity_sources` for Q1-03/-04 and
  `perplexity_footnotes` for Q1-01/-02; Gemini `report_section` + `works_cited`). Study labels: round
  1's Claude-judge first reads, `~/Projects/whu-study-private/scoring/quarterly/round1/m1/replies/claude/`
  (not `replies_repeat`, not the superseded folders), items by its `key_map.json`, `uncited.json`, and
  sentences from `blinded/<q>/<system>.sentences.jsonl`.
- **Secondary (reported separately, not judged against the bars):** v3 on v2's same 8 answers (§9.6),
  to show v2 against v3 on identical input.

**10.9 COULDN'T CHECK reasons, counted by name.** barred publisher; robots.txt disallows; TDM
reservation; bot wall or CAPTCHA; sign-in or paywall; publisher copy without licence; no copy found;
HTTP error (code); connection failed or timed out; abstract does not state it; delivery check; no
passage to show; refused; unparsed; marker outside the reference list.

**10.10 Spend and order.** Ledger issue `whu-check-pilot-v3`, `--cap 35` for both runs together, within
caps.json's $25 all-spend day cap (checked before every call, as v1 §6). A free preparation pass
prints the worst-case estimate for each run (judge_m1's formula). If primary plus secondary is over
$35, only the primary runs; if the primary alone is over, nothing runs. Primary first.

**10.11 Code.** `study/whu-reliability/check_pilot/pipeline_v3.py` (imports v1 and v2 unchanged; judge
prompt only through `judge_m1`), `run_pilot_v3.py`; offline tests on recorded fixtures in
`backend/tests/test_whu_check_pilot_v3.py`. Counts only are committed (`pilot_v3_counts.json`,
`pilot_v3_secondary_counts.json`). The preview (`routers/whu_check.py`) is not switched to v3 until
Fred says so.

**10.12 Out of scope for this pilot: a public launch.** Before one: a durable spend cap (not the
per-instance ledger; see the KNOWN LIMIT in CLAUDE.md), per-visitor limits, and the validity checks.

**10.13 Implementation notes (written with the code, before the estimate or any run).** Two readings of
§10.3 step 2 that the text left open, both taken the cautious way: (1) a page carrying a `citation_doi`
that its title does not confirm is still a journal page; its licence cannot be read, so it is not used
("publisher copy without licence"), not read as a web page under (c). (2) The Crossref title lookup is
made only when the cited page itself could not be read; a page that was read and names no DOI is a web
page under (c), so a loose title match (v2 gave a UN report a journal's DOI) cannot turn it into a
journal work. Headless rendering is Playwright 1.64.1's Chromium headless shell.

**10.14 Free preparation passes, 2026-10-30 (no model call; $0 on `whu-check-pilot-v3`).**
1. Technical failure: an answer whose first source had a DOI reached `find_access` (urllib, the macOS
   system-proxy lookup) before `snapshot` was imported to set `no_proxy`, so every later child process
   died: pdftotext read PDFs as empty and Playwright's driver crashed. Fixed by setting `no_proxy` when
   `pipeline_v3` is imported. Outputs deleted.
2. **Rule breach in the code, found before any run:** three kinds of challenge page served with HTTP 200
   ("Client Challenge" at link.springer.com and BMC; "Checking your browser - reCAPTCHA" at NCBI
   Bookshelf; "Validating your request" at digital.library.unt.edu) were not recognised and were sent to
   headless rendering, against §10.3 (d). Detection widened (markers, and pages up to 100 kB); the three
   pages are recorded as test fixtures (`backend/tests/fixtures/whu_check/v3_walls/`) and are now walls,
   never rendered. Every snapshot from that pass was deleted; nothing from it was judged or kept.
3. Clean pass: two pages are rendered (an ArcGIS StoryMap; Wellcome Open Research's article app), no
   challenge page. Estimate (judge_m1's worst-case formula): **primary $44.32**, secondary $26.40.
   **Under §10.10 the primary alone is over the $35 cap, so nothing ran.** (For scale only: v2's actual
   spend was 66% of its worst case, $12.18 of $18.55.) Any run now needs Fred's decision on the cap or
   the design; per v1 §5, the sample, bars and rules are not retuned to fit.

**10.15 Fred's rulings of 2026-10-30, written before the paid run.** (1) The primary sample only runs,
with `--cap 45` on `whu-check-pilot-v3` (Fred approved the extra $10), within caps.json's $25 day cap.
**The secondary sample (v2's 8, §10.8) is dropped, for budget.** The bars (§10.7) stay as written,
including $2 per answer. (2) The rendering slip (§10.14.2) stays logged; a test asserts that an HTTP-200
page carrying any of the three challenge signatures seen is a wall and is never rendered.

**10.16 Result (primary, 8 answers; `check_pilot/pilot_v3_counts.json`).** Run 2026-10-30: 7 answers, then a stop
at the $25 day cap before Gemini Q1-03's first call (no spend lost); Fred raised the day cap to $40 for that one
answer (committed af31017, reverted b7e3d3b straight after). Total $37.36. **Fails** (2 of 5 bars):
COULDN'T CHECK 64 of 295 = 21.7% (bar 20%): bot wall or CAPTCHA 34, delivery check 15, barred publisher 4,
publisher copy without licence 3, robots.txt 3, no passage to show 3, HTTP error 2, TDM reservation 0; abstract
only 11, counted apart. Cost $4.67 per answer (bar $2). **Passes:** agreement 46 of 47 = 97.9% (abstract-only
3 of 3; v1's rule 77 of 78); mean 52 s per answer (max 104 s); passages on 124 of 124 verdicts. Per v1 §5 this is
the result; nothing is retuned.

## 11. v4: lean WHU's passage retrieval (code only; nothing run)

Built 2026-10-30 by session LW (plan doc "WHU next phase: validity checks and a leaner WHU", Part B
item 1). `check_pilot/pipeline_v4.py` imports v1-v3 unchanged and does everything v3 does; only what
the judge reads differs. In place of the whole cited source (judge_m1.chunk past MAX_SOURCE_TOKENS) the
judge gets the `TOP_K` = 6 passages BM25 finds for the claim (`backend/scripts/whatholdsup/passage_index.py`,
shared with lean WHU's audit), topped up with the best passage for each key term of the claim the source
holds but those passages miss, so `judge_m1.delivery_problems` still holds. When retrieval finds nothing
above its threshold the claim is COULDN'T CHECK with the reason "no relevant passage", logged; the whole
source is never sent. The passage shown to a reader (§10.1) is located in the full held text. Offline
tests: `backend/tests/test_whu_check_pilot_v4.py`. Not run (no paid call), not wired into the preview
(`routers/whu_check.py` stays on v2; a test pins it).

**11.1 v4 run, written 2026-10-30 before any v4 call (session VP; plan doc "WHU next phase", step 1 of
Fred's brief for this phase).**
- **Input: the same 8 round-1 answers v3 used** (§10.8's primary draw: Claude Q1-01, Q1-02, Q1-04;
  Perplexity Q1-01, Q1-03, Q1-04; Gemini Q1-01, Q1-03). **This is not a fresh sample:** it is a
  side-by-side of v3 and v4 on identical input, so it can say what v4's retrieval changes, not how v4
  does on answers it has not seen. The claims are v3's (same adapter, same ranking, at most 40), and
  the copies are the ones v3 held: v3's private manifest and source texts are copied into v4's run
  folder and **nothing is re-fetched**, so only what the judge reads differs. Consequence, stated
  before the run: every COULDN'T CHECK that v3 gave for a copy reason (bot wall, barred publisher,
  robots.txt, licence, HTTP error) is carried over unchanged by construction; v4 can change only
  claims v3 judged or stopped at the delivery check, no passage to show or the abstract, and it adds
  one reason, "no relevant passage" (§11).
- **Bars: §10.7's five, unchanged** (COULDN'T CHECK at most 20%; agreement at least 90% on claims both
  judged, against round 1's Claude-judge first reads as in §10.8; at most $2 per answer; at most 120 s
  per answer on average; 100% of BACKED / NOT BACKED verdicts carry a passage). Seconds: because v4
  re-uses v3's copies, its wall clock leaves out fetching. It is reported as measured, and the 120 s
  bar is applied to that figure plus v3's fetch time for the same answer, reconstructed from v3's
  manifest (per-copy seconds summed per host, the slowest host taken, as `snapshots_v3` fetches hosts
  in parallel), labelled an estimate.
- **Judge: as built,** `judge_m1` (M1 v3 prompt, first read) on `claude-opus-5-5`; code as committed at
  `1a3a868` (`pipeline_v4.py`, `passage_index.py`; TOP_K 6). Runner: `check_pilot/run_pilot_v4.py`
  (prepare | run --cap | compare).
- **Spend:** ledger issue `whu-check-pilot-v4`, `--cap 10`, within caps.json's $25 all-spend day cap
  (checked before every call; never overridden). A free prepare prints judge_m1's worst-case estimate
  first; if it is over $10 nothing runs. Part of the phase's $350 approval.
- **Reported, v3 and v4 side by side:** each bar; COULDN'T CHECK by reason; dollars and seconds per
  answer; passages shown; the claim-by-claim table v3 label -> v4 label; and **how many of v3's 15
  "delivery check" claims v4 cleared**, where cleared means v4 gave BACKED or NOT BACKED with a passage
  shown, with each cleared claim's agreement with the study label where the study drew it.
- Counts only are committed (`check_pilot/pilot_v4_counts.json`); outputs stay private
  (`~/Projects/whu-study-private/check_pilot_v4/`). **The preview stays on v2.** As v1 §5: failing a bar
  is a result, not a reason to retune and re-run.

**11.2 v4 result (the same 8 answers and v3's held copies; `check_pilot/pilot_v4_counts.json`).** Run 2026-10-30
under the raised day cap (caps.json `default_per_day` 60, `e454d9f`); $3.03 on `whu-check-pilot-v4` (worst case
$7.92). **Fails** (1 of 5 bars), v3 beside it:

| Bar | v3 | v4 |
|---|---|---|
| COULDN'T CHECK ≤ 20% | 64/295 = 21.7% FAIL | 53/295 = 18.0% pass |
| Agreement ≥ 90% (both judged) | 46/47 = 97.9% pass | **40/48 = 83.3% FAIL** |
| ≤ $2 per answer | $4.67 FAIL | $0.38 pass |
| ≤ 120 s per answer (mean) | 52 s pass | 13.5 s measured, no fetch; 31 s with v3's fetch time added (estimate) pass |
| Passages on every verdict | 124/124 pass | 135/135 pass |

COULDN'T CHECK by reason, v3 -> v4: bot wall 34 -> 33; delivery check 15 -> 0; no relevant passage (new) 0 -> 6;
barred publisher 4 -> 4; publisher copy without licence 3 -> 3; robots.txt 3 -> 3; no passage to show 3 -> 1; HTTP
error 2 -> 2; unparsed 0 -> 1. The one bot-wall claim that changed name cites two sources, one walled and one where
retrieval found nothing; `judge_v4` names "no relevant passage" whenever it appears in the reason, so the claim is
COULDN'T CHECK either way (a naming quirk, logged; no copy was re-fetched).

**Delivery check: v4 cleared 13 of v3's 15** (3 BACKED, 10 NOT BACKED, each with a passage); 2 stay COULDN'T CHECK
(no relevant passage 1, no passage to show 1). None of the 13 has a study verdict to compare (the study had them
as COULDN'T CHECK or did not draw them), so whether they are right is not known from this run.

**Why agreement fell.** v3 -> v4 on the same claims: 56 BACKED stayed BACKED, **21 BACKED became NOT BACKED**, 2 NOT
BACKED became BACKED. Of the 8 disagreements with the study, 7 are study BACKED -> v4 NOT BACKED; in 5 the judge said
"Absent", saying the text it was shown lacks the point (e.g. "the visible text does not give certainty grades"),
where v3 and the study, reading the whole source, found it. Retrieval (BM25 top 6, topped up by key term) missed
the supporting passage: a false NOT BACKED, the costliest error for a reader. The same retrieval module feeds lean
WHU's audit, where a sentence's bound passage is always sent too; the seeded-defect test's false-alarm count
(validity plan §9) is where that shows. Per v1 §5 this is the result; nothing is retuned. The preview stays on v2.
