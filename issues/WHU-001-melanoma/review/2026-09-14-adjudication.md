# WHU-001 — ROUND-2026-09-14

## ROUND-2026-09-14

**What was asked.** The outside-review check reports 287 changes since the
review of a788f00a with no decision behind them, and blocks.

**What the 287 actually are.** 323 sentence-level changes have occurred since
the 4 September snapshot; 36 carry per-change entries. Of the remaining 287:

- 280 lie inside a788f00a → 76703fe9, the span ROUND-2026-09-10 examined and
  decided. They are unlinked, not undecided: that set is pinned to to_sha
  76703fe9, and a pinned set stops covering the moment the page changes by a
  byte. Two record-live rows on 10 September and the 12-13 September work moved
  it past the pin.
- 4 are sentence-splitter fragments of one paragraph — the EORTC 18071 erratum
  sentence — already decided under ERRATUM-001.
- 3 are sentences touched more than once end to end.

Of the 35 changes made on 12-13 September, 31 cite a decision already on the
record: 25 to ERRATUM-001 (review/2026-09-11-erratum-read-adjudication.md) and
6 to AD-HOC entries naming the 12 September modest-promise ruling. The
remaining 4 are the sentence-splitter fragments of the erratum paragraph
named above ("Dr. / Jedd D. / Wolchok's disclosures…"), decided under
ERRATUM-001 and unlinked only because the splitter breaks that paragraph at
"Dr." and "D."

**The decision.** Keep. The reasoning covering this span exists in the
documents named below and was made at the time. What was missing is the
linkage, not the judgement. I have read the partition above and I accept that
the span a788f00a → 58c28929 is accounted for by those documents, and I am
recording that as a change set so the record says what was already true.

**What would overturn this.** Any of the 287 changes turning out to fall
outside the spans described — in particular any change to the assessment's
argument between 10 and 13 September that is not covered by ERRATUM-001 or the
modest-promise ruling. The partition above is falsifiable by re-running
reconcile against the named shas.

**Signed:** Fred Ugast, 14 September 2026.

---

**Filing note — descriptive, not adjudicative. Nothing below is covered by the
signature above.** Written by the assistant that filed the section, 14
September 2026. The signed section is the operator's text as approved
("Keep, signed Fred Ugast; new file review/2026-09-14-adjudication.md"), with
only the decision word and the signature line filled in as instructed. It
carries no `##` heading of its own so that it creates no decision label.

*Why this file exists.* The publish reconciliation requires every change to a
published page to cite a decision that resolves to something a person can open
and read. The set that covered this page's changes since the 4 September review
— ROUND-2026-09-10 — is pinned to a content hash the page has moved past. The
signed section records that the span is accounted for; the change set in
changes.json cites it.

*The documents the change set names as `decided_by`.*
review/2026-09-14-adjudication.md (this file);
review/2026-09-08-adjudication.md (ROUND-2026-09-08 and ROUND-2026-09-10);
review/2026-09-10-the-140-ruling.md;
review/2026-09-10-melanoma-coverage-ruling.md;
review/2026-09-10-changelog-correction-ruling.md;
review/2026-09-11-erratum-read-adjudication.md (ERRATUM-001);
issues/WHU-003-deskilling/review/2026-09-12-modest-promise-ruling.md.
The signed section says "the documents named below"; at the time of approval
the list lived in the change-set draft, and it is reproduced here so the
reference resolves.
