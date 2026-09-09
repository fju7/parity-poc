# Ruling — the S029 erratum

**Option (b), strengthened: publish, and say it on the page rather than only in
the record.** Not (a) — I tried and it is closed. Not (c) — removing the
counterexample would be a worse error than the one being guarded against.

---

## First: this was my miss, and it was in front of me

The erratum notice was in the PubMed output I fetched when I supplied EORTC
18071. I quoted the abstract's figures out of that same response and did not
read the field four lines above them:

```
Erratum in
    N Engl J Med. 2018 Nov 29;379(22):2185. doi: 10.1056/NEJMx180040.
```

Seventh instance of the same failure: I took the part of a document I wanted and
did not attend to the field that qualified it. **RV-07**, and it belongs in the
adjudication.

One thing distinguishes it from the other six, and it is the good news in this
report: the previous six were caught by a reader opening an artifact. This one
was caught by `errata.py` running on its own. The machinery found what the
reviewer missed, which is the reverse of the pattern this cycle has otherwise
shown, and it is worth recording as evidence that the errata check earns its
keep.

---

## What I established, and what I did not

**Confirmed independently.** The erratum exists, is PMID 31442371, and covers
`10.1056/NEJMoa1611299` — our paper — as one of **thirteen** NEJM articles in a
single notice.

**Could not obtain.** NEJM returns 403. Europe PMC: `isOpenAccess N`, `inEPMC N`.
Crossref carries title and date only, no abstract, and its `update-to` field is
absent. PubMed carries the coverage list and no notice text. Your finding stands
in full.

**An inference, labelled as one and not load-bearing.** The thirteen papers span
2013–2018, are all melanoma or immunotherapy, and come from heavily overlapping
author groups. Thirteen papers do not simultaneously have arithmetic wrong; what
they share is people. A bulk notice of that shape is characteristic of a
disclosure or conflict-of-interest correction rather than a data correction.

That is a pattern argument. It is not a reading of the notice, it is exactly the
kind of reasoning I have been wrong with six times this week, and **it is not the
basis of this ruling.** I record it because it bounds expectation, not because it
closes anything.

---

## Why not (c) — remove the counterexample

Removing EORTC 18071 would restore the impression OR-008 exists to correct: that
no adjuvant checkpoint inhibitor has shown a survival benefit against placebo in
this disease. One has. Deleting a true and well-sourced counterexample on the
strength of an unread notice that probably concerns disclosures would be
over-correction driven by an unknown — a different failure from the one being
guarded against, and a worse one, because it removes accurate information from
readers to protect the publication's comfort.

The test that settles it: **does the page's claim depend on anything the erratum
could plausibly have changed?** The page says one adjuvant checkpoint inhibitor
reported an OS benefit against placebo as a prespecified secondary endpoint, at a
dose and toxicity that kept it from becoming standard care. That claim survives
any decimal-level correction to 0.72 or 65.4%. It would only fall if the erratum
retracted the survival finding, and a retraction is not issued as one line in a
thirteen-paper notice.

---

## Why (b) has to be strengthened

Recording it in `corrections.md` and the source entry is where the machinery
wants it. That is not sufficient here, because this is the page's own subject.

A publication whose argument is that readers should be told what the evidence
does and does not establish, holding a paper whose correction it cannot read,
should say so **where the reader is**. Not as an apology — as the piece doing the
thing it asks of others. The 2 September entry already established the principle
in the reverse direction: our failure to find a document was never evidence it
did not exist. This is the same principle pointed forward.

**Add to the S029 source note, in the reader-facing list:**

> A 2018 erratum covering thirteen NEJM articles at once (N Engl J Med
> 2018;379:2185) applies to this paper. We have not been able to read it — the
> notice is paywalled and carries no abstract — so we do not know whether it
> touches anything quoted here. Every figure we quote appears in the current
> PubMed record of this paper, which post-dates the erratum.

That last sentence is corroboration and is labelled as corroboration. It is not
a claim to have read the notice.

**And record the standing debt.** S029 keeps an open errata item until the notice
is read. If it is ever obtained and it touches a figure on this page, that is a
correction and it goes in the log like any other.

---

## Three smaller rulings from your report

**Spruance PMID.** Correct handling. The page asserts PMID 15273082 and that
string is not in the held bytes; the PMCID is corroborated by the fetch URL. A
PMID is a catalogue identifier rather than a claim about content, so this does
not block — but leave it recorded as unverified rather than quietly promoting it.
Do not remove the PMID; an identifier we believe correct and have labelled
unverified is more useful to a reader than no identifier.

**The b13 bug.** Good find and the right fix. Two checks reading one file with
two notions of "used", one filter further out — and you verified the repair still
catches a genuinely dead entry rather than just going green. That regression test
is the part that matters. Worth a line in the open-gaps document: the class of
bug is "a staleness test evaluated against the same narrowed view that created
the staleness," and it will recur wherever two checks share a source and differ
on scope.

**The KOL Pulse CONTRADICTION.** Your disposition is right and the way you
disposed of it is better than the disposition. The claim is sound — different
subjects, both spans verified — but an automated reader collapsed the two
clauses and a human might. Recording the style objection instead of only
dismissing the flag is the correct instinct. Leave the sentence; the compression
is defensible and the objection is now on the record for whoever reads it next.

---

## Proceed

Apply the S029 source note and the standing errata debt, add RV-07 to the
adjudication, re-run the gates, then produce the verification record and stop for
the operator's acceptance and confirm-review.

```
STEP 3b — then step 4.

1. Add to the S029 reader-facing source note the erratum paragraph in
   2026-09-09-erratum-ruling.md. It states that a 2018 thirteen-article NEJM
   erratum applies, that we have not read it and why, that we do not know whether
   it touches anything quoted, and that every figure quoted appears in the
   current PubMed record which post-dates it. The last sentence is corroboration
   and must read as corroboration, not as closure.

2. Keep the S029 errata item OPEN as a standing debt rather than dispositioning
   it. If the notice is ever obtained and touches a figure on this page, that is
   a correction and goes in the log.

3. Add RV-07 to the adjudication: the reviewer supplied EORTC 18071 and missed
   the erratum field printed four lines above the abstract figures quoted from
   the same response. Seventh instance of the same failure — taking the part of a
   document wanted and not attending to the field qualifying it. Note that unlike
   RV-01 to RV-06 this one was caught by errata.py rather than by a reader.

4. Spruance PMID stays, recorded as unverified. Do not promote or remove it.

5. Add to docs/whatholdsup-open-gaps.md: a staleness test evaluated against the
   same narrowed view that created the staleness will report a live entry as
   dead. It will recur wherever two checks share a source file and differ on
   scope. Cite the b13 / corrections_check case and the regression test.

6. Re-run all gates. If green, produce the verification record as specified in
   step 4 and stop for the operator.
```
