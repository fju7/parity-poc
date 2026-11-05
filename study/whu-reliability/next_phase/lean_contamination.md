# Lean test: contamination check, per drafting subagent

Advisor rulings of 2026-11-05 (`deviations.md`). Source: the harness's transcript of each subagent (every tool
call's input and result), read by `lean_contamination_scan.py` (offline tests:
`test_lean_contamination_scan.py`). The full per-call listing and the deduplicated path list (`paths-q1-0n.tsv`) are
kept privately at `~/Projects/whu-study-private/lean/session_lt/contam/`, because they name source files and the
scratchpad. This file holds the counts, every flag and the judgement on each.

**Invalid if** the drafter printed CONTENT (not only names) from another issue's folder (advisor ruling, 2026-11-05; a names-only listing is a breach, ruled case by case); or opened anything under `issues/WHU-Q1-0*`, any round-1 or study results, scoring or keys
folders, `~/Projects/whu-study-private` (other than its own archive folder), or another system's answer (NAMED);
or ran a command whose scope took in one of these without naming it, unless its scope provably excluded them
(BROAD); or read the scratchpad's former contents (SCRATCH). OTHER-ISSUE (another issue's case folder, which the
brief forbids but the invalidation list does not name) and OUTPUT (a tool result that mentions a forbidden
location) are reported and judged by hand.

## WHU-Q1-01 (whu-lean-q1-01)

**Final scan, all 148 tool calls (02:05-02:40Z): VALID.** No NAMED read, no SCRATCH, no CONTENT from another issue's folder. Every BROAD flag is the brief's `git diff --cached --name-only` (02:14:24, 02:14:33, 02:33:54, 02:34:09, 02:37:41; each output names only `issues/WHU-L1-01-whu-lean-q1-01/` files) or, at 02:21:56, a false match on the word "git" inside study-log text the drafter was writing. The drafter's shell started in LT's working directory (`study/whu-reliability/next_phase/`, which is forbidden). Every one of its Bash calls but one begins with an absolute `cd` into the repo or scratchpad, and that one (02:07:54) works in the scratchpad by absolute path, so no relative path resolved inside `next_phase/`. LT now starts each drafter from the repo root.

| Time (UTC) | Flag | Exact text (relevant part) | Judgement |
|---|---|---|---|
| 02:05:36 | OUTPUT | `git status --short \| head -20` | Names only: the working tree's modified `issues/WHU-Q1-0*/sweeps.json` files (other sessions' changes) appear in the listing. No file opened. Benign. |
| 02:05:42 | OUTPUT | `cat issues/WHU-L1-01-whu-lean-q1-01/issue.json` | Its own issue.json, which the brief requires; its `_round_note` (LT's text) names "WHU-Q1-01" and `validity_plan.md`. Benign. |
| 02:05:59 | OUTPUT | Read of the harness's saved output of `CLAUDE.md` | CLAUDE.md is required reading. It names study paths and the lean section's fixture (names and counts only; known limit, deviations 2026-11-05). Benign. |
| 02:06:07 | OUTPUT | `sed -n 1,366p docs/whatholdsup-process.md` | Required reading (§0-§5, §4.5, §4.6, §4.6.1); §4.6.1 names round 1 and the test file. Benign. |
| 02:07:11 | NAMED | writes `premise.json`: `d['lead_came_from']="Lean four-question test: round 1's question WHU-Q1-01, asked again verbatim (issue.json)."` | A write, not a read. The phrase comes from LT's text in its own issue.json, `_round_note`: "round 1's question WHU-Q1-01, verbatim, asked again of lean WHU", and from its brief: "It is a lean-test question (round 1's question, asked again of lean WHU)". Benign. |
| 02:08:43 | OTHER-ISSUE | `grep -l '"licence"' issues/WHU-S0*/sources.json \| head -2` (with `ls issues/ \| grep -v 'WHU-Q1\|WHU-L1' \| head -3`) | **A breach of the brief** ("Any other issue's case folder"): grep read two study issues' sources.json files (WHU-S07r, WHU-S08) and printed **their file names only** (`-l`). No content was shown. `WHU-S*` is not in the advisor's invalidation list. **Advisor ruling (2026-11-05): not invalidating** (two file names, no content; a field's format revealed, no source or finding; WHU-S07r and WHU-S08 are unrelated to Q1-01's topic). Recorded as a breach of the brief, with no information relevant to the answer transferred. Scanner kind: names-only. |
| 02:08:43 | BROAD (first scan; withdrawn) | `grep -rn 'publisher terms\|PUBLISHER\|BARRED' backend/scripts/whatholdsup/*.py` | Scope `backend/scripts/whatholdsup/*.py`, which holds no forbidden folder. The first scan flagged it because the splitter cut the command at the quoted `\|`. Fixed (quote-aware splitting), and the exact command added to the tests as narrow. |
| 02:14:24, 02:14:33 | BROAD | `git diff --cached --name-only` (the brief's pre-commit check) | Prints staged file names only. The outputs list only `issues/WHU-L1-01-whu-lean-q1-01/` files. Scope provably excluded. Benign. |

SCRATCH: 0. The drafter never listed the scratchpad and never read or named LT's former files there.
| 02:08:26 | (not a read) | `curl -sL -A 'Mozilla/5.0 … Chrome/125 Safari/537.36' 'https://iris.who.int/bitstream/handle/10665/311941/9789241550505-eng.pdf'` | **Attempted bot-check circumvention** (a browser user agent after iris.who.int answered the PDF address with an HTML page), against the brief's "never get past a … bot wall". Refused by the harness's classifier [Bot Check Circumvention], so nothing was fetched. The WHO guideline was then left out of the answer. Not contamination; reported. |

## WHU-Q1-02 (whu-lean-q1-02)

**Final scan, all 146 tool calls (02:45-03:20Z): VALID.** No NAMED read, no SCRATCH, no OTHER-ISSUE call. Of the BROAD flags, 4 are the brief's `git diff --cached --name-only` (outputs name only `issues/WHU-L1-02-whu-lean-q1-02/` files), and 1 is `find $DEST -type f` over its own new archive folder (`~/Projects/whu-study-private/WHU-L1-02-whu-lean-q1-02/<stamp>/`, allowed for step 11). The other 3 are false matches on words ("find", "There", "ruled:") inside heredoc text it was writing. The 2 NAMED flags are its own premise text naming WHU-Q1-02, written from its issue.json, and its own archive folder. OUTPUT mentions come from the required files (CLAUDE.md, the process doc, its issue.json) and from `git status`. Web calls: 1 WebSearch (inclusive education, general) and 1 WebFetch (worldbank.org, a 2026 results page); neither is another system's answer. Outside its folder: it edited its own issue's library record `backend/data/whatholdsup/library/issues/whu-lean-q1-02.json` (untracked, not committed) to drop S002. This is the tools' own store for its issue, recorded and not a read of another issue.
