# WHU-001 — provenance of the publication dates

**Established 9 September 2026.** Everything below was found on that date by
reading commits and a status document written on 27 August. **None of it was
recorded at the time**, and that is why it is here rather than in
`backend/data/whatholdsup/published.json`: a record does not gain rows for
events it did not witness. What is established afterwards goes in a note that
says when it was established. The two must never be merged, because the value of
the record is that its rows were written at the time.

---

## The question

The page's masthead reads **"Published 26 August 2026"**. The first row for
melanoma in `published.json` is **2026-08-28T16:05:57Z**. A check comparing the
two reports a two-day disagreement, and the disagreement is not real.

## What is established

**1. The page was live at `https://whatholdsup.org/melanoma` from 26 August.**

| evidence | |
|---|---|
| `54b9c88` | committed 2026-08-26 16:00:15 -0400; creates `melanoma.html`, `index.html`, `who-pays-for-this.html`, `style.css` and `vercel.json` (`cleanUrls: true`, which is what makes `/melanoma` resolve) |
| push | `origin/main` reflog: `deabfc02 -> 54b9c887`, **2026-08-26T20:00:16Z** — eleven seconds after the commit |
| `docs/whatholdsup-prelaunch.md` | written **2026-08-27**, header states every "today" claim was verified against the running system that day — the DNS, the live site, the code |
| — that document records | `/`, `/melanoma`, `/who-pays-for-this` → **Live, 200** |
| — and | issue one live is **stale**: "the deployed page still reads *157 unblinded patients*", evidence `curl https://whatholdsup.org/melanoma` |

**The control that makes this sound rather than merely plausible.** The same
table records `/what-this-is` as *"Written today, **not deployed**"*. A page
written but not pushed was not deployed; three pages pushed on the 26th were
live. That establishes that deployment tracked pushes on that date, which is
what carries the melanoma conclusion. It is a controlled observation sitting
inside a status document written for an entirely different purpose, and it
survived twelve days because somebody wrote down what they checked and when.

**2. `published.json` begins on 28 August because it was created on 28 August.**

| | |
|---|---|
| `publish.py` first commit | `533286e`, 2026-08-28 10:42 -0400 |
| `published.json` first commit | `81bc48e`, 2026-08-28 13:27 -0400 |
| first melanoma row | `0aa5b19`, 2026-08-28T16:05:57Z |

On 26 August there was no pipeline to record a publication and no file to record
it in. The record is not missing a row. **The event is outside its reach.**

**3. The word "Published" was applied retrospectively, to an accurate date.**

The masthead read a bare `26 August 2026 · event dated 19 August 2026` from
`54b9c88` through 27 August. It was rewritten to
`Published 26 August 2026 · Updated 28 August 2026` in **`152bbc5`, 2026-08-28
12:35 -0400** — thirty minutes after the first pipeline publish. Somebody
back-labelled the 26th as the publication date. They were right.

## The ruling

**The dateline stands. It is not changed, and no row is backfilled.** A row in
`published.json` asserts that the pipeline recorded a publication; writing one
for a day on which the pipeline did not exist would assert a record that never
happened, in the file every publication decision rests on. The record's honest
shape is that it begins on 28 August and this page predates it, and that shape
stays visible rather than being smoothed away.

## What was built instead, and why it is the durable part

`publish.record_begins()` derives the record's own start date from the earliest
`at` in `published.json`. The masthead check reports a Published date **earlier
than that** as a distinguishable state — *"the page predates the record rather
than disagreeing with it — an operator ruling, not a page edit"* — rather than as
a false date.

Nothing in that logic mentions melanoma. Every future page that predates its own
tooling gets the correct treatment without anyone remembering this
investigation. **Encode the principle; do not patch the instance.**
