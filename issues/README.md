# Case files

One folder per issue, named by a permanent ID that never changes. Slugs and
headlines change; `WHU-001` does not, and it is what every other record keys on.

## What is canonical where

The point of this folder is the evidence trail. It is **not** a second copy of
records that already exist — two records of one fact that can disagree is the
failure this project keeps hitting, and adding more of them would be a strange
lesson to draw from it.

| Fact | Canonical home | Why there |
|---|---|---|
| The published assessment | `site/whatholdsup/<slug>.html` | It is the artefact. A Markdown copy would drift from the page. |
| Gate findings and our adjudication of them | `backend/tests/fixtures/draft_decisions.json` | The gate reads it at run time to tell a repeat from a new problem. |
| Recorded error classes | `backend/tests/fixtures/factcheck_known_errors.json` | Fed into the role prompts. Cross-issue by nature. |
| What was published and sent, and when | `backend/data/whatholdsup/published.json` | Written by `publish.py`, append-only. |
| That an outside review happened | `backend/data/whatholdsup/reviews.json` | Read by the `publish.py` preflight, which blocks without it. |
| **Exactly what the reviewer read** | **here**, `review/*-sent.html` | A hash proves the version differed; only the bytes say what it said. |
| **The review, verbatim** | **here**, `review/*-review.md` | Immutable. Never edited after the fact, including by us. |
| **Our dispositions, finding by finding** | **here**, `review/*-adjudication.md` | Sits beside the review rather than inside it, so the record cannot get muddled. |
| **The source register** | **here**, `sources.json` | Typed sources make rule 11 auditable: you can see whether we looked for the best coverage or only the worst. |
| **Issue metadata** | **here**, `issue.json` | Machine-readable, so the register, a dashboard and the site can read the collection without parsing prose. |

`issue-register.csv` at the repo root is **generated** from the `issue.json`
files by `publish.py register`. Do not edit it by hand; a hand-maintained
register is wrong by the fifth issue and nobody notices which row.

## Three histories, kept apart

1. **Draft history** — ordinary writing changes before publication. Git.
2. **Review and adjudication history** — what was challenged during quality
   control and what we did about it. This folder.
3. **Public correction history** — substantive changes *after* publication.
   `corrections.md` here, mirrored into the page footer, which is the only one
   of the three a reader sees. That is rule 10.

## Standards are versioned

A review means "reviewed against the standard as it stood that day". When rule 7
is refined or a twelfth rule is added, an old review must not silently acquire
today's standard. `issue.json` records `standards_version` and every review
records the version it was conducted under.

## JSON, not YAML

The reviewer who proposed this structure suggested YAML, which is nicer to edit
by hand. Everything else we keep is JSON, `publish.py` already reads JSON in
four places, and YAML would add a dependency whose absence would break the
publish path. Consistency won.
