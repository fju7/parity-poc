# Verification record — melanoma adjudication, standing rule 13

**Page verified:** `site/whatholdsup/melanoma.html`, sha256
`7ae5304cf5b7313b3c1c57718a2d234513eb68defed56f03fd5a231d6d102221`.
The review packet at `2026-09-09-review-packet.md` carries the same SHA in its
header.

**Verified by:** Claude Code (Opus 5), session of 2026-09-08/09. I did not write
the adjudication. I did write most of the page changes it dispositions, and that
is a real limit on this record: I am independent of the adjudication's authorship
and not of the implementation's. Rule 13 as amended asks for independence from
authorship of the adjudication. Where an entry turns on whether *my own* work
landed, I have said which artifact shows it rather than asserting that it did.

**What this record attests:** that each entry below was checked against a named
artifact, and what that artifact showed. It does not attest that the page is
true, and it is not the acceptance signature.

**Result, stated plainly.** The verification found **two discrepancies and one
noted item, all three in work authored by the reviewer** — including a figure
asserted seven times across four documents by two parties, none of whom measured
it. All three were ruled on and repaired on 2026-09-09; the amendment section at
the end of this record says what changed and what was re-checked. The findings
below are left as they were written. The point of a verification half is that it
finds things on its first run, and the record should show that rather than let
the fixes erase the evidence.

**Method.** Every ACCEPT was tested against the installed page as a string
present-or-absent check, in both directions — the new wording present, the
corrected wording gone from the body. 28 such checks; all pass. Where an entry
rests on a source document I opened the held bytes through `spancheck.b2_present`
or read the document directly. Where it rests on history I read `git log`/`git
show`. Figures asserted inside entries were measured rather than assumed, which
is where the one substantive discrepancy came from.

Two checks initially read as failures and are not: `the register says so` and
`drifted out from 0.288` are still on the page, in the change log, where the
entry quotes the error it corrected. Both are absent from the body. Verified by
splitting the page at `<footer id="updates">` and testing each half.

---

## OR entries

| entry | disposition | artifact opened | verdict |
|---|---|---|---|
| OR-001 | ACCEPT | Page: `has not been updated since 24 September 2025` present; `the register says so` absent from body, present in change log as the quoted error. S013 held record, `lastUpdatePostDateStruct.date` = `2025-09-24`, bound by field path. | CONFIRMED |
| OR-002 | ACCEPT, corrected further | Page: the four-slot enumeration and `do not independently classify a document as news or primary` both present, in Sources and in Checking. | CONFIRMED |
| OR-003 | ACCEPT | Page: `Both bounds came in, the upper from 0.906 to 0.887 and the lower from 0.288 to 0.294` present; old wording absent from body. S004 and S007 spans verified on the row. | CONFIRMED — see note 1 |
| OR-004 | ACCEPT | Page: `In the Lancet report, immune-mediated adverse events were similar` present. S003 held abstract carries `25% … 18%` and `(37 [36%]) and monotherapy (18 [36%])`; both spans verified. | CONFIRMED |
| OR-005 | ACCEPT | Page: `The second pair says otherwise` present. Entry states no source required; none checked. | CONFIRMED |
| OR-006 | ACCEPT | Page: `That single release moves both scores, and both upward whatever the numbers say` present. Recomputation of 3.94 from the six dimrows and published weights re-run: 3.9375 → 3.94. | CONFIRMED |
| OR-007 | ACCEPT, half later rejected | Page: enumeration present and bound to five outlet spans, each naming KEYNOTE-942 beside the 49% figure, all verified. The KOL Pulse half was overturned — see RV-05. | CONFIRMED |
| OR-008 | ACCEPT | Page: `In EORTC 18071, adjuvant ipilimumab` present; `holds no document about one` absent. S029 held; `65.4% … 54.4% … 0.72; 95.1% CI, 0.58 to 0.88; P = 0.001` verified in the held bytes. Appendix C: universal negative 6 absent from the rebuilt packet. | CONFIRMED |
| OR-009 | ACCEPT | Page: the CheckMate 238 paragraph names its arms and the ipilimumab comparison. S021 held registry record. | CONFIRMED |
| OR-010 | ACCEPT | Page: `First, does the range cross 1.0?` present as the first of two, with the width question following and the convention note. | CONFIRMED |
| OR-011 | ACCEPT, reviewer wording rejected | Page: `These are 95% intervals, the convention readers meet elsewhere` and `on a two-sided 5% criterion` both present. The rejected attribution is absent — see RV-02. | CONFIRMED |
| OR-012 | ACCEPT | Page: `a permissive threshold, and a normal choice for a phase 2b trial` present. S007 `designed with approximately 80% power … one-sided a of 0.10` verified; S008 `1-sided alpha of 0.1 per protocol` verified. | CONFIRMED — see note 2 |
| OR-013 | ACCEPT | Page: `about a 66% chance the treated one goes longer without recurrence` present. S023 held, pairwise span verified; ledger shows `full_text_held`; S023 in the reader-facing list. | CONFIRMED |
| OR-014 | ACCEPT | Page: `the interval around that Phase 2b trend` and `patients in the Phase 3 trial` present in the strip; `furniture.py` passes 2 computed / 5 restates / 1 scale. | CONFIRMED |
| OR-015 | ACCEPT | Page: the blinding caveat present, naming injection-site pain 59.6% and chills 51.0% against a saline comparator. S002 and S013 spans verified on the row. | CONFIRMED |
| OR-016 | ACCEPT | Page: `stage IIB, IIC and IIIA patients` present. Inference record for the IIIA step present in the packet. | CONFIRMED |
| OR-017 | ACCEPT | Page: `anticipated in its registry record for November 2026` and `October 2033` present. S020 and S026 held records: `reportingStatus NOT_POSTED`, `anticipatedPostingDate` 2026-11 and 2033-10, read from the JSON. | CONFIRMED |
| OR-018 | PARTIALLY ACTED ON → closed | Scoring paragraph byte-compared against the declared base `melanoma.revised.html`: identical, 1152 bytes, all three score sentences unchanged — so the pass really was records-only. Three inference records present in the packet with premises verified. | CONFIRMED — see note 3 |
| OR-019 | ACCEPT, superseded | Page: `95% CI 0.114 to 1.584` present; `at 95% it would be wider still` absent. S007 Table 1 row `0.425 80% CI 0.179 to 1.004 95% CI 0.114 to 1.584` verified in held bytes. | CONFIRMED — see note 4 |
| OR-020 | PARTIALLY RESOLVED | `store.sources()` enumerated: S011 → S013, no S012. `review_packet.py` read: iterates and prints ids verbatim, no filter or renumbering, so the gap is in the store. Still open. | CONFIRMED |

