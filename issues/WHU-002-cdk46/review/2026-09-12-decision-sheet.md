# WHU-002 — decision sheet, 12 September 2026 (editorial time)

A draft for the operator. **Nothing here is decided.** No decision file, page or
ledger was changed to produce it. Every recommendation is one person's reading
and is labelled as such; the operator supplies the decision, by the mechanism
each section names.

State it was drawn from: `publish.py check cdk46` at this tree, 7 STOPs —
email gate · gate findings settled (15) · changed sentences reviewed · outside
review · rule 1 (1: the P-value rounding) · page dateline · correction recorded
(37 undetermined). Live page: the 31 August publication (sha `4e4bb50b…`).

---

## 0. THE COUPLING, FIRST

**No sentence in group (b) corrects a FIGURE the subscriber email carries.**
Checked by grepping `email/issue2-cdk46.{html,txt}` for every figure and
phrase in the 1 September round: 29 blocks, 73.3/70.2, HARMONIA, "neither
separated", "exploratory", "response rate", "clinical benefit" — none in the
email. The one figure the email shares with a gate finding (0.804, c29) is not
corrected on the page.

**But two non-figure corrections DO reach the email**, and the update lane's
premise — `email gate: "the email is not what is changing"` — is already false
for cdk46 on those two, whatever lane is chosen:

| what the email says (issue2-cdk46.txt) | what the page corrected | round |
|---|---|---|
| "…a point Tanguy and colleagues made formally in npj Breast Cancer in 2018…" (l.74) | CORR-14: the observation is ours, not Tanguy's; the page's own log says "the same sentence went out in the announcement email in a barer form" | 1 Sept |
| "it was funded by Pfizer, which makes palbociclib" (l.125) | the page now quotes the paper's funding statement, "supported by Pfizer Inc (no grant number)", and the SABCS poster's "funded by" was withdrawn as a quotation from a document not held | 1 Sept |

Neither changes a number, so the update lane's *figure* parity check would
pass. Both are misattributions already sent to subscribers. That is a
corrections-email question (`correction_email.py`), not an update-lane one, and
it is outside this sheet. It is flagged here because "the email is not what is
changing" is the ground on which `email gate` is softened, and for cdk46 that
ground is not sound.

---

## 1. THE 15 GATE FINDINGS

Gate run of 2026-08-31 (claude-sonnet-4-6) on an earlier draft (54ff6332). The
page has been through the 31 August, 1 September and 12 September rounds since.
Decisions go in `gate-findings.json` via `findings.py`; a decision must be
`accept`/`reject` with a source and a quotation in the held bytes, or a
`judgement` with a reason and a name.

**Findings whose sentence has CHANGED since the gate ran — a different question
from accept/reject:** c4, c82, c95, c25, c29, c68, obj-1, obj-2, obj-3, inf-1,
inf-8. Eleven of fifteen. For each, the row below says whether the gate's
objection still applies to today's sentence. Only inf-3, inf-9, inf-10 and
inf-16 attack a sentence that stands verbatim.

