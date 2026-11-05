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

## WHU-Q1-02r (whu-lean-q1-02r): the re-run, fresh drafter, frozen code 4abcab6

**Final scan, `--rerun 02` (the earlier attempt's case folder, private archive and library record count as NAMED), all 181 tool calls (12:39-13:23Z): VALID.** No read of the earlier attempt, no SCRATCH read, no OTHER-ISSUE call, no CONTENT from another issue's folder. Flags: NAMED 1, BROAD 4, OUTPUT 5.
- **NAMED (1):** a write, not a read. The drafter's own premise text, `lead_came_from` = "the lean four-question test: round 1's question WHU-Q1-02, asked again (issue.json)", taken from its issue.json. Benign.
- **BROAD (4):** three are the brief's pre-commit check (`git add issues/WHU-L1-02r-whu-lean-q1-02r/ && git diff --cached --name-only`), whose outputs name only its own files; its three commits 3464a5d, f41a303 and b2b75d5 touch only `issues/WHU-L1-02r-whu-lean-q1-02r/`. One is a false match on `**Ready.**` inside study-log text, beside a `git ls-files --others --ignored -- issues/WHU-L1-02r…` scoped to its own folder. Scope provably excluded. Benign.
- **OUTPUT (5):** mentions in the files the brief requires: `git status` (other sessions' modified files, names only), CLAUDE.md, the process doc and its own publish.py output naming its own private archive. Benign.

Outside its folder, the drafter edited `backend/data/whatholdsup/library/index.json` to drop S002 from this issue's entry (uncommitted, as the brief requires). This is the tools' store for its own issue, not a read of another issue. Its scratchpad files (pre-edit copies, the audit dry run, commit logs) are archived at `~/Projects/whu-study-private/lean/session_lt/scratch_after_q1-02r/`, and the scratchpad is empty again.

## WHU-Q1-03 (whu-lean-q1-03): fresh drafter, frozen code fab2b3e

**Final scan, all 234 tool calls (13:32-15:19Z): VALID.** No read of round 1's Q1-03 records, no SCRATCH read, no OTHER-ISSUE call, no CONTENT from another issue's folder, no FORBIDDEN path. Flags: NAMED 1, BROAD 6, OUTPUT 4.
- **NAMED (1):** a write, not a read: its own premise text, `lead_came_from` = "…WHU-Q1-03, asked again of lean WHU (issue.json)". Benign.
- **BROAD (6):**
  - A `find backend -name caps.json` fallback that never ran (the `cat` before it succeeded; output: caps.json only).
  - A `find issues` inside its own private-archive folder.
  - The brief's pre-commit `git diff --cached --name-only` checks (three).
  - A false match on a `**` inside study-log text.
  - Its commits 8762d4c, e2f2d25 and a4b9996 touch only `issues/WHU-L1-03-whu-lean-q1-03/`.

  Benign.
- **OUTPUT (4):** `git status` (other sessions' modified files, names only), the process doc, its own first command's saved output, and its own private-archive path. Benign.

It also read the ledger totals for the other lean issues (whu-lean-q1-01, -02, -04), which is spend only, for the room rule. Its scratchpad is archived at `~/Projects/whu-study-private/lean/session_lt/scratch_after_q1-03/` (58 files, checked identical), and the scratchpad is empty again. The scan output is at `…/session_lt/contam/scan-q1-03.txt` and `paths-q1-03.tsv`.

## WHU-Q1-04 (whu-lean-q1-04)

**Final scan, all 196 tool calls (18:58:49-20:02Z): VALID.** The drafter was restarted after the machine restart in a new LT session, so its scratchpad is a new folder (empty at the start). It was scanned with a private copy of `lean_contamination_scan.py` that differs only in `SCRATCH` (this session's scratchpad) and `CLEANED` (18:58:00Z). Copy, listing and path list: `contam/scan_q104_session.py`, `scan-q1-04.txt`, `paths-q1-04.tsv`. Flags: NAMED 1, BROAD 7, SCRATCH 0, OTHER-ISSUE 0, OUTPUT 8; no path in the path list is FORBIDDEN.

| Time (UTC) | Flag | Exact text (relevant part) | Judgement |
|---|---|---|---|
| 19:17:43 | NAMED | writes `premise.json`: `d['lead_came_from']="The lean four-question test's question (round 1's WHU-Q1-04, asked again)."` | A write, not a read; the words come from its own issue.json `_round_note` and its brief (as Q1-01). Benign. |
| 19:06:01, 19:34:36, 19:45:08, 19:59:58 | BROAD | `git diff --cached --name-only` (the brief's pre-commit check), `git log --oneline -1` | File names / one log line only. Each output lists only `issues/WHU-L1-04-whu-lean-q1-04/` files. Benign. |
| 19:08:49, 19:44:20 | BROAD | Python text in heredocs: `def find(prefix):`, a comment `# find the declaration…`; `git diff --quiet HEAD -- issues/WHU-L1-04-whu-lean-q1-04/coverage.json` | False matches (a function name, a comment) and a git diff with its own pathspec. Benign. |
| 19:59:52 | BROAD | `(cd "$DEST" && find . -type f \| wc -l)` | `$DEST` is its own new archive folder `~/Projects/whu-study-private/WHU-L1-04-whu-lean-q1-04/20261105T195953Z/` (OWN). Benign. |
| 18:58:49 | OUTPUT | `git status --short \| head -20` | Names only: other sessions' modified `issues/WHU-Q1-0*/sweeps.json`. Benign. |
| 18:58:52 | OUTPUT | `cat issues/WHU-L1-04-whu-lean-q1-04/issue.json` | Its own issue.json (`_round_note` names study paths). Required. Benign. |
| 18:59:04, 18:59:10 | OUTPUT | CLAUDE.md sections; `docs/whatholdsup-process.md` | Required reading. Benign. |
| 19:14:13, 19:22:00, 19:48:19 | OUTPUT | harness note "Session cwd remains …/study/whu-reliability/next_phase" on backgrounded commands | The harness reports LT's working directory. Every drafter command either starts with an absolute `cd` into the repo or the scratchpad, or uses absolute paths, or (from 19:53:28) uses repo-relative paths that resolved at the repo root (each succeeded; `next_phase/` holds no `issues/` or `backend/`). No file under `study/` was opened. Benign. |
| 20:02:25 | OUTPUT | its final report names its own archive folder | OWN. Benign. |

## WHU-Q1-01b (whu-lean-q1-01b, second freeze)

**Final scan, all 119 tool calls (20:50-21:15Z): VALID.** `lean_contamination_scan.py --rerun-b 01 --scratch <this session's scratchpad> --cleaned 2026-11-05T20:49:00`. Flags: NAMED 2, BROAD 5, SCRATCH 0, OTHER-ISSUE 0, OUTPUT 4; no FORBIDDEN path. NAMED: two writes (premise.json `lead_came_from`, the study log) whose words "WHU-Q1-01" come from its own issue.json and brief. Benign. BROAD: the brief's `git diff --cached --name-only` and `git log --oneline -1` (three commits), and `find .` in its own new archive folder. Also `cat backend/data/spend/caps.json 2>/dev/null || find backend -name caps.json`: the find runs only if the cat fails, and prints only paths of files named caps.json. Benign. OUTPUT: git status names, its issue.json, CLAUDE.md and the process doc (required reading). Benign. Listing: `contam/scan-q1-01b.txt`, `paths-q1-01b.tsv`.