## RV entries — read hardest, per the rule

| entry | disposition | artifact opened | verdict |
|---|---|---|---|
| RV-01 | REJECT | S020 and S026 held JSON, `outcomeMeasures` walked: OS rows carry `reportingStatus: NOT_POSTED` with `anticipatedPostingDate` 2026-11 and 2033-10. Nothing posted. The entry's account matches the rebase note, which records the reviewer signing off the false claim as "Verified true as stated". | CONFIRMED |
| RV-02 | REJECT | S007 held bytes: `0.510 80% CI 0.351 to 0.743 95% CI 0.288 to 0.906` present — the 80% interval belongs to the three-year HR. Searched S007 for any 80% interval on the 2023 readout: none; nearest are the TMB subgroups, as the entry says. | CONFIRMED |
| RV-03 | REJECT | Scoring paragraph measured in the declared base: 1,013 characters plain, 1,152 as HTML. `Reproducibility scores 4` begins at plain character 484. A 400-character cut lands inside the Data support sentence. | **DISCREPANCY — see finding A** |
| RV-04 | REJECT on the second clause | `sources.json` before the fix carried no EORTC entry; the library held no such document; `b13` reported 0.58 in nothing held. After: S029 stored, store's own identity test `contains its identifier PMC5648545`, ledger `full_text_held`. Page link now resolves to the copy held. | CONFIRMED |
| RV-05 | REJECT half of OR-007 | S019 read in full: `KEYNOTE-942` occurs 11 times, counted; `hazard-ratio figures circulating on announcement day are these KEYNOTE-942 Phase 2b numbers` present; the `~49%`-as-phase-2 wording occurs only inside a logged third-party post. Both spans are verified premises on the row. | CONFIRMED |
| RV-06 | REJECT | `git show` on commits 2c71b8e, d4de02a, 5ba841b, 5881433: working printed as `(3×.25)+(1×.20)+(4×.15)+(4×.15)+(5×.15)+(5×.10)`, which sums to 3.4000 against the printed 3.4. `87b8d9d` changes it to the rubric's weights and adds `the-rubric.html` in the same commit; rubric weights read 25/20/20/15/10/10. | CONFIRMED |
| RV-07 | REJECT the omission | NCBI efetch PMID 31442371: title enumerates 13 articles; comment-correction list carries `10.1056/NEJMoa1611299`. S029 held bytes carry `This article has been corrected. See N Engl J Med. 2018 Nov 9;379(22):2185`. Obtainability re-tested independently: NEJM 403, Europe PMC `isOpenAccess N`/`inEPMC N`, Crossref title and date only, no abstract anywhere. | CONFIRMED |