| id | kind | the sentence AS IT STANDS TODAY | gate verdict | still exists? | RECOMMENDED | one line |
|---|---|---|---|---|---|---|
| c4 | figure | "In combination with fulvestrant rather than an aromatase inhibitor, both ribociclib and abemaciclib are category 1, and palbociclib is not." | WRONG_VALUE — "verified for the fulvestrant combinations; the complication is that the attributed source is v6.2026, which I cannot access" | changed (rewritten 31 Aug to scope it) | **accept, settled by S001 attestation** | The gate's own text says the fact is correct; its objection was reaching the licence-bound guideline, which no gate may. The operator's recorded reading of the Categories table (advocate S001-11/12/13) is the settling document. |
| c82 | figure | "The guideline prints the same medians against HR 0.56 (0.45–0.70)." | WRONG_VALUE — "no source gives HR 0.56 with CI 0.45–0.70" (papers give 0.556 / 0.568) | changed (now explicitly the guideline's print, not the paper's) | **accept, settled by S001 attestation** | The sentence claims what the guideline *prints*, not what the paper found; the gate searched papers. Needs the operator's reading of the table row to settle. Changed-sentence case. |
| c95 | characterisation | "MONARCH 3's is two-sided and was judged against .034, not .05: its cumulative two-sided type I error of 0.05 was divided … and spent across interim and final analyses under an O'Brien-Fleming spending function." | WRONG_VALUE — "the spending function is Lan–DeMets; O'Brien–Fleming is the boundary shape" | changed; a second sentence on the page already says "by the Lan-DeMets method with an O'Brien-Fleming spending function" | **reject, settled by S003** — but note the page is inconsistent with itself | The gate is right about the terminology and the page says it two ways. Settling it means one sentence changes: that is a page edit, not a decision file entry. Flag for the next correction round. |
| c25 | attribution | "…its registry record (NCT01740427) annotates each of its three stratified log-rank analyses … 1-sided p-value from the stratified log-rank test" | NOT_FOUND (gate could not reach the registry) | changed (now names the record) | **reject, settled by S020** | The string is in the held ClinicalTrials.gov posting (S020); `registry_figures`/`registry_facts` confirm it. A gate that cannot reach a registry is a fact about the gate. |
| c29 | figure | "Its MONARCH 3 input is the final overall-survival result — HR 0.804 (0.637–1.015), at 97.2 months, the figure given above" | NOT_FOUND in the NMA's per-trial table | changed (now says which result the NMA used) | **judgement — or a page edit** | The figure is verified in S003; the open question is whether S015 (the NMA) lists it. S015 is held: settle by reading S015's table. If S015 does not print 0.804, the sentence is a claim about S015 that S015 does not support. Read before deciding. |
| c68 | figure | "…Europe PMC's record (PMID 41093689) carries a license field reading cc by-nc-nd … carries an isOpenAccess field reading N…" | NOT_FOUND | changed today (LIC-Q-001: unquoted readings) | **judgement, by name** | A reading of a live index on 10 September, recorded as such on the page and in S025.retrieval_claims; no held document settles it and the page no longer claims one does. |
| obj-1 | fairness/FACT | "Neither is first line with an aromatase inhibitor…" — GONE; replaced 1 Sept by "restricted to the HER2-enriched intrinsic subtype" | SERIOUS — HARMONIA enrolled first-line patients and allowed letrozole | changed; the objection was accepted as CORR-15 | **accept, settled by S018 (registry: arms and population)** | Already acted on; the decision file never recorded it. |
| obj-2 | fairness/FACT | "the trial being powered on response rate" — GONE; page now says "its stated primary objectives are the clinical benefit rate (CBR)… while its sample-size calculation says 'The primary outcome of interest is the overall response rate (ORR)'" | SERIOUS — primary endpoint is CBR | changed; acted on as CORR-19 | **accept, settled by S017 (Q-21)** | The paper names one endpoint and powers on another; the page now quotes both. |
| obj-3 | fairness/FACT | source-list twin of obj-2 — GONE | SERIOUS | changed; acted on as CORR-19 | **accept, settled by S017 (Q-21)** | Same fix, same document. |
| inf-1 | inference/FACT | "It also reports overall survival, as an exploratory endpoint" — GONE; now "…pointing the same way. This page called that an exploratory endpoint until 1 September, which was wrong…" | SERIOUS — OS is PALMARES-2's primary endpoint | changed; acted on as CORR-16 | **accept, settled by S021 (registry primary outcome)** | Already corrected; record the decision. |
| inf-3 | inference/CONTRADICTION | "On the endpoint every one of these trials was powered to measure, nothing separates them." | SERIOUS — implies PFS-only powering; false for PALOMA-2 | **stands verbatim** | **accept — page edit owed** (gate's fix: "On progression-free survival — the primary endpoint all four trials were powered to measure — nothing separates them.") | The contradiction with the page's own later PALOMA-2 paragraph is real. Cannot be settled by a document; it is a wording decision. |
| inf-8 | inference/CONTRADICTION | "A network meta-analysis (Scientific Reports, February 2024) pooled seven phase III randomised trials, 4,415 patients, at a median follow-up of 73.3 months." | SERIOUS — the paper prints 73.3 (abstract) and 70.2 (results); the body prints only 73.3 | **stands verbatim** (the 31 Aug CORR-08 note sits in the log, not the body) | **accept — page edit owed** | S015 is held and prints both; the body should carry the discrepancy where a reader meets the figure, not only in the log. |
| inf-9 | inference/CONTRADICTION | "The guideline also records that the three drugs have not been directly compared in clinical trials." | SERIOUS — unscoped; two head-to-heads exist | **stands verbatim** | **reject, settled by S001 + S017/S018 — with a scope check** | The sentence reports what the *guideline* says (true: the guideline says it), and the page's scoping discussion follows. Whether a reader who stops there is misled is an editorial call; recommend adding "in the first-line aromatase-inhibitor setting" only if the guideline's own sentence carries that scope (it does not — see CORR-01). Judgement. |
| inf-10 | inference/CONTRADICTION | "…both ribociclib against palbociclib, both outside the first-line aromatase-inhibitor setting, and neither separated them." | SERIOUS — HARMONIA reported nothing, so "neither separated them" overstates | **stands verbatim** — and the page's 1 Sept log admits it ("And a third time on HARMONIA… HARMONIA reported nothing") while the body sentence still says "neither separated them" | **accept — page edit owed** | The page corrected this in the *source list* ("the one that reported did not separate them") and in the log, and left the body sentence. Third instance, as the log itself says. |
| inf-16 | inference/CONTRADICTION | "…moved the hazard ratio from 0.96 to 0.92 (0.76–1.12). Four hundredths — and this piece … will not now call that no movement." | SERIOUS — 0.04 between trials and 0.04 within a sensitivity analysis are argued in opposite directions | **stands verbatim** | **judgement, by name — reject** | The sentence says explicitly that it will not apply a standard to others that it would not apply to itself; that is the argument, not a contradiction. A person should say so and sign it. |

Counts: **15 findings; 11 attack a sentence that has changed since the gate
ran; 4 attack a sentence that stands.** Of the 15, 6 are already acted on and
need only a decision recorded (obj-1/2/3, inf-1, c4, c25); 3 need a page edit
before they can be closed (inf-3, inf-8, inf-10 — plus c95's self-
inconsistency); 2 need a document read first (c29 against S015; c82 against
the operator's reading of the guideline table); 3 are judgements (c68, inf-9,
inf-16).

---

## 2. THE 37 UNCLASSIFIED

**(c) uncertain: 5.** Stated first, per instruction, and not zero.

**What the 37 are.** Every one is from the 1 September round. Thirty-one are
the page's own change-log entry for that day ("Corrected 1 September 2026…"),
read by the sentence checkers as new prose; six are body and source-note
edits from the same round. The CORR-14…19 decisions exist, resolve to
2026-09-01, and corrections.md carries 1 September entries — but the
`changes.json` rows recorded for that round carry *other* sentences (the ones
edited in the body), and the reconciliation matches on prose. So these 37 are
not undecided; they are decided sentences with no row that matches them. The
remedy for most is `explain-change --because CORR-nn` against the existing
label, which is neither `--not-a-correction` nor a new corrections.md entry.
That third bucket is added below as **(b′)**, because folding it into (a) or
(b) would misdescribe it.

**(b′) already recorded as a correction on 1 September — owed a row citing the
existing label: 25.** The "Corrected 1 September 2026" log entry, sentence by
sentence, under its four headings: *An observation we put under someone else's
name* (CORR-14, 6 sentences); *A true conclusion with a false reason* (CORR-15,
5); *An endpoint downgraded* (CORR-16, 3); *And a third time on HARMONIA*
(CORR-17, 4); *A number we withdrew that the paper had stated* (CORR-18, 7).
Plus the entry's two opening sentences ("Corrected 1 September 2026." / "Four
things a reader saw were wrong…"), which belong to all four labels; recommend
CORR-14 as the carrier with a note naming the others.

**(a) apparatus — candidates for `--not-a-correction`: 4.**
- "Read directly by Fred Ugast, on 28 and 29 August 2026, and by nobody and nothing else." (S001 note: names the reader; was "Read directly by a human")
- "NCCN's licence forbids putting the document through any automated tool, so no fact-check run, gate or script on this page has read it…" (S001 note: process)
- "Sections read: the first-line HR+/HER2- therapy tables…" (S001 note: reading log)
- "Not read: everything outside the HR+/HER2- advanced breast cancer section." (S001 note)
Reasoning: these describe our own reading of a document, add no assertion about
the world, and the page's prior text was true but less specific. Recommend
`--not-a-correction`, one note citing the 2026-09-01 adjudication.

**(b) substantive changes to what the page asserts — candidates for a
corrections.md entry: 3.**
- "Ribociclib and palbociclib have been compared head to head twice — Shaaban and colleagues in the second line with fulvestrant, and HARMONIA, which terminated at 61 patients — and the one that reported did not separate them; …" — the "Established" list. This IS the CORR-17 correction applied in the established list; corrections.md's 1 September entry covers the substance. Recommend `--because CORR-17` rather than a new entry; listed under (b) because it changes what the page asserts and the reader-facing entry should be checked to say it covers this sentence too.
- "Its full name is the Palbociclib Verifying Evidence of Real-world Impact study, and its published paper states that it was supported by Pfizer Inc., which makes palbociclib." and "The paper's funding statement reads: 'This work was supported by Pfizer Inc (no grant number)'." — a quotation replaced ("funded by", SABCS poster, not held → "supported by", paper, held: Q-12). No corrections.md entry names this. **Recommend a corrections.md entry** (a quotation on a published page was replaced with a different document's words; readers saw the first) — the same class as the licence quotation, and the email carries the old wording (§0).

**(c) uncertain: 5.**
- "Pfizer makes palbociclib." — trivially true, added beside the funding sentence; substantive or apparatus depends on whether the funding change is ruled a correction.
- "The same sentence went out in the announcement email in a barer form; it was found when a gate run read the email, and settled when the operator obtained the full text." — a statement about our own operation (rule 31(d)); true per the record, but it is the page announcing an email defect that no correction email has yet addressed.
- "That reason came in with the 30 August correction above." — a cross-reference inside the log; apparatus if the log is apparatus, correction prose if the log is the reader's correction history (it is both, which is the two-histories problem the process doc names).
- "It computes each trial's statistical power to reach significance on survival, and concludes that if significance appears in some trials and not others the difference might be more attributable to chance…" — carries a paraphrase of Tanguy that is not marked as a quotation; the 12 September Q-22 records the verbatim from the source list, not this sentence.
- "Its stated primary objectives are the clinical benefit rate (CBR), quality of life and toxicity profiles, while its sample-size calculation says The primary outcome of interest is the overall response rate (ORR)." — two `<q>`s (Q-19, Q-21) in a log sentence; recorded, but Q-21's verbatim context is the one the byte-match row warns on.

Totals: **(b′) 25 · (a) 4 · (b) 3 · (c) 5 = 37.**

---

## 3. THE P-VALUE ROUNDING — declared exclusion, for signature

`issues/WHU-002-cdk46/figure-exclusions.json` does not exist yet for this
issue; the file's shape is melanoma's (b13 reads it). Draft entries, three
figures, one sentence. **`by` is blank. Unsigned, this is not an exclusion.**

```json
{
  "_what_this_is": "Figures on this page that are not claims about any document, each declared by a person with the sentence it belongs to and the reason. B13 counts them in its report and reports one that no longer matches a sentence as stale, so this file cannot quietly become a filter.",
  "_the_rule": "An exclusion says 'this figure is not taken from a source', never 'do not check this figure'. If the sentence changes so that the figure IS a claim about a document, the exclusion stops matching and the check comes back.",
  "exclusions": [
    {
      "figure": "0.75",
      "in_sentence": "On overall survival it found nothing anywhere: ribociclib versus palbociclib 0.98 (0.87–1.10, P = 0.75), abemaciclib versus palbociclib 0.95 (0.84–1.08, P = 0.43), abemaciclib versus ribociclib 0.97 (0.82–1.14, P = 0.70).",
      "why": "The page's rounding, to two places, of P = 0.7531 as S016 (P-VERIFY, ESMO Open) prints it. The hazard ratios and intervals in the same sentence are printed as S016 prints them; the P values are not. Two places is this page's convention for a P value it is not testing against a boundary: every P on the page that is compared to a threshold (.0664 against .034; .00973 against .01018; .004; .007; .008) is printed at the source's precision, and every P that only says 'nothing separates them' is printed at two. The excluded figure is the rounding, not the value: S016's 0.7531 is in the bound span, verified.",
      "by": "",
      "on": "",
      "falsifier": "S016 ceasing to print 0.7531 for this comparison (a corrected paper, a re-analysis); or the page's sentence changing so that 0.75 is compared against a boundary, at which point the precision is a claim and the exclusion stops matching; or spancheck B12 reporting the rounding as a precision change, which is B12's question and not this one's."
    },
    {
      "figure": "0.43",
      "in_sentence": "<same sentence>",
      "why": "As above: S016 prints P = 0.4292 for abemaciclib versus palbociclib; the page prints 0.43.",
      "by": "",
      "on": "",
      "falsifier": "<as above>"
    },
    {
      "figure": "0.70",
      "in_sentence": "<same sentence>",
      "why": "As above: S016 prints P = 0.6956 for abemaciclib versus ribociclib; the page prints 0.70. Note this one rounds UP across the tenth: 0.6956 -> 0.70, which is correct to two places and is the case a reader is likeliest to query.",
      "by": "",
      "on": "",
      "falsifier": "<as above>"
    }
  ]
}
```

What is excluded: the two-place rounding of three P values the page does not
test against any boundary. What is not excluded: the values themselves, which
S016 prints at four places in the span the sentence is bound to. Alternative
the operator may prefer: print the four-place values and declare nothing, which
closes rule 1 with a page edit instead of a signature.

---

## Counts, for the report

- Gate findings: 15; 11 on a changed sentence, 4 on a sentence that stands.
- Unclassified: 37 = (b′) 25 already-recorded-owed-a-row · (a) 4 · (b) 3 · (c) 5.
- Coupling: no figure; two attributions/quotations the email carries (Tanguy; "funded by Pfizer").


---

## Addendum, 12 September 2026 (later): the classification rule applied, the entries drafted, c29 and c82 re-tested

### The 5 "uncertain", under the rule now in docs/whatholdsup-process.md § 9

| sentence | under the rule | carriage |
|---|---|---|
| "Pfizer makes palbociclib." | **substantive** — it exists to change what a reader concludes about P-VERIFY's funding | carried by the funding entry (Draft A below) |
| "The same sentence went out in the announcement email in a barer form; it was found when a gate run read the email, and settled when the operator obtained the full text." | **straddles** — about our own operation (31(d)), but it discloses to readers that the email was wrong, which is a correction of an account readers were given | carried by CORR-14; the email itself is a corrections-email matter |
| "That reason came in with the 30 August correction above." | **apparatus** in content (a cross-reference) — but it is a sentence of the 1 September log entry, which is the reader-facing account of CORR-15 | row citing CORR-15, not `--not-a-correction` |
| "It computes each trial's statistical power … more attributable to chance than to a truly different drug efficacy." | **substantive** — characterises what Tanguy's paper says | carried by CORR-14 (it is the log's account of that correction) |
| "Its stated primary objectives are the clinical benefit rate (CBR) … The primary outcome of interest is the overall response rate (ORR)." | **substantive** — characterises what Shaaban's paper says | carried by CORR-19 |

Count: substantive 3 · apparatus 1 · straddle 1. Four of the five are sentences
of the 1 September log entry and belong to group (b′): a row citing the
existing label, not a new entry and not `--not-a-correction`. None recorded —
this addendum applies the rule and decides nothing.

### The substantive entries, drafted for one approval — NOT entered

Two matters, not three: the sheet's group (b) had three sentences, two of
which are one correction.

**Draft A — new corrections.md entry (the funding statement)**

> ## 12 September 2026 — a funding statement quoted from a poster we do not hold
>
> The P-VERIFY source entry, and the body sentence that leans on it, said the
> study's SABCS 2024 poster states <q>This study was funded by Pfizer Inc.</q>
> We do not hold that poster and never did. The published paper (S016), which we
> hold, states in its funding section: <q>This work was supported by Pfizer Inc
> (no grant number)</q>. The page now quotes the paper, names it as the source,
> and says the plain thing the quotation is there to say: Pfizer makes
> palbociclib. The conclusion a reader draws — that P-VERIFY was industry-funded
> by the maker of one of the three drugs — does not change; the document the
> quotation came from does, and the wording with it ("funded by" was the
> poster's; "supported by" is the paper's).
>
> The announcement email of 29 August carries the earlier wording ("it was
> funded by Pfizer, which makes palbociclib"). A correction email is owed for
> that and for the Tanguy attribution (1 September); it has not been sent.

**Draft B — addendum to the existing 1 September entry (the head-to-head sentence in "Established")**

> **Added 12 September 2026.** The correction above ("And a third time on
> HARMONIA") reached the summary and the source list and missed the
> "Established" list, which still said the two head-to-head trials "did not
> separate them". It now reads: "Ribociclib and palbociclib have been compared
> head to head twice — Shaaban and colleagues in the second line with
> fulvestrant, and HARMONIA, which terminated at 61 patients — and the one that
> reported did not separate them." Same correction, third place.

Draft B is an addendum rather than a new entry because the ruling is already on
the record under CORR-17 and this completes it — the same shape as the
PALMARES-2 note under CORR-16.

### c29, re-tested against the held bytes (not a retrieval)

- **Table 1 is not in the held bytes.** Nature serves it as a separate "Full
  size table" page; the held S015 HTML carries only "Table 1 Characteristics of
  included studies. Full size table". Nothing in what we hold states MONARCH 3's
  row, so the page's "Its Table 1 lists MONARCH 3 at HR 0.804 (0.637–1.015) and
  its 'Year of updated data' row gives 2023" cannot be tested from the library.
- **The dates reconcile, and the page's sentence about the reference list is
  verbatim true.** S015: received 10 July 2023, accepted 29 January 2024,
  published 7 February 2024. S003: available online 8 May 2024, printing
  "hazard ratio, 0.804; 95% confidence interval 0.637-1.015; P = 0.0664". S015's
  reference list, verbatim: "Goetz, P. M. et al . Abstract GS01-12: MONARCH 3:
  Final overall survival results of abemaciclib plus a nonsteroidal aromatase
  inhibitor as first-line therapy for HR+, HER2- advanced breast cancer. in San
  Antonio Breast Cancer Conference 2023". The NMA used the final OS result via
  SABCS (December 2023), which S003 later published with the same figure. The
  objection "February cannot cite May" does not hold.
- **Outcome: LIVE, narrowed.** Not wrong, not closed. The remaining test is one
  acquisition — the table page (nature.com/articles/s41598-024-53151-8/tables/1)
  as an also_held rendition of S015 — after which the row is a string test.

### c82 — closed on the record

Answered as **S001-07 on 2026-08-29**, two days before the gate that raised it;
now recorded `attested`, citing that answer verbatim. The durable state that
lets checks consult such answers is `findings.attestation_for` (§ 11.5). The
gate was right about the publications (0.556 / 0.568 / 0.57) and wrong about the
guideline, which prints its own rounding; it could not have known, because the
licence forbids it reading S001.


---

## Addendum, 13 September 2026: c95 — the correction, drafted and NOT recorded

**F1, settled on the rendered page** (pdftoppm, 200 dpi, page 2 right column,
continuing at the top of page 3). Character by character the paper prints:

> The cumulative type I error rate within each population was maintained using the Lan—DeMets spending function with O’Brien—Fleming boundary used to control multiplicity for all the interim and final analyses.

Both dashes are long (em-width) rules with no spacing; the apostrophe in
O’Brien is typographic. The PDF's text layer yields "Lane DeMets" and
"O’BrieneFleming" for the same glyphs — declared on S003's record as
`text_layer: defective` (F3), since F2 produced no sound rendition (Europe PMC
inEPMC N; annalsofoncology.org and ScienceDirect 403 to a script; browser not
connected).

**The published sentences, from the live bytes (repo identical):**

1. `MONARCH 3&rsquo;s is two-sided and was judged against <b>.034</b>, not .05: its cumulative two-sided type&nbsp;I error of 0.05 was divided between the intention-to-treat population and a visceral-disease subgroup, and spent across interim and final analyses under an O&rsquo;Brien-Fleming spending function.`
2. `The trial maintained a cumulative two-sided type&nbsp;I error of 0.05 by the Lan-DeMets method with an O&rsquo;Brien-Fleming spending function, with alpha divided between the intention-to-treat population and a visceral-disease subgroup by a prespecified graphical testing procedure.`

Both call O’Brien–Fleming the spending function; the second also names
Lan–DeMets as "the method". The paper: the spending function is Lan–DeMets, the
boundary is O’Brien–Fleming. The gate (c95, WRONG_VALUE) was right.

### Draft — page edits

Sentence 1 → `…and spent across interim and final analyses under a Lan&ndash;DeMets spending function with an O&rsquo;Brien&ndash;Fleming boundary.`

Sentence 2 → `The trial maintained a cumulative two-sided type&nbsp;I error of 0.05 by a Lan&ndash;DeMets spending function with an O&rsquo;Brien&ndash;Fleming boundary, with alpha divided between the intention-to-treat population and a visceral-disease subgroup by a prespecified graphical testing procedure.`

### Draft — corrections.md entry

> ## 13 September 2026 — we called the boundary the spending function, twice
>
> On MONARCH 3's statistical design this page said, in the body, that the
> cumulative type I error was <q>spent across interim and final analyses under
> an O’Brien-Fleming spending function</q>, and, in the source list, that the
> trial maintained it <q>by the Lan-DeMets method with an O’Brien-Fleming
> spending function</q>. Both conflate two things the paper keeps apart. The
> paper's statistical section reads: <q>The cumulative type I error rate within
> each population was maintained using the Lan–DeMets spending function with
> O’Brien–Fleming boundary</q>. Lan–DeMets is the spending function — the rule
> for how much alpha may be spent at each look; O’Brien–Fleming is the shape of
> the boundary that spending traces. Both sentences now say so.
>
> No figure changes: the alpha split (0.04 and 0.01), the final-look threshold
> (.034) and the result (P = .0664, not significant) are as they were. What
> changes is the name of the method, which a reader checking us against the
> paper would have found wrong.
>
> The fact-check gate raised this on 31 August (c95) and it sat unanswered
> until 13 September. Settling it required reading the paper's page as
> printed: the PDF's text layer renders the dashes in both names as the letter
> "e", so no string check could confirm or refute the wording, and the record
> now says so.

### Draft — label (review/2026-09-13-c95-adjudication.md)

> ## C95-001 — the spending function and the boundary, un-conflated
> **What changed.** Two sentences (body; MONARCH 3 source note) rewritten as above.
> **Why.** Gate finding c95 (WRONG_VALUE, 31 August), confirmed 13 September on the rendered page of S003 (F1).
> **Who decided.** The advisor's directive of 13 September, authorised by the operator; applied by Claude Code.
> **Effect on this assessment.** None on any figure.
> **Recorded for readers** in corrections.md, 13 September 2026.

### Draft — changes.json rows

Two `explain-change cdk46 --because C95-001` rows (one per sentence, `--was`
the published sentence, `--now` the replacement). c95's decision becomes
`accepted`, source S003, with the paper's sentence as the quote — which the
quotation check will report **cannot evaluate** (WARN) against the defective
layer, not ok and not STOP, until a sound rendition is held.


---

## Addendum, 13 September 2026 (later): the five inferences, changecheck re-run, the source-list draft, what was recorded

### Source-list correction for S021, S025, S027 — DRAFT, shown, NOT applied

The preflight row names three documents that carry sentences on the page and
have no entry in the list a reader sees. Each is mentioned in the prose — the
PALMARES-2 registry by NCT number in the PALMARES note, the corrigendum in the
MONARCH 3 note (journal, year, volume, page, DOI, PMID), the second P-VERIFY
paper as a body link and a link inside the first P-VERIFY entry — but none has
a `<div class="src">` entry with a link of its own, which is what the row
matches on (by any identifier the ledger holds). SRC-LIST-001 class: nothing
quoted changes; the list gains three entries.

**Entry 1 — after the HARMONIA registry entry (tag Registry):**

> `<a href="https://clinicaltrials.gov/study/NCT06805812">PALMARES-2 — ClinicalTrials.gov record. NCT06805812</a>`
> *Note:* Read for what the paper's registration says the study is — observational, still recruiting toward an estimated 3,500 patients, overall survival its primary outcome — and for what it does not have: no results are posted. That absence is why this page does not print PALMARES-2's survival figures; the paper's full text did not open to us and the registry has nothing to fall back on. Read from the record itself on 30 August 2026; held as the v2 API protocol section.

**Entry 2 — after the MONARCH 3 final overall-survival entry (tag Corrigendum):**

> `<a href="https://www.annalsofoncology.org/article/S0923-7534(25)00851-8/fulltext">Corrigendum to MONARCH 3 — final overall survival. <em>Ann Oncol</em> 2025;36:1556</a>`
> *Note:* The formal correction to the paper above, held in full since 1 September 2026 and read. It corrects one number — the placebo-arm event count in the chemotherapy-free survival analysis of Figure 4, 162 to 132 — and republishes the figure. This page uses nothing from that endpoint; the overall-survival figures above are untouched. Its access state and licence are settled in the entry above, which this entry does not repeat.

**Entry 3 — after the first P-VERIFY entry (tag Comparison):**

> `<a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC12424423/">P-VERIFY — real-world progression-free survival of first-line CDK4/6 inhibitors plus an aromatase inhibitor. <em>ESMO Open</em> 2025</a>`
> *Note:* The second paper from the same Flatiron cohort, on progression rather than survival: ribociclib and abemaciclib each against palbociclib, no significant difference found. The body links it by its PubMed record (PMID 40896879); the document we hold is the PMC full text. Same cohort, same funding statement as the paper above.

**corrections.md entry, drafted (dated the day the list changes):**

> ## [date] — the source list did not show three more documents this page rests on
>
> On 12 September this page said its source list had been made to show two documents it rested on without listing. Three more were in the same state and were not caught then: the PALMARES-2 registry record, which the page cites for the study's primary outcome and for the absence of posted results; the corrigendum to MONARCH 3's final overall-survival paper, which the page discusses at length inside another entry but never listed on its own; and the second P-VERIFY paper, linked from the body since publication. Each now has an entry. Nothing quoted or asserted changes; three documents a reader could already find in the prose can now be found where the page promises every source is.

**Label:** `review/[date]-source-list-2-adjudication.md`, `## SRC-LIST-002 — three documents shown to the reader`, same shape as SRC-LIST-001. Three `explain-change --because SRC-LIST-002` rows (kind added).

Not applied: the block says draft and show.

### changecheck, re-run (twice — the second run was mine, unneeded, ~3¢ wasted)

Run against `aca7b4b8`: 102 changed sentences, 16 findings, 7 decided. The
0.804 pair (S015 network meta-analysis input / Table 1) no longer appears —
bound. **Nine open**, all counted as such by the `changed sentences reviewed`
row:

| # | sentence carries | what it needs |
|---|---|---|
| 1–4 | 6.2026 (two sentences, each raised twice: FIGURE_IN_NOTHING_HELD + NEW_AND_UNBOUND) | **a document we cannot hold**: S001, NCCN v6.2026, licence-barred from every automated reader; the version number is on the operator's attested reading (S001 answers). Comes back to the advisor as "missing document" only in the sense that it can never be held; a disposition against the attestation is the alternative. |
| 5–7 | 116 (three sentences: the body's Shaaban sentence, its source note, and the 31 August log sentence) | **no missing document.** S017 is held and never prints the total; it prints 58 per arm. 116 is our arithmetic (58 + 58). Needs a disposition saying so (or a figure-exclusion attributed to us), not a document. |
| 8 | 0.71, 0.712, 0.535 | **no missing document.** The sentence is S007's source note; S007 (MONALEESA-7 OS, NEJM 2019) is `full_text_held` since 1 September (Fred's browser download) and its text carries 0.71, 0.54, 0.95; S022 (the registry posting) carries 0.712, 0.535, 0.948 — tested against the held bytes 13 September. It needs a binding, not a document. **And a finding, three tests deep:** the same note still tells readers "The journal paper is behind a wall we could not open" — (1) the ledger says held, by whom, when; (2) the held bytes carry the figures; (3) the page says the opposite. Same class as CORR-10 (a wall claimed over a paper the ledger held). Not fixed: pages untouched in this block. To the advisor. |
| 8′ | (row 8's genuinely-missing candidate withdrawn) | I first wrote "NEJM 2019 not held" from memory of a summary; the ledger says otherwise. Rule 22: opened the record before reporting. |
| 9 | 464, 31.3, 45.7 (PALMARES note) | **a document we do not hold**: the PALMARES-2 paper (every direct route refused 31 August; S021's registry record carries no results). |

Genuinely missing document, for the advisor: **one** — the PALMARES-2 paper
(row 9). Rows 1–4's document is barred, not missing; rows 5–8 need no document
(116 is our arithmetic; 0.71/0.712 are in held S007/S022 and want a binding).

### Recorded in this addendum's block

- corrections.md: `## 13 September 2026 — a funding statement quoted from a poster we do not hold` (Draft A, entered; dated the day it is recorded, and it says the wording changed 11 September). Label `review/2026-09-13-funding-quotation-adjudication.md`, `## FUND-Q-001`.
- corrections.md: the Draft B addendum under the 1 September entry (**Added 13 September 2026.**).
- changes.json: nine rows — FUND-Q-001 ×3 (body funding sentence, source-note quotation, "Pfizer makes palbociclib."), CORR-17 ×1 ("Established" head-to-head), CORR-14 ×2, CORR-15 ×1, CORR-19 ×1, `--not-a-correction` ×1 (the NCCN-licence process sentence).
- `correction recorded` row: STOP → **ok** (62 differ; 52 by an entry, 10 not a correction).
- dateline: 1 September 2026 → 13 September 2026.
- Consequence not acted on: the homepage card says 13 corrections, the record now says 14 — `homepage dates match the record` is a new STOP. The card is regenerated from the generator, never typed; not done here because this block does not touch pages beyond what it names.


---

## Addendum, 13 September 2026 (third): drafts for the advisor — inf-8 and the S007 note

### inf-8 — DRAFT, not recorded

**Page edit (body, the network meta-analysis paragraph):**
`…pooled seven phase III randomised trials, 4,415 patients, at a median follow-up of 73.3 months.` →
`…pooled seven phase III randomised trials, 4,415 patients, at a median follow-up the paper reports as 73.3 months in its abstract and 70.2 months in its results section; this page cannot determine which is correct.`

**Bindings (S015, article HTML, both spans verified present 13 September):**
- `Median follow-up was 73.3 months (range: 48.7–97.2 months)` — the abstract
- `The median follow-up was 70.2 months (range: 48.7–97.2 months)` — the results section

Note for the advisor: the S015 source-list note also opens "Seven phase III trials, 4,415 patients, 73.3 months median follow-up" and discloses 70.2 only in a parenthetical two sentences later. The directive names the body; I have not drafted a note edit. Say if the note's opening should carry both figures too.

**corrections.md entry (draft):**

> ## [date] — a figure the body kept printing after this page had already questioned it
>
> On 31 August this page recorded, in its corrections, that the network meta-analysis (Scientific Reports, February 2024) gives its pooled median follow-up as 73.3 months in its abstract and 70.2 months in its results section, over the same range, and that we cannot say which is correct. The body went on printing <q>at a median follow-up of 73.3 months</q> alone. A reader of the body — which is most readers — saw a figure this page had already questioned, and nothing in the sentence told them so. The body now carries both figures and says the page cannot determine which is correct. The source-list note had disclosed the discrepancy since 31 August; the body had not, until now. Nothing else in the paragraph changes.

**Label:** `review/[date]-inf8-adjudication.md`, `## INF8-001 — both follow-up figures in the body` (what/why/who/effect/recorded-for-readers). **Row:** one `explain-change --because INF8-001`. **Finding:** inf-8 → `accepted`, S015, quote `The median follow-up was 70.2 months (range: 48.7–97.2 months)`.


### The S007 source note — DRAFT, not recorded

**What the note tells readers now (published bytes, unchanged since 30 August, commit 1a4ac16):** the test direction "is stated in the ASCO 2019 abstract … and confirmed independently in the trial's ClinicalTrials.gov results posting"; then: `The journal paper is behind a wall we could not open; the registry is not. The paper prints 0.71; the more precise 0.712 is the Cox hazard ratio in that same registry posting (95% CI 0.535–0.948), and does not appear in the publication this page cites.`

**What the ledger says:** S007 `full_text_held`, "Fred Ugast, who downloaded the publisher's PDF in a browser on 2026-09-01"; identity confirmed by the article's own DOI; "STATE MEANS HELD, NOT READ … no section of it has yet been read against the page."

**What the held bytes carry (read 13 September, every span verified present):**
- `hazard ratio for death, 0.71; 95% CI, 0.54 to 0.95; P = 0.00973 by log-rank test`
- `The one-sided stratified log-rank P value was 0.00973, which crossed the prespecified stopping boundary (P = 0.01018) to claim superior efficacy of ribociclib`
- `at a one-sided overall significance level of 2.5%, with the use of a log-rank test and threelook group sequential design`
- `The median duration of follow-up was 34.6 months (minimum, 28.0 months)`

So the paper itself states the direction of the test; the note's "confirmed independently" chain (abstract, then registry) was built because nobody here had opened it, and it stood twelve days after Fred had.

**Rewritten note (draft):**

> The protocol-specified interim analysis: median not reached vs 40.9 months, HR 0.71 (95% CI 0.54–0.95), one-sided P = .00973 against a prespecified stopping boundary of P = .01018, at 34.6 months median follow-up. The paper states the direction of its test itself — <q>The one-sided stratified log-rank P value was 0.00973, which crossed the prespecified stopping boundary (P = 0.01018)</q> — and the trial's ClinicalTrials.gov results posting (NCT02278120) posts the same analysis with p = 0.00973 and the annotation <q>One-sided stratified log-rank test</q>. The paper prints 0.71; the more precise 0.712 is the Cox hazard ratio in that registry posting (95% CI 0.535–0.948), and does not appear in the paper. Until 13 September 2026 this entry said the paper was behind a wall we could not open and rested the direction of the test on the ASCO 2019 abstract and the registry instead; the operator had obtained the publisher's PDF on 1 September and the page was not re-read against it. A group-sequential test with an adjusted threshold, which is why its p-value cannot be read beside MONALEESA-2's 0.008 as though the two numbers meant the same thing.

(The ASCO abstract link, S023, is dropped from the note as the direction's source; S023 stays in the ledger and is still held. Say if the link should stay.)

**Bindings after the rewrite:** the 0.71 / 0.54 / 0.95 / .00973 / .01018 / 34.6 sentence → S007 (spans above); the 0.712 / 0.535 / 0.948 sentence → S022 (spans `0.712` … `0.535` … `0.948`, verified present).

**corrections.md entry (draft):**

> ## [date] — we told readers a paper was behind a wall while we held it
>
> The source entry for MONALEESA-7's overall-survival paper (N Engl J Med, 2019) said, from 30 August, that <q>the journal paper is behind a wall we could not open</q>, and rested the direction of the trial's survival test on a conference abstract and the trial's registry record instead. On 1 September the operator obtained the publisher's PDF and it entered our library, identity confirmed. The entry was not re-read against it, and went on telling readers for twelve days that the paper was out of our reach. It was not; the paper states the direction of its own test — <q>The one-sided stratified log-rank P value was 0.00973, which crossed the prespecified stopping boundary (P = 0.01018)</q> — and every figure the entry prints from it is in it. The entry now says so. No figure changes. It was found on 13 September when a check that reads changed sentences reported the entry's figures as resting on nothing this system could name, and the ledger was opened before the report was believed.

**Label:** `review/[date]-s007-wall-adjudication.md`, `## S007-WALL-001 — a wall claimed over a paper the library held` (CORR-10's class; what/why/who/effect/recorded). **Row:** one `explain-change --because S007-WALL-001` (kind changed, the whole note). **Finding:** none open on this; the 116/0.71 changecheck items are settled separately (§ 8).

### PALMARES-2 (464 / 31.3 / 45.7) — acquisition result, and the correction DRAFT

**Acquisition attempt, 13 September, browser:** could not be made. The Claude-in-Chrome extension reports "Browser extension is not connected" — the same state as on the F2 attempt for S003. No request reached annalsofoncology.org from a browser; the only refusals on record are the script's 403s of 31 August. So this is not a publisher refusal and not a paywall finding; it is that no browser was available to this session. If a browser is connected, the attempt is one navigation and I will make it before this draft is recorded.

**What the ruling reaches, measured against what we hold.** The changecheck item names three figures (464 events, 31.3 months, 45.7 months) in the S011 note's immaturity sentence; the same sentence also carries 25.2 and 22.4. None of those five is in any held document. But the note's and the body's OTHER PALMARES-2 figures — 1,982 patients; aHR 0.76 (0.63–0.92), p = 0.004; 0.83 (0.73–0.95), p = 0.007; 0.91 (0.73–1.14), p = 0.425 — are printed verbatim in a document we DO hold: S027 (the second P-VERIFY paper, ESMO Open 2025), which reports them as PALMARES-2's: `In PALMARES-2 ( N = 1982), aHR for rwPFS in the 1L setting was 0.83 (95% CI 0.73-0.95, P = 0.007) for ribociclib versus palbociclib, 0.76 (95% CI 0.63-0.92, P = 0.004) for abemaciclib versus palbociclib, and 0.91 (95% CI 0.73-1.14, P = 0.425) for abemaciclib versus ribociclib.` Span verified present. "Eighteen Italian centres" is in no held document. S016 (held) cites the ASCO 2024 presentation: `J Clin Oncol. 2024;42(suppl 16):1014`.

So the draft below does two things and separates them: (1) the immaturity figures are dropped, per the ruling; (2) the PFS figures are re-attributed to S027's report of the paper rather than to the paper itself, and bound there — a recommendation, because they are figures from a document we hold. If the ruling is meant to drop them too, say so; the page's "This is the study that separates palbociclib from the other two" then loses its numbers.

**Page edit — the S011 note's immaturity sentence:**
`What is exploratory is the maturity of this look at it: the authors describe the survival data as immature — 464 events at a median 31.3 months — with follow-up of 45.7 months on palbociclib against 25.2 on ribociclib and 22.4 on abemaciclib.` →
`What is exploratory is the maturity of this look at it: the authors describe the survival data as immature and the follow-up as uneven between the arms. The analysis was presented at ASCO 2024 (J Clin Oncol 2024;42(suppl 16):1014) and published in Annals of Oncology in April 2025; we have not obtained either document, so this page does not print the event count or the follow-up figures.`

**Page edit — the body's PALMARES-2 paragraph, same clause:** `What the authors do say about that endpoint is that the data are immature — 464 events at a median 31.3 months — and that follow-up is badly uneven between the arms: 45.7 months on palbociclib against 25.2 on ribociclib …` → `What the authors do say about that endpoint is that the data are immature and that follow-up is uneven between the arms; the figures are in a document we have not obtained, and this page does not print them.`

**Page edit — attribution of the PFS figures (recommended, not the ruling's letter):** in the body, `PALMARES-2 (Annals of Oncology, April 2025) followed 1,982 patients across eighteen Italian centres` → `PALMARES-2 (Annals of Oncology, April 2025) followed 1,982 patients in Italy` and, after the hazard ratios, add `— figures we take from the second P-VERIFY paper's account of PALMARES-2 (ESMO Open 2025), which we hold; the PALMARES-2 paper itself we do not.` Note: same attribution sentence; "eighteen Italian centres" dropped (no held document states it).

**Bindings:** the PFS-figure sentences (body and note) → S027, the span above. The rewritten immaturity sentences carry no figure and need no row.

**corrections.md entry (draft):**

> ## [date] — figures printed from a paper we never held
>
> This page's account of PALMARES-2 printed, from the paper's discussion of its own survival data, an event count (464), a median follow-up (31.3 months) and per-arm follow-up figures (45.7, 25.2 and 22.4 months). We do not hold that paper: every route we tried was refused, and the figures came through an automated search route the page itself described as weaker than reading. A figure from a document we cannot open is not a figure this page can stand behind, and the page now says that the data were described as immature and the follow-up as uneven, names where the analysis was presented and published, and prints no numbers for either. The progression-free survival hazard ratios the page gives for PALMARES-2 are unchanged and are now attributed where we actually read them: the second P-VERIFY paper (ESMO Open 2025), which reports them, and which we hold in full. "Eighteen Italian centres" is dropped for the same reason as the follow-up figures.

**Label:** `review/[date]-palmares-figures-adjudication.md`, `## PALM-FIG-001 — figures from a paper we do not hold, withdrawn`. **Rows:** three `explain-change --because PALM-FIG-001` (note immaturity sentence; body immaturity clause; body attribution sentence). **changecheck disposition:** accept, naming the label.

### Recorded under the directive of 13 September ("five dispositions, three clarifications, two corrections, and the nine")

- **c95** recorded: both page sentences rewritten; corrections.md `## 13 September 2026 — we called the boundary the spending function, twice` (last clause names the text layer); label `review/2026-09-13-c95-adjudication.md` `## C95-001`; two rows; c95 → accepted, S003, quote = the rendered page's sentence; the quotation check reports cannot-evaluate (WARN). F2 attempted and refused (Europe PMC inEPMC N; annalsofoncology.org and sciencedirect.com 403 to a script; no browser connected). F3 counterfactual tests: `tests/test_whatholdsup_text_layer.py` — spancheck level (existing) and findings level (added today); each proven real by deleting the distinction and watching it fail.
- **inf-3, inf-9, inf-16** clarified on the page, `--not-a-correction` rows, dispositions `judgement` with the directive's text; inf-3 bound to the four trials' primary-endpoint statements (S005/S019, S003, S009/S020, S007/S022); inf-16's figures bound to S010, its two new sentences carry premises and a step; `1.0` declared in figure-exclusions.json as the no-effect value.
- **inf-10** dismissed by re-test, quoting the current sentence in full. `findings.retest` now returns `partly` on a prefix match (neither live nor settled; no decision recorded; WARN row "findings partly still in the text"); counterfactual tests added and proven; ledgered as face 5 in `source_store.py`.
- **The nine:** 116 ×3 rejected (58 + 58, S017 prints 58 per arm and no total); 0.71 / 0.712 / 0.535 bound to S007 + S022 as held; 6.2026 ×4 rejected citing the attestation (S001 heading "version 6.2026", every S001 answer "by Fred Ugast, reading NCCN v6.2026 directly"; the "Nowhere in version 6.2026…" sentence rests on S001-13, answered 3 September); PALMARES-2 — no browser was connected, so no browser attempt was possible; the correction is drafted above with that result.
- Two model findings from today's changecheck runs rejected on the record (a CONTRADICTION whose own text concludes "no contradiction found"; an UNSOURCED reading of a disclaimer as a claim); a third (the MONALEESA-2 one-sided sentence read as sitting in the MONARCH 3 entry) rejected against the page bytes.
- Housekeeping: `tests/whatholdsup/announce_test.py` → `announce_check.py` (a script, not a pytest module; it also lacked the scripts dir on sys.path, fixed). Run standalone it reports 10 passed, 1 failed: "a sender that exits non-zero records NOTHING" gets rc 2 not 1 because no interpreter here can import `resend` — it records nothing, as required; the exit code differs for an environmental reason. Not fixed. `tests/test_whatholdsup_dates.py`'s fixture helper scoped to the melanoma card (it asserted a count string was unique across the index; cdk46 reaching 15 corrections made it equal melanoma's).
- Homepage card regenerated (14 → 15 corrections), `index_dates.audit()` clean.

### Recorded under the directive "record the three corrections and the source list" (13 September)

- **INF8-001** recorded: body and S015 note opening (both figures, shared range, "cannot determine which is correct"); the note's parenthetical deferral removed; entry says the note carried the same asymmetry; label; two rows (+ per-sentence rows for the diff); inf-8 → accepted, S015; both spans bound.
- **S007-WALL-001** recorded with the S023 clause ("is how this page confirmed the direction while the paper stood unread here; the paper now states it itself"); entry; label; rows; the note's sentences bound to S007 / S022 / S023; Q-26 records the new quotation.
- **SRC-LIST-002** recorded: three entries, entry, label, three rows (+ per-sentence rows); the four figure-bearing entry sentences bound to S027 / S021 / S025.
- **PALMARES-2 (C): STOPPED before editing** on the directive's own precondition — see the report; the page says "progression-free survival" / "Progression-free survival" where S027 says "rwPFS", and the summary-list sentence names no statistic where S027 says "aHR". Both strings reported. Nothing on the page changed for C.
- Homepage card regenerated (15 → 18 corrections); `index_dates.audit()` clean; dateline already 13 September.

### Recorded under the directive "PALMARES-2, two corrections" (13 September)

Sweep found five more sentences leaning on PALMARES-2's survival or on the unheld paper's own descriptions (contradiction paragraph ×2, open-questions list ×1, summary list ×1, note's ASCO-2024 figure ×1); all changed under PALM-FIG-001. PALM-END-001 (rwPFS / aHR, three places) and PALM-FIG-001 recorded: entries, one label file with both headings, rows per changed sentence, every figure-bearing sentence bound to S027 / S016 / S021; five deletions recorded UNSOURCED with the library search stated; 403, 0.08 and 0.05 declared as apparatus/arithmetic figures; the 464 changecheck item accepted as fixed. Homepage card regenerated (18 → 20). `update` read-only: 0 STOPs.
