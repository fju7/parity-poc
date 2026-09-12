# WHU-001 — changes made after publication, 11 September 2026

Not a review. As with `2026-08-29-nav-adjudication.md`, this file exists
because the publish reconciliation requires every change to a published page to
cite a decision that resolves to something a person can open and read. The
decision it resolves is the standing one in `2026-09-09-erratum-ruling.md`:
"S029 keeps an open errata item until the notice is read. If it is ever
obtained and it touches a figure on this page, that is a correction and it goes
in the log like any other."

## ERRATUM-001 — the 2018 erratum to EORTC 18071 has been read, and it touches nothing here

**What changed.** In the reader-facing source list, the entry for Eggermont et
al. (EORTC 18071, S029) no longer says the 2018 erratum could not be read. It
says the notice has been read; that in full it updates the disclosures of one
author, Jedd D. Wolchok, and states the articles are correct at NEJM.org; that
it changes no result, method or figure and touches nothing on this page; and
that our held copy of the paper is the PubMed Central full text, which may carry
the disclosure as it stood before the update. The erratum's link now goes to the
notice itself (https://www.nejm.org/doi/full/10.1056/NEJMx180040) rather than to
its PubMed record. The masthead date is 11 September 2026.

**Why.** The notice was obtained on 11 September 2026 from nejm.org in a
browser and is held as S031, verified as the document by its content (one page;
/Subject "N Engl J Med 2018.379:2185-2185"; /CreationDate D:20181115141649;
folio 2185; thirteen "(N Engl J Med 20.." citations; the two verbatim passages;
no correction-of-substance language). After its list of thirteen articles —
ours as "Prolonged Survival in Stage III Melanoma with Ipilimumab Adjuvant
Therapy (N Engl J Med 2016;375:1845-1855)" — its complete operative text is one
sentence: "Dr. Jedd D. Wolchok's disclosures have been updated, and the
articles are correct at NEJM.org."

**What was wrong, and whose.** The 9 September records (S029 erratum_note,
S030 note, the corrections entry of that date) said the notice was
subscription-only. That was an inference from an HTTP 403 returned to a script.
NEJM serves a Cloudflare bot challenge to scripts; the notice and its PDF are
freely readable in a browser without a subscription. The inference was ours and
is withdrawn in every record that carried it. The page's own sentence — "We
have not been able to read it: NEJM returns 403 …" — was true of a script when
written and is now superseded.

**Effect on this assessment.** None on any figure. Every figure this page quotes
from S029 — 65.4% vs 54.4%, HR 0.72, 95.1% CI 0.58 to 0.88, P=0.001, the
10 mg/kg dose, five immune-related deaths — is unaffected by a disclosure
update. The standing errata debt against S029 is closed by S031; the residual
(the pre-update disclosure in our held PMC copy) is recorded in S029's
erratum_note and on the page.

**Records changed.** sources.json (S031 added with `amends: S029`; S029
erratum_note and S030 notes rewritten); the library (S031 ingested); bindings
(the erratum sentence rebound from S030 to S031, one row added for the
disclosure sentence); deletions.json (403 recorded as superseded by S031);
figure-exclusions.json (the 403 exclusion retired with its sentence);
errata.json (S031 looked up).

**Recorded for readers** in `corrections.md`, 11 September 2026.
