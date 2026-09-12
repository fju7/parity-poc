# Ruling — the watch is internal; the page promises nothing

**Operator ruling, 12 September 2026, Fred Ugast.** Recorded here because
deskilling is the only living issue, so the rule being withdrawn was in force on
this page and nowhere else. It applies to every issue.

**A rule is being WITHDRAWN by ruling. No check is being weakened because it was
inconvenient, and nothing is waived.** Every code change that follows cites
this file.

---

## The rule withdrawn

`watch.py` enforced, and its docstring argued for at length:

> THE PAGE DISPLAYS THE DATE OF THE LAST CHECK, NOT THE LAST CHANGE.

with a blocking preflight row, `page says when it was last reviewed`, that
refused to publish a living issue unless the page carried "Last reviewed
<date>" and that date matched the last recorded check in `watch.json`. The
same rule was asserted in `watch.json`'s `the_promise` field and in the
`publish.py update` docstring. All three are retired.

## The reason

What Holds Up makes only the **modest promise**: we read these documents and
this is what they said, as of a stated date. It does not promise currency,
because we cannot be sure that promise is true. A "Last reviewed" date on a
page is a currency claim — it tells a reader somebody looked recently and found
nothing — and the only thing that could make it honest is a watch that runs on
its own, on time, every time, against every question. No such watch exists
here, and a check that the page's date matches the register's date verifies
that two records agree with each other, not that anybody looked at the world.

The danger the old rule guarded against was real: a page with a changelog
reads as current, and a stale page that reads as current is an unrun check
reported as a pass, in public. The old remedy was to make the freshness claim
checkable. The remedy now is not to make the claim at all.

## What replaces it

- **`watch.json` stays**, as the internal register of what we are watching for.
  The watch runs for us. What it finds is recorded there and, where the page
  changes, in the changelog. It is an instrument for our own attention, not a
  promise to anyone else.
- **The page states a bound and claims nothing beyond it.** The evidence
  "as of" date says when the claims were last checked against the record.
  That date moves when we check again, not when we edit the prose, and it is
  never compared to today. (The wording of the bound on each page is a
  separate editorial change and is not made by this ruling.)
- **What blocks is contradiction, never age.** "Nobody has looked lately" is
  Class 3 — nothing has checked this yet — and the standing rule is that
  Class 3 does not block. The row that carries the weight now is
  `registry claims match the registry`, which fires when a captured registry
  state disagrees with a printed sentence, and the citation and registry
  sweeps that feed it.

## The one judgement call, which the operator may reverse

`watch has been run` was BAD past twice the review interval and BAD when no
check had ever been recorded. **It is demoted to WARN in both cases.** The
reasoning: with the page making no currency claim, "nobody has looked lately"
no longer makes anything on the page false; it is Class 3, and Class 3 does not
block. The row keeps its exact text, keeps printing the day count and the
interval, and stays counted, so that it cannot become invisible. The
never-checked message loses only the clause "the page is about to promise a
reader it is current", which is no longer true; it now says that no check has
ever been recorded, and nothing more.

If the operator would rather a living issue that nobody has checked for two
intervals could not be republished at all, that is a one-line reversal in
`watch.py` and this section is where the argument for it lives.

## Unchanged, deliberately

The three rows about the register's own integrity keep their severities:

- `living issue — open questions` — BAD: a watch that watches nothing.
- `changelog entries bound to a sha` — BAD: `watch.json`'s own changelog array.
- `changelog is not the correction history` — BAD: the two-histories rule.

None of them is about what the page tells a reader. The two-histories rule
(`corrections.md`: WE WERE WRONG; `changelog.md`: THE EVIDENCE MOVED) and the
kill-conditions rule are untouched by this ruling.

## Effected by

- `backend/scripts/whatholdsup/watch.py` — row, regex and scanner deleted;
  docstring rewritten; `watch has been run` demoted; the `init` template and
  the `check` command's closing line no longer instruct anyone to print a
  review date.
- `backend/scripts/whatholdsup/publish.py` — the `update` docstring; the
  `evidence 'as of'` row no longer compares the date to today.
- `issues/WHU-003-deskilling/watch.json` — `the_promise`.
- `backend/tests/test_whatholdsup_watch.py` — the retired rule stays retired.