---

## Findings

### A. DISCREPANCY — a figure asserted seven times, in the entries about not checking figures

RV-03, and OR-018 and the process document with it, state that the scoring
paragraph "runs to 2,116 characters". **It does not. It is 1,013 characters of
plain text and 1,152 as HTML** — measured on the declared base and on the current
page, which are byte-identical for that paragraph.

The rest of RV-03 is exact. `Reproducibility scores 4` begins at plain character
484, matching the entry's "roughly character 480", and a 400-character cut does
land inside the Data support sentence, which is the mechanism the entry
describes. The failure happened as described. Only its size is wrong.

The direction matters. Overstating the paragraph by roughly 2× makes the
truncation more forgivable than it was: reading 400 of 2,116 characters is a
third of a long paragraph, reading 400 of 1,013 is most of a short one. That is
the shape rule 13 warns about — a reviewer's account of their own error reading
tidier than the error.

**Provenance.** It originates at `2026-09-08-directive-amendment.md` line 8
("char ~480 of a 2,116-char paragraph"), and I repeated it without measuring into
the verification addendum §7, the OR-018 entry, RV-03, and thence to the process
document and the remediation order. Seven occurrences, four documents, two
parties, one measurement nobody took. Both of us wrote it into entries whose
subject is asserting things about documents without opening them.

**Not corrected here.** I did not edit the adjudication I am verifying. It needs
a one-line fix in each of the seven places, or a note at RV-03 and a pointer.

### B. DISCREPANCY — the Outstanding section is stale, and inconsistently so

Two of its five items describe work that has since been completed:

- **Item 2, OR-019** — "replace the hedge with 0.114–1.584". Done. The page
  carries `95% CI 0.114 to 1.584` and the hedge is gone.
- **Item 4, the 4 September log entry and the misdated paragraphs** — "Blocking,
  because the header has claimed a 4 September update since that date with
  nothing in the log explaining it". Done. The entry is in the log, six
  paragraphs were relocated or split, and the header now reads 9 September.

Item 1 *was* updated to read CLOSED. That is what makes this a discrepancy rather
than a snapshot: the section reads as maintained, so a reader takes items 2 and 4
as live. Item 3 (S012) and item 5 (the unrecoverable 175) are correctly still
open.

An operator signing acceptance would be told two blocking items remain when
neither does.

### C. Noted, not a discrepancy — OR-003 and OR-012 quote superseded wording

Both entries quote page text that a later decision changed:

- OR-003 quotes "so the interval narrowed **only** slightly". "only" was removed
  on 8 September because no span carried its force; recorded in the step-3
  ruling and in `change-reviews.json`.
- OR-012 quotes "a permissive threshold, **equivalent to a two-sided 0.20**, and
  a normal choice…". The derived 0.20 was removed on 8 September because it is
  the page's own doubling and appears in no held document; the nearest 0.20 in
  S022 is an unrelated replication-crisis calculation and binding to it would
  have been RV-02's error.

The substance of both ACCEPTs landed and is on the page. I record these because
an entry quoting text the page no longer contains will read as a failed change to
whoever checks it next, and because OR-012's removal is recorded only at round
level in the change set, not against the entry.

---

## What I did not verify

- **Whether the page is true.** Out of scope. This checks the adjudication
  against the page and the artifacts.
- **The S029 erratum's content.** It cannot be read. RV-07 and the source note
  say so; the standing errata debt is open and `corrections not yet read` is
  still BLOCKED by design.
- **The Spruance PMID 15273082.** Not in the held bytes; recorded as unverified
  in `attributions.json`, per ruling.
- **Sources S005, S006, S009, S010, S015, S016, S017, S018, S027, S028.** Not
  re-opened for this record beyond the spans the checks verify automatically.
