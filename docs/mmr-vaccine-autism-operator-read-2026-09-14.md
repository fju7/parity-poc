# mmr-vaccine-autism — operator read, 2026-09-15 (final, record 0e25a32)

One page, for the human read the design requires (§6a) before any flip. Record `20260915T190740+0000-0e25a32`, gate `7338993` (tree `0e25a32`), stored in `topic_publications` and served to the draft page. This is the build finished: CHRONOLOGY, the publish gate on already-changed sources, the erratum precision check, the two retracted markers, the corpus corrections 081–083, the six refused plain summaries (088–089), the word-form figure rule, and two hand-fetched documents admitted under `OPERATOR_SUPPLIED`.

**31 of 35 sources survive · 63 claims figure-bound · 43 source-confirmed only (34%) · 22 withheld.** Status of survivors at freeze: Wakefield 1998 ×2 retracted (subject-only on the page), Jain 2015 ×2 corrected (JAMA erratum), the Lancet retraction notice (a `retraction_notice` about Wakefield 1998), 6 agency/payer documents with no status registry, 20 unchanged — Cochrane is now cited at its current version, pub5. **Two survivors were fetched by a person, not the machine**, and the record says so on each: the Lancet retraction notice (sha256 `b70a2200…`) and Deer's BMJ investigation (`79373a9f…`), both supplied by Fred Ugast on 2026-09-15 after the registry's title was found in the file. Seven claims moved on them; none moved the other way.