- **The 175 unreconciled changes of 28 August – 4 September.** Closed by decision
  at Outstanding item 5, not by research, and I did not reopen it.

## Gate state at verification

All green except one, which is open by ruling:

    BLOCKED  corrections not yet read — S029: Erratum in 31442371

rule 1 ok (130 sentences) · rule 2 ok (130) · figures in held documents ok (132,
3 declared exclusions) · correction history ok (244 change-log sentences) ·
sources checked for corrections ok (29) · changed sentences reviewed ok (95
changed, 3 findings, all disposed) · attributions ok (3) · sources shown ok (27) ·
universal negatives ok · furniture ok · 45 inference records, 0 failed spans.


---

# Amendment, 2026-09-09 — the discrepancy rulings applied

All three findings were upheld. None blocked publication; all three were record
repairs. What follows is what changed and what I re-checked. **The findings above
are unedited.**

## A — RV-08 added, and the figure corrected in seven places

The operator measured before ruling and confirmed every number: 1,013 plain,
1,152 as an HTML element, `Reproducibility scores 4` at plain character 484, a
400-character cut landing inside the data support sentence.

The origin is now known and is worse than an unchecked repetition. The probe was
`re.search(r'Two scores, not one.{0,2400}', s)` — a fixed 2,400-character window
of raw HTML, tag-stripped afterwards. **2,116 is the text content of an arbitrary
window.** It was never a measurement of a paragraph and was then reported as one.

Corrected in all seven: the 8 September directive amendment where it originates,
the verification addendum §7, OR-018, RV-03, the RV list at RV-07, the
remediation order, and the process document. Each dated record carries a marker
naming what it originally said, so the correction does not erase the evidence.
The living documents were corrected without a marker.

`RV-08` records the fabrication, its direction — wrong in the way that flattered
the original error — and that it was found by the rule 13 verification rather
than by any check or either author. The process document carries the lesson
beside failure 14: *a wrong number that looks right propagates further than a
wrong argument*, because an argument invites scrutiny and a plausible figure
invites copying.

Standing rule 13 gains: *a verifier does not edit what they are verifying. A
discrepancy is reported and returned; the correction is a separate act by a
separate hand, and is itself subject to verification.* That is why the corrections
above were made only after the ruling came back, and why this amendment is
separated from the findings rather than folded into them.

**Re-checked:** the corrected figure and the 484 offset present in RV-03; the
`2,116` marker present so the evidence survives; RV-08 present. Three checks,
all pass.

## B — Outstanding items 2 and 4 updated

Both now read CLOSED with the date and what closed them. Item 4 also corrects its
own count: six paragraphs were misdated, not four — the diff found three under
28 August and one inside the 2 September entry, and reading every paragraph
against its heading found two more, one of which was ruled to stay as a signposted
forward reference.

The section now opens by saying what it is: *state, not a record*. The process
document §13 carries the general form — a dated finding must not be retro-edited,
a live status list must be kept current, and failing to update state is as much a
falsification as editing a record. That gap is why item 1 was updated while 2 and
4 were not: the maintainer had a rule against editing and none requiring it.

**Re-checked:** both items read CLOSED, the state-vs-record header present. Three
checks, all pass.

## C — dated notes appended to OR-003 and OR-012

Neither entry was rewritten. Both keep their original Change blocks, quoting the
wording decided on 8 September, with a dated note recording that the page wording
moved afterwards, why, and where that is recorded. OR-012's note carries the
entry-level pointer the ruling asked for: its removal is recorded **only** at
round level in the `ROUND-2026-09-08` change set, with no entry-level decision,
which is why the trail was hard to follow.

**Re-checked:** both notes present, both original Change blocks intact and still
quoting the superseded wording, and the page still carries the substance of both
ACCEPTs. Seven checks, all pass.

## The KOL Pulse box — recorded, not edited

Two independent automated misreadings of one passage in two runs is a signal
about the prose. It is a structural note in `docs/whatholdsup-open-gaps.md` for
the next revision, with what closing it looks like: state the turn near the top,
so a reader knows what the enumeration is evidence for before reading it. The
prose was not touched — restructuring a twice-misread passage at the last moment
is how a further error gets in.

## State after the amendment

The page did not move: `7ae5304cf5b7313b`, unchanged through the amendment. Every
change here is to the record. Gate state is unchanged from the section above —
all green except `corrections not yet read` for S029, open by ruling.

Thirteen re-checks across A, B and C, all pass. No new discrepancy.