> The two records before this one: `22387c7` (29 of 35, 58/41/29 — the word-form fix, no supplied documents) and `b902246` (26 of 35 — Europe PMC stopped answering mid-run; kept, not signed). Still pending: migration 090 (Godlee's editorial as a source, the 'elaborate fraud' claim re-cited to it; Walker-Smith v GMC as a source) — after it, one more re-freeze and this page changes again.

**Sign-off:** the freeze register has a pending row. Reader name, date and ruling go there either way.

## What changed since the 14 Sep read

* **Two documents the machine could not get were fetched by hand and admitted** (`verify/supplied.py`): the Lancet retraction notice (Elsevier serves the machine a shell) and Deer's BMJ investigation (403). Admission required the registry's title to be found in the file; binding then ran unchanged. The notice recovers "paid by lawyers … 1998" (figure-bound on the date), "full retraction … in February 2010" (month precision; "struck off in May 2010" stays withheld — the notice predates it), and two identity-only claims (the GMC findings; "removed the primary published basis"). Deer recovers the £435,643, the "all 12 children" data-alteration claims. The notice says "incorrect" and "proven to be false", not fraud; nothing on the page makes it say more. 'an elaborate fraud' is Godlee's editorial, not Deer's feature: SPAN refused it against Deer and it waits on migration 090.
* **A bare "one" or "zero" in a claim is no longer a figure** (gate 7338993). "one of the strongest natural experiments" is an article; "vaccination rates dropping to zero" asserts absence. Three claims recover: the Honda "strongest natural experiments" claim (source-confirmed only), and the two Yokohama "dropped to zero after the 1993 withdrawal" claims (figure-bound). The fourth, "…rose from 48.4 to 117.2 per 10,000, despite zero MMR vaccination", stays withheld — for the right reason now: 48.4, 117.2 and 10,000 are not in the abstract. No bound claim became unbound. "one dose", "zero cases" and every other counting word are unchanged.
* **Two withholdings re-described** (section 3): the RR 0.92 claims say the upper bound is 1.26; Madsen 2002's abstract says 1.24. That is not a retrieval limit — the claim's figure disagrees with the source's — and it is the gate's best result on this record.
* **Six plain summaries removed** (088, 089): four added a fact the claim and source do not carry, one computed an interval the summariser was never handed, one sat on a withheld claim. The claims render without them.
* **Cochrane cited at pub5** (migration 083; DOI from Crossref's own update-to, not typed). All nine claims re-bind against the current review — 5 figure-bound (138 studies; 23,480,668 participants; 95% and 96% measles risk reduction), 4 source-confirmed. None was refused, so the refusal on pub4 was a citation problem and nothing more. One wording defect no gate can catch: the sentence "The Cochrane systematic review … published in 2020" now cites the 2021 version; it should say 2021 or drop the date.
* **Erratum precision** (support links only): the erratum is fetched and asked whether it mentions a figure the claim asserts. For Jain 2015 the erratum — *"Incorrect Variable Description"*, JAMA 2016, `10.1001/jama.2015.17754` — is behind JAMA's Cloudflare wall and Europe PMC holds no text, so it **cannot be read, and the check fails closed**: the two support-link claims (the sibling HR 0.80 findings) stay withheld with that reason. Six Jain claims that name the study are subject links and pass. Its title suggests a variable-description fix, not a figure — but a title is not the text, and the rule does not guess. A reviewer who can open the erratum can settle it in a minute.
* **CHRONOLOGY:** the three GMC / struck-off claims are withheld — true, but the 1998 paper cannot contain the GMC's 2010 findings.
* The red RETRACTED marker now only ever means "changed after we froze it"; at freeze a retracted paper appears only as the subject of a claim, with a grey information note.

## 1. The scope statement, exactly as it will appear under the title

> This page covers the epidemiological evidence on MMR vaccination and autism. The retraction of Wakefield 1998, the General Medical Council findings and the Omnibus Autism Proceeding are matters of record that this page cites but does not itself document; see the sources marked retracted.

## 2. Thirteen IDENTITY_ONLY claims, weakest first (of 43) — each will carry *"Source confirmed; wording not machine-checked"*

- The UK General Medical Council found that the Wakefield et al. research involved undisclosed financial conflicts of interest, ethical violations in the treatment of child subjects (including invasive procedures without ethical approval), data manipulation, and dishonesty — constituting serious professional misconduct.  
  ← Retraction—Ileal-lymphoid-nodular hyperplasia… (The Lancet, 2010)  *(recovered on the hand-fetched notice; the notice says "incorrect" and "proven to be false" about consecutive referral and ethics approval — it does not say "data manipulation" or "dishonesty", and the GMC findings on ethics approval were quashed for Walker-Smith in 2012: see the wording list)*
- The retraction of the Wakefield et al. paper removed the primary published basis for the MMR-autism hypothesis.  
  ← Retraction—Ileal-lymphoid-nodular hyperplasia… (The Lancet, 2010)  *(recovered; editorial framing — the notice retracts, it does not say what the paper was the basis of)*
- The Honda et al. Japan study is considered one of the strongest natural experiments disproving a causal link between MMR vaccine and autism.  
  ← No effect of MMR withdrawal on the incidence of autism: a total population study  *(recovered at gate 7338993; "one of" was read as a figure)*
- The Madsen et al. Danish cohort study was published in the New England Journal of Medicine.  
  ← A Population-Based Study of Measles, Mumps, and 
- The Danish cohort study on MMR vaccination and autism was published in Annals of Internal Medicine.  
  ← Measles, Mumps, Rubella Vaccination and Autism: 
- ACIP recommendations carry regulatory weight as they inform the Vaccines for Children program and state immunization mandates.  
  ← Advisory Committee on Immunization Practices (AC
- The Institute of Medicine convened an independent Immunization Safety Review Committee that conducted a comprehensive review of all available epidemiological and biological evidence on the MMR–autism and thimerosal–autism hypotheses, and is described as the most authoritative U.S. government-commissioned scientific review of the MMR-autism controversy.  
  ← Immunization Safety Review: Vaccines and Autism; Immunization Safety Review: Vaccines and Autism 
- Anti-vaccine advocates conflated concerns about thimerosal with the separate MMR-autism hypothesis advanced by Wakefield.  
  ← FDA Statement Regarding the MMR Vaccine and Thim
- M-M-R II has never contained thimerosal as a preservative; the vaccine uses a live attenuated formulation incompatible with preservative use.  
  ← FDA Statement Regarding the MMR Vaccine and Thim
- The EMA's EPAR notes that the original Wakefield hypothesis was not substantiated by subsequent large-scale epidemiological studies conducted in Europe, including the Danish cohort study by Madsen et al.  
  ← European Medicines Agency: M-M-RvaxPro — Europea
- Multiple large-scale epidemiological studies reviewed by ACIP found no association between MMR vaccination and autism spectrum disorder.  
  ← Advisory Committee on Immunization Practices (AC
- The Institute of Medicine's Immunization Safety Review Committee concluded that the epidemiological evidence consistently and convincingly favors rejection of a causal relationship between MMR vaccine and autism.  
  ← Immunization Safety Review: Vaccines and Autism 
- The biological mechanisms proposed by Wakefield — including measles virus persistence in gut tissue and 'leaky gut' leading to neurological damage — were not supported by credible scientific evidence, according to the Institute of Medicine's Immunization Safety Review Committee.  
  ← Immunization Safety Review: Vaccines and Autism; Immunization Safety Review: Vaccines and Autism 

Trivia ("was published in…"), editorial framing ("anti-vaccine advocates conflated…", "carry regulatory weight", "one of the strongest"), and agency prose the fetch confirms exists but nothing anchors. 34%; should trend down by rewriting.

## 3. All 22 withheld claims, one line each

- The Omnibus Autism Proceeding ruling rejected both the 'MMR plus thimerosal' causation theory and the standalone MMR-autism theory, finding that epid…  
  WHY: source unretrievable: Omnibus Autism Proceeding: Special M (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- Among children with an older sibling with ASD, MMR vaccination was not associated with increased autism risk, with a hazard ratio of 0.80 (95% CI 0.5…  
  WHY: ERRATUM unreadable: erratum text could not be read (unretrievable (publisher HTTP 203)); it cannot b
- The Danish cohort study found no temporal clustering of autism diagnoses in the 2-year period following MMR vaccination.  
  WHY: figure not in abstract: 2
- A Danish cohort study followed 537,303 children born between 1991 and 1998, comparing autism rates between 440,655 MMR-vaccinated and 96,648 unvaccin…  
  WHY: figure not in abstract: 96648
- Among children born in Yokohama between 1992 and 1996, the cumulative incidence of autism by age 7 rose from 48.4 to 117.2 per 10,000, despite zero M…  
  WHY: figure not in abstract: 10000, 117.2, 48.4
- The relative risk of autism in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.26), indicating no increased risk o…  
  WHY: **the source states a different value** — Madsen 2002 (NEJM) abstract: 0.92 (95% CI, 0.68 to **1.24**); the claim says **1.26**. The claim's figure disagrees with the source's and the gate refused it correctly; it stays withheld until the sentence is corrected.
- FDA product labeling for M-M-R II lists known adverse reactions including fever, rash, and rare febrile seizures, but does not list autism spectrum d…  
  WHY: source unretrievable: Biologics License Application (BLA)  (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- The cumulative incidence of autism spectrum disorders in Yokohama rose from 47.6 per 10,000 in the 1988 birth cohort to 117.2 per 10,000 in the 1996 …  
  WHY: figure not in abstract: 10000, 117.2, 47.6
- Ten of the thirteen co-authors of the Wakefield et al. paper formally withdrew their names from the paper's interpretation in 2004.  
  WHY: CHRONOLOGY: explicit date 2004
- Children with an older autistic sibling showed no increased autism risk from MMR vaccination, refuting concerns about genetically susceptible subgrou…  
  WHY: ERRATUM unreadable: erratum text could not be read (unretrievable (publisher HTTP 203)); it cannot b
- The relative risk of autistic disorder in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.26), indicating no stati…  
  WHY: **the source states a different value** — Madsen 2002 (NEJM) abstract: 0.92 (95% CI, 0.68 to **1.24**); the claim says **1.26**. The claim's figure disagrees with the source's and the gate refused it correctly; it stays withheld until the sentence is corrected.
- The Danish cohort study included 440,655 MMR-vaccinated children and 96,648 unvaccinated children, finding no statistically significant difference in…  
  WHY: figure not in abstract: 2, 96648
- The temporal clustering of autism diagnoses with MMR vaccination timing reflects the coincidence of the 12–18 month vaccination window with the typic…  
  WHY: figure not in abstract: 12, 18
- M-M-R II (BLA 103166), manufactured by Merck & Co., has maintained FDA licensure continuously since 1978 with periodic label updates.  
  WHY: source unretrievable: Biologics License Application (BLA)  (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- Post-marketing safety update reviews of M-M-R II conducted by FDA's Center for Biologics Evaluation and Research (CBER) have not identified a causal …  
  WHY: source unretrievable: Biologics License Application (BLA)  (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- The Omnibus Autism Proceeding involved approximately 5,500 claims filed in the Vaccine Injury Compensation Program alleging that MMR vaccination caus…  
  WHY: source unretrievable: Omnibus Autism Proceeding: Special M (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- Special Master George Hastings ruled that petitioners had not demonstrated by a preponderance of evidence that MMR vaccine caused autism in the test …  
  WHY: source unretrievable: Omnibus Autism Proceeding: Special M (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- Andrew Wakefield was struck off the UK medical register following the General Medical Council findings.  
  WHY: CHRONOLOGY: General Medical Council fitness-to-practise determination on Wakefield, Walker-S
- Andrew Wakefield was struck off the UK medical register in May 2010.  
  WHY: CHRONOLOGY: explicit date 2010-05
- The Wakefield et al. study was found to have involved data manipulation, undisclosed conflicts of interest, and ethical violations in subject recruit…  
  WHY: CHRONOLOGY: General Medical Council fitness-to-practise determination on Wakefield, Walker-S
- Special Master Hastings characterized the scientific evidence presented by petitioners — including testimony based on Wakefield's research — as 'weak…  
  WHY: source unretrievable: Omnibus Autism Proceeding: Special M (fetch: HTTP 404); SOURCE: fetch: HTTP 404
- The BMJ formally characterized the 1998 Lancet paper by Wakefield as 'an elaborate fraud' in an editorial by editor Fiona Godlee, marking the first t…  
  WHY: SPAN: not in the document: 'an elaborate fraud'

## 4. The two retracted markers, in page context

A — the retracted work is the subject (the only surviving Wakefield-linked claim; grey note). B — the support case, illustrative: no claim on this record rests on a retracted source, so B can only appear from a re-check after publication (red block).

![Subject and support markers side by side](mmr-vaccine-autism-markers-side-by-side-2026-09-14.png)

## 5. Link roles — the audit trail

63 subject links, 62 support links, each with the rule that fired on the record (first author's surname, or the title word — `thimerosal`, `montreal`, `withdrawal`, `regression`, `siblings`, `pervasive`, `medicines` — or nothing). The title-word matches are the ones to watch; each is traceable to the word.
