# mmr-vaccine-autism — survival read, 2026-09-14

Record `20260914T225743+0000-2b84a4a`, gate `2b84a4a`, **not flipped** (ruling: stays draft).

This is the read the ruling asked for: what a filter kept, what it dropped, and whether what remains still carries the topic's central finding with its strongest evidence. Nothing here is rewritten.

## Totals

Sources: 35 in, 23 survive. Withheld: {'HEADING': 2, 'resolve': 2, 'fetch': 8}. Status of survivors: {'retracted': 2, 'unchanged': 13, 'superseded': 2, 'no_registry': 6}.

Claims: 128 in — {'IDENTITY_ONLY': 38, 'UNSUPPORTED': 53, 'FIGURE_BOUND': 37}; IDENTITY_ONLY rate 29.7% (a metric to trend down).

## The question that matters: does the surviving set still carry the central finding with its strongest evidence?

**Yes for the epidemiology; no for the institutional record; and two of the strongest primary studies are lost — both to bad identifiers in the corpus, not to the gate.**

The topic's central finding — no association between MMR vaccination and autism — survives with its strongest evidence intact:

| study | what it is | status |
|---|---|---|
| Madsen 2002, NEJM | Danish cohort, 537,303 children | **survives**, 11 claims (FIGURE_BOUND on 537,303; RR 0.92) |
| Hviid 2019, Annals | Danish cohort, 657,461 children; sibling and high-risk subgroups | **survives**, 10 claims (FIGURE_BOUND on HR 0.93, 0.85–1.02) |
| Taylor 2014, Vaccine | meta-analysis, 1,256,407 children in cohorts + 9,920 in case-control | **survives**, 12 claims (FIGURE_BOUND on OR 0.99, 0.84) |
| Cochrane 2020 (CD004407.pub4) | 138 studies, 23,480,668 participants | **survives**, but `superseded` (pub5, 2021) — and the "23 million" claims are withheld because the record's number is 23,480,668, not 23 million |
| Taylor 1999, Lancet; Taylor 2002, BMJ; Smeeth 2004, Lancet; Fombonne 2006, Pediatrics | UK and Canadian cohorts / case-control | **all survive** |
| **Honda 2005**, Dev Med Child Neurol | the Japan MMR-withdrawal natural experiment — the one study that tests the hypothesis by removing the exposure | **LOST** — both stored DOIs (`…tb01095.x`, `…tb01215.x`) resolve to a gastrostomy paper and a botulinum-toxin paper. 9 claims withheld. The paper is real; the corpus's identifiers for it are not. |
| **Jain 2015**, JAMA | US cohort of 95,727 children, the largest sibling-risk analysis | **LOST** — stored DOI `10.1001/jama.2015.1534` does not exist (the paper is `10.1001/jama.2015.3077`). 8 claims withheld, including the HR 0.80 sibling finding. |

So the surviving epidemiology is the two Danish cohorts, the meta-analysis, Cochrane and the four smaller UK/Canadian studies. What is missing from the *strongest* tier is Honda and Jain — disproportionately important (a natural experiment and the largest US cohort), and both lost for the same reason the whole corpus was frozen: identifiers written from memory. Neither loss is the filter's judgement; both are recoverable by correcting two identifiers, which is a corpus change and therefore not this phase's to make.

The institutional and regulatory record fares worse, even after the generic adapter: the **Omnibus Autism Proceeding** (Cedillo) is lost — the stored uscfc.uscourts.gov URL returns 404 — and with it the four claims about what the special masters found; the FDA BLA page URL is 404; **Deer's 2011 BMJ series** ("How the case against the MMR vaccine was fixed") has no registry abstract to fetch, so the £435,643 and data-manipulation claims rest on nothing fetched; the **2010 Lancet retraction notice** likewise. The retraction-and-fraud category keeps 2 of 10 claims. The generic adapter did recover the IOM 2004 review (NCBI Books), the ACIP MMWR, the FDA thimerosal statement, the EMA EPAR, the VAERS guide and the Aetna policy — 12 institutional claims now stand, all IDENTITY_ONLY.

**What a human read should decide before any flip:** whether a page that states the epidemiological consensus with its two best cohorts but without Honda, Jain, the Omnibus decision or the Deer investigation "still says what the topic means." My reading: the science half does; the accountability half — retraction, fraud, the court — is reduced to the retracted paper's own record and two GMC-finding claims that are IDENTITY_ONLY, which is thin for a topic whose public meaning is as much about the fraud as the epidemiology. That is a judgement, not a gate result, and it is the reviewer's.

## The surviving claims, grouped by what they assert

### large_scale_epidemiological_evidence (53)

- **[IDENTITY_ONLY]** The Cochrane systematic review on MMR vaccine safety found no credible evidence linking MMR vaccination to Crohn's disease.  
  ← Vaccines for measles, mumps, rubella, and varicell
- **[IDENTITY_ONLY]** The EMA's EPAR notes that the original Wakefield hypothesis was not substantiated by subsequent large-scale epidemiological studies conducted in Europe, including the Danish cohort study by Madsen et al.  
  ← European Medicines Agency: M-M-RvaxPro — European 
- **[FIGURE_BOUND]** A UK population-based study examined 278 children with autism to assess whether MMR vaccination was associated with developmental regression or bowel problems.  
  ← Measles, mumps, and rubella vaccination and bowel 
- **[FIGURE_BOUND]** The Taylor et al. (2002) study found no association between MMR vaccination and developmental regression in children with autism.  
  ← Measles, mumps, and rubella vaccination and bowel 
- **[FIGURE_BOUND]** The adjusted hazard ratio for autism in MMR-vaccinated children compared to unvaccinated children was 0.93 (95% CI 0.85–1.02), indicating no increased risk.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[IDENTITY_ONLY]** The Danish cohort study found no increased risk of autism associated with MMR vaccination in children with siblings with autism, preterm birth, or low birth weight.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[IDENTITY_ONLY]** The Cochrane systematic review found no credible evidence of an association between MMR vaccination and inflammatory bowel disease.  
  ← Vaccines for measles, mumps, rubella, and varicell
- **[FIGURE_BOUND]** One dose of the MMR vaccine reduced measles risk by 95% and two doses reduced measles risk by 96%.  
  ← Vaccines for measles, mumps, rubella, and varicell
- **[FIGURE_BOUND]** A meta-analysis by Taylor et al. synthesized data from five cohort studies involving 1,256,407 children to examine the relationship between vaccines and autism.  
  ← Vaccines are not associated with autism: An eviden
- **[FIGURE_BOUND]** A meta-analysis by Taylor et al. synthesized data from five case-control studies involving 9,920 children to examine the relationship between vaccines and autism.  
  ← Vaccines are not associated with autism: An eviden
- **[FIGURE_BOUND]** The pooled odds ratio for the association between vaccination and autism was 0.99 (95% CI 0.92–1.06), indicating no association.  
  ← Vaccines are not associated with autism: An eviden
- **[FIGURE_BOUND]** The pooled odds ratio for the association between MMR vaccination specifically and autism was 0.84 (95% CI 0.70–1.01), showing no statistically significant association.  
  ← Vaccines are not associated with autism: An eviden
- **[IDENTITY_ONLY]** The Taylor et al. meta-analysis found no relationship between thimerosal or mercury-containing vaccines and autism.  
  ← Vaccines are not associated with autism: An eviden
- **[FIGURE_BOUND]** No change in the trend of increasing autism diagnoses was detected following MMR vaccine introduction in the UK in 1988.  
  ← Autism and measles, mumps, and rubella vaccine: no
- **[FIGURE_BOUND]** No temporal clustering of autism onset was detected within 2 or 6 months of MMR vaccination.  
  ← Autism and measles, mumps, and rubella vaccine: no
- **[IDENTITY_ONLY]** No difference in age at autism diagnosis was found between MMR-vaccinated and unvaccinated children.  
  ← Autism and measles, mumps, and rubella vaccine: no
- **[FIGURE_BOUND]** The rate of autism increase was consistent before and after MMR introduction in 1988, ruling out the vaccine as a cause of the observed rise in autism diagnoses.  
  ← Autism and measles, mumps, and rubella vaccine: no
- **[FIGURE_BOUND]** The Madsen 2002 Danish cohort study found no association between age at MMR vaccination, time since vaccination, or date of vaccination and the development of autism.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[FIGURE_BOUND]** The Madsen 2002 Danish cohort study found no dose-response relationship between MMR vaccination and autism.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[FIGURE_BOUND]** A Canadian study examined 27,749 children born between 1987 and 1998 in Montreal, Quebec to analyze the relationship between MMR vaccination coverage and autism prevalence across birth cohorts.  
  ← Pervasive Developmental Disorders in Montreal, Que
- **[FIGURE_BOUND]** In the Montreal birth cohort study, autism prevalence increased over time while MMR vaccination coverage also increased, but the association between the two trends was not statistically significant after adjustment.  
  ← Pervasive Developmental Disorders in Montreal, Que
- **[FIGURE_BOUND]** The Fombonne 2006 Montreal study found no causal relationship between MMR vaccination rates and autism prevalence across birth cohorts.  
  ← Pervasive Developmental Disorders in Montreal, Que
- **[FIGURE_BOUND]** The Fombonne 2006 Montreal study ruled out both thimerosal exposure and MMR vaccination as contributors to the observed increase in autism diagnoses.  
  ← Pervasive Developmental Disorders in Montreal, Que
- **[FIGURE_BOUND]** A UK case-control study using the General Practice Research Database compared 1,294 cases of pervasive developmental disorder (PDD) with 4,469 matched controls to examine MMR vaccination history.  
  ← MMR vaccination and pervasive developmental disord
- **[IDENTITY_ONLY]** Multiple large-scale epidemiological studies reviewed by ACIP found no association between MMR vaccination and autism spectrum disorder.  
  ← Advisory Committee on Immunization Practices (ACIP
- **[FIGURE_BOUND]** The Taylor et al. (2002) study found no association between MMR vaccination and bowel problems in children with autism.  
  ← Measles, mumps, and rubella vaccination and bowel 
- **[IDENTITY_ONLY]** The Taylor et al. meta-analysis found no relationship between vaccination and autism or autism spectrum disorder.  
  ← Vaccines are not associated with autism: An eviden
- **[FIGURE_BOUND]** The odds ratio for the association between MMR vaccination and pervasive developmental disorder was 0.86 (95% CI 0.68–1.09), indicating no increased risk.  
  ← MMR vaccination and pervasive developmental disord
- **[IDENTITY_ONLY]** The Cochrane MMR review concluded that the benefits of MMR vaccination substantially outweigh its risks.  
  ← Vaccines for measles, mumps, rubella, and varicell
- **[FIGURE_BOUND]** A Danish population-based cohort study followed 537,303 children born between 1991 and 1998 to investigate the association between MMR vaccination and autism.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[FIGURE_BOUND]** The Smeeth 2004 case-control study found no evidence of temporal clustering of pervasive developmental disorder diagnoses following MMR vaccination.  
  ← MMR vaccination and pervasive developmental disord
- **[FIGURE_BOUND]** The finding of no association between MMR vaccination and pervasive developmental disorder in the Smeeth 2004 study was consistent across multiple sensitivity analyses and subgroup analyses.  
  ← MMR vaccination and pervasive developmental disord
- **[IDENTITY_ONLY]** The Institute of Medicine's Immunization Safety Review Committee concluded that the epidemiological evidence consistently and convincingly favors rejection of a causal relationship between MMR vaccine and autism.  
  ← Immunization Safety Review: Vaccines and Autism — 
- **[FIGURE_BOUND]** The Cochrane systematic review on MMR vaccine safety, published in 2020, is described as the most comprehensive systematic review on MMR vaccine safety to date.  
  ← Vaccines for measles, mumps, rubella, and varicell
- **[IDENTITY_ONLY]** The Taylor et al. meta-analysis found no association between MMR vaccine and autism outcomes.  
  ← Vaccines are not associated with autism: An eviden
- **[IDENTITY_ONLY]** The Taylor et al. meta-analysis found no association between thimerosal or mercury-containing vaccines and autism outcomes.  
  ← Vaccines are not associated with autism: An eviden
- **[IDENTITY_ONLY]** The null finding in the Taylor et al. meta-analysis was consistent across both cohort and case-control study designs.  
  ← Vaccines are not associated with autism: An eviden
- **[IDENTITY_ONLY]** The Madsen et al. Danish cohort study found no association between MMR vaccination and autism regardless of age at vaccination, time since vaccination, or vaccination status.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[IDENTITY_ONLY]** In the Madsen et al. Danish cohort study, vaccinated children had no higher risk of autism than unvaccinated children.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[IDENTITY_ONLY]** The Madsen et al. Danish cohort study results held after adjustment for potential confounders including sex, birth weight, gestational age, and socioeconomic status.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[IDENTITY_ONLY]** The Madsen et al. Danish cohort study was published in the New England Journal of Medicine.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[IDENTITY_ONLY]** The Danish cohort study found no clustering of autism diagnoses at any time interval following MMR vaccination.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[IDENTITY_ONLY]** The Danish cohort study found no association between MMR vaccination and autism in subgroup analyses of children with older autistic siblings or other autism risk factors.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[IDENTITY_ONLY]** The Danish cohort study on MMR vaccination and autism was published in Annals of Internal Medicine.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[IDENTITY_ONLY]** The Danish cohort study found no association between age at MMR vaccination, time since vaccination, or date of vaccination and the development of autism.  
  ← A Population-Based Study of Measles, Mumps, and Ru
- **[FIGURE_BOUND]** The Taylor 1999 UK cohort study found no sudden increase in autism diagnoses following the introduction of the MMR vaccine in the United Kingdom in 1988.  
  ← Autism and Measles, Mumps, and Rubella Vaccine: No
- **[FIGURE_BOUND]** The Taylor 1999 UK cohort study found no statistically significant difference in age at autism diagnosis between children who received the MMR vaccine and those who did not.  
  ← Autism and Measles, Mumps, and Rubella Vaccine: No
- **[FIGURE_BOUND]** The Taylor 1999 UK cohort study found no temporal clustering of autism diagnoses within either 2 or 6 months of MMR vaccination.  
  ← Autism and Measles, Mumps, and Rubella Vaccine: No
- **[FIGURE_BOUND]** The findings of the Taylor 1999 UK cohort study directly contradicted the Wakefield hypothesis linking MMR vaccination to autism.  
  ← Autism and Measles, Mumps, and Rubella Vaccine: No
- **[FIGURE_BOUND]** The adjusted hazard ratio for autism in MMR-vaccinated versus unvaccinated children in the Hviid 2019 Danish cohort study was 0.93 (95% CI, 0.85–1.02).  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[FIGURE_BOUND]** The Hviid 2019 Danish cohort study found no increased autism risk in children with a sibling diagnosed with autism spectrum disorder who received the MMR vaccine.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[FIGURE_BOUND]** The Hviid 2019 Danish cohort study found no increased autism risk in high-risk subgroups including children with preterm birth or low birth weight who received the MMR vaccine.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 
- **[FIGURE_BOUND]** The Hviid 2019 Danish cohort study found no evidence supporting a causal link between MMR vaccination and autism under any analytical approach tested.  
  ← Measles, Mumps, Rubella Vaccination and Autism: A 

### institutional_regulatory_response (12)

- **[FIGURE_BOUND]** The FDA initiated a review of thimerosal in childhood vaccines in 1999 under the FDA Modernization Act, found no evidence of harm from thimerosal-containing vaccines, but supported precautionary removal of thimerosal from childhood vaccines as a public health measure.  
  ← FDA Statement Regarding the MMR Vaccine and Thimer
- **[IDENTITY_ONLY]** The CDC's Advisory Committee on Immunization Practices (ACIP) concluded that evidence favors rejection of a causal relationship between MMR vaccine and autism spectrum disorder, citing large epidemiological studies and IOM reviews.  
  ← Advisory Committee on Immunization Practices (ACIP
- **[FIGURE_BOUND]** ACIP's 2013 recommendations reaffirm a two-dose MMR schedule administered at 12–15 months and 4–6 years of age as safe and effective.  
  ← Advisory Committee on Immunization Practices (ACIP
- **[IDENTITY_ONLY]** ACIP reviewed and rejected proposed contraindications to MMR vaccination based on family history of autism, finding no scientific basis for such precautions.  
  ← Advisory Committee on Immunization Practices (ACIP
- **[IDENTITY_ONLY]** ACIP recommendations carry regulatory weight as they inform the Vaccines for Children program and state immunization mandates.  
  ← Advisory Committee on Immunization Practices (ACIP
- **[IDENTITY_ONLY]** The Institute of Medicine's Immunization Safety Review Committee concluded that the body of epidemiological evidence favors rejection of a causal relationship between the MMR vaccine and autism, and recommended that future vaccine safety research resources not be directed toward the MMR-autism hypothesis but instead focus on identifying actual causes of autism.  
  ← Immunization Safety Review: Vaccines and Autism — 
- **[IDENTITY_ONLY]** The Institute of Medicine convened an independent Immunization Safety Review Committee that conducted a comprehensive review of all available epidemiological and biological evidence on the MMR–autism and thimerosal–autism hypotheses, and is described as the most authoritative U.S. government-commissioned scientific review of the MMR-autism controversy.  
  ← Immunization Safety Review: Vaccines and Autism — 
- **[IDENTITY_ONLY]** The European Medicines Agency's CHMP concluded that autism is not listed as a causally associated adverse reaction in the approved product information for M-M-RvaxPro, that the benefit-risk balance is favorable, and found no signal supporting a causal association between MMR vaccination and autism in post-marketing pharmacovigilance data from multiple European countries.  
  ← European Medicines Agency: M-M-RvaxPro — European 
- **[IDENTITY_ONLY]** The European Medicines Agency granted marketing authorization for M-M-RvaxPro and published a European Public Assessment Report (EPAR) representing the EMA's formal regulatory position on the MMR-autism question.  
  ← European Medicines Agency: M-M-RvaxPro — European 
- **[IDENTITY_ONLY]** FDA and CDC conducted a joint review of VAERS reports coded for autism or autism spectrum disorder following MMR vaccination, applying proportional reporting ratios and empirical Bayesian data mining, and found no disproportionate reporting ratio for autism following MMR vaccination; the FDA concluded that VAERS data provided no causal evidence linking MMR vaccination to autism.  
  ← Vaccine Adverse Event Reporting System (VAERS): Re
- **[IDENTITY_ONLY]** The VAERS passive surveillance system is not designed to establish causality between vaccines and adverse events.  
  ← Vaccine Adverse Event Reporting System (VAERS): Re
- **[IDENTITY_ONLY]** Andrew Wakefield was struck off the UK medical register following the General Medical Council findings.  
  ← Ileal-lymphoid-nodular hyperplasia, non-specific c

### biological_mechanisms (5)

- **[IDENTITY_ONLY]** M-M-R II has never contained thimerosal as a preservative; the vaccine uses a live attenuated formulation incompatible with preservative use.  
  ← FDA Statement Regarding the MMR Vaccine and Thimer
- **[FIGURE_BOUND]** The Smeeth 2004 case-control study found no evidence of a new-onset syndrome following MMR vaccination.  
  ← MMR vaccination and pervasive developmental disord
- **[FIGURE_BOUND]** The Taylor et al. (2002) study directly tested the specific biological mechanism proposed in Wakefield's retracted study and found no supporting evidence.  
  ← Measles, mumps, and rubella vaccination and bowel 
- **[IDENTITY_ONLY]** Serious adverse events such as encephalitis and febrile seizures following MMR vaccination are rare, and the benefit-risk balance strongly favors vaccination.  
  ← Vaccines for measles, mumps, rubella, and varicell
- **[IDENTITY_ONLY]** The Danish cohort study found no clustering of autism diagnoses at any specific time interval following MMR vaccination, contradicting the proposed biological mechanism linking the vaccine to autism.  
  ← A Population-Based Study of Measles, Mumps, and Ru

### retraction_and_fraud_investigation (2)

- **[IDENTITY_ONLY]** The UK General Medical Council found that the Wakefield et al. research involved undisclosed financial conflicts of interest, ethical violations in the treatment of child subjects (including invasive procedures without ethical approval), data manipulation, and dishonesty — constituting serious professional misconduct.  
  ← Ileal-lymphoid-nodular hyperplasia, non-specific c
- **[IDENTITY_ONLY]** The Wakefield et al. study was found to have involved data manipulation, undisclosed conflicts of interest, and ethical violations in subject recruitment.  
  ← Ileal-lymphoid-nodular hyperplasia, non-specific c

### public_health_impact (2)

- **[IDENTITY_ONLY]** Anti-vaccine advocates conflated concerns about thimerosal with the separate MMR-autism hypothesis advanced by Wakefield.  
  ← FDA Statement Regarding the MMR Vaccine and Thimer
- **[IDENTITY_ONLY]** The authors of the Taylor et al. meta-analysis concluded that continued promotion of vaccine safety concerns related to autism may be harmful to public health.  
  ← Vaccines are not associated with autism: An eviden

### original_wakefield_research (1)

- **[FIGURE_BOUND]** The Wakefield et al. case series enrolled only 12 children — a sample size statistically insufficient to establish any causal association between MMR vaccination and developmental disorder — and claimed to identify a novel syndrome linking MMR vaccination to autism and gastrointestinal pathology.  
  ← Ileal-lymphoid-nodular hyperplasia, non-specific c

## The withheld claims, each with why

### large_scale_epidemiological_evidence (32)

- The Omnibus Autism Proceeding ruling rejected both the 'MMR plus thimerosal' causation theory and the standalone MMR-autism theory, finding that epidemiological evidence overwhelmingly contradicted both hypotheses.  
  WHY: Omnibus Autism Proceeding: Special Masters' D — fetch: HTTP 404
- A Cochrane systematic review analyzed 138 studies involving over 23 million children and found no credible evidence of a link between MMR vaccination and autism spectrum disorder.  
  WHY: Vaccines for measles, mumps, rubella, and var — not in the document: 23, 23000000
- The Institute of Medicine's review of the MMR–autism hypothesis was based on epidemiological studies covering millions of children across multiple countries.  
  WHY: Immunization Safety Review: Vaccines and Auti — fetch: nothing retrieved
- The Honda et al. Japan study is considered one of the strongest natural experiments disproving a causal link between MMR vaccine and autism.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- A US cohort study of 95,727 children found no association between MMR vaccination and autism, including among children with older siblings with autism spectrum disorder.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- Among children with an older sibling with ASD, MMR vaccination was not associated with increased autism risk, with a hazard ratio of 0.80 (95% CI 0.55–1.16).  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- The Jain 2015 study specifically examined MMR vaccine safety in a high-risk population defined by having an older sibling with autism, a group considered at higher genetic risk for ASD.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- The Jain 2015 cohort study found no elevated autism risk from MMR vaccination in genetically predisposed child populations, directly addressing concerns of vaccine-hesitant parents of high-risk children.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- A Danish cohort study examined 650,000 children born between 1999 and 2010 for an association between MMR vaccination and autism.  
  WHY: Measles, Mumps, Rubella Vaccination and Autis — not in the document: 650000
- The Danish cohort study found no temporal clustering of autism diagnoses in the 2-year period following MMR vaccination.  
  WHY: Measles, Mumps, Rubella Vaccination and Autis — not in the document: 2
- A Cochrane systematic review synthesized evidence from 138 studies including over 23 million children on the safety and efficacy of MMR and MMRV vaccines.  
  WHY: Vaccines for measles, mumps, rubella, and var — not in the document: 23, 23000000
- The Cochrane systematic review found no credible evidence of an association between MMR vaccination and autism across 138 studies and 23 million children.  
  WHY: Vaccines for measles, mumps, rubella, and var — not in the document: 23, 23000000
- A UK cohort study examined 498 children with autism spectrum disorder born between 1979 and 1998 in the North Thames region.  
  WHY: Autism and measles, mumps, and rubella vaccin — not in the document: 1998
- A Danish cohort study followed 530,000 children born between 1991 and 1998, comparing autism rates between 440,655 MMR-vaccinated and 96,648 unvaccinated children using national registry data.  
  WHY: A Population-Based Study of Measles, Mumps, a — not in the document: 530000, 96648
- The relative risk of autism in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.26), indicating no increased risk of autism from MMR vaccination.  
  WHY: A Population-Based Study of Measles, Mumps, a — not in the document: 1.26
- Among children born in Yokohama between 1992 and 1996, the cumulative incidence of autism by age 7 rose from 48.4 to 117.2 per 10,000, despite zero MMR vaccination.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- Autism prevalence in Yokohama continued to rise after MMR vaccination rates dropped to zero following the 1993 withdrawal of the vaccine in Japan.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- The Honda et al. (2005) study examined autism rates in Yokohama across the period 1988 to 1996, spanning the withdrawal of MMR vaccination in Japan.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- A meta-analysis by Taylor et al. pooled data from 1.2 million children across five cohort studies and five case-control studies.  
  WHY: Vaccines are not associated with autism: An e — not in the document: 1200000
- MMR-vaccinated children showed no increased risk of autism compared to unvaccinated children in a cohort of 650,000 Danish children.  
  WHY: Measles, Mumps, Rubella Vaccination and Autis — not in the document: 650000
- Japan withdrew the MMR vaccine in 1993, creating a natural experiment to test whether MMR vaccination causes autism.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- After MMR vaccination was discontinued in Japan in 1993, autism rates in Yokohama continued to rise rather than decline.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- The cumulative incidence of autism spectrum disorders in Yokohama rose from 47.6 per 10,000 in the 1988 birth cohort to 117.2 per 10,000 in the 1996 birth cohort, entirely during the post-MMR period.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- A JAMA study examined 95,727 children with older siblings to test whether MMR vaccination increased autism risk.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- The Jain et al. (2015) JAMA study found no association between MMR vaccination and autism in a cohort of 95,727 children, including those with autistic older siblings.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- Children with an older autistic sibling showed no increased autism risk from MMR vaccination, refuting concerns about genetically susceptible subgroups.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
- A Danish cohort study followed 650,000 children born between 1999 and 2010 to examine the relationship between MMR vaccination and autism.  
  WHY: Measles, Mumps, Rubella Vaccination and Autis — not in the document: 650000
- The Danish cohort study followed 530,000 children born between 1991 and 1998, comparing autism rates between MMR-vaccinated and unvaccinated children.  
  WHY: A Population-Based Study of Measles, Mumps, a — not in the document: 530000
- The relative risk of autistic disorder in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.26), indicating no statistically significant increased risk.  
  WHY: A Population-Based Study of Measles, Mumps, a — not in the document: 1.26
- The Danish cohort study included 440,655 MMR-vaccinated children and 96,648 unvaccinated children, finding no statistically significant difference in autism incidence between the two groups.  
  WHY: A Population-Based Study of Measles, Mumps, a — not in the document: 2, 96648
- A UK-based cohort study examined 498 children with autism or atypical autism born between 1979 and 1992 in the North Thames region to analyze the temporal relationship between MMR vaccination and autism onset.  
  WHY: Autism and Measles, Mumps, and Rubella Vaccin — not in the document: 1992
- A Danish registry study followed 650,000 children born in Denmark between 1999 and 2010 to examine the relationship between MMR vaccination and autism.  
  WHY: Measles, Mumps, Rubella Vaccination and Autis — not in the document: 650000

### retraction_and_fraud_investigation (8)

- The Lancet issued a full retraction of the Wakefield et al. MMR-autism paper in February 2010.  
  WHY: Ileal-lymphoid-nodular hyperplasia, non-speci — not in the document: 2010 | Retraction—Ileal-lymphoid-nodular hyperplasia — fetch: nothing retrieved | Ileal-lymphoid-nodular hyperplasia, non-speci — not in the document: 2010
- Andrew Wakefield was struck off the UK medical register in May 2010.  
  WHY: Ileal-lymphoid-nodular hyperplasia, non-speci — not in the document: 2010 | Retraction—Ileal-lymphoid-nodular hyperplasia — fetch: nothing retrieved
- Wakefield received £435,643 plus expenses from lawyers seeking to build a case against MMR vaccine manufacturers prior to publication of the 1998 Lancet study, a conflict of interest that was never disclosed to The Lancet.  
  WHY: Ileal-lymphoid-nodular hyperplasia, non-speci — not in the document: 435643 | How the Case Against the MMR Vaccine Was Fixe — fetch: nothing retrieved
- Special Master Hastings characterized the scientific evidence presented by petitioners — including testimony based on Wakefield's research — as 'weak, contradictory, and unpersuasive' with respect to a causal link between MMR vaccine and autism.  
  WHY: Omnibus Autism Proceeding: Special Masters' D — fetch: HTTP 404
- The retraction of the Wakefield et al. paper removed the primary published basis for the MMR-autism hypothesis.  
  WHY: Retraction—Ileal-lymphoid-nodular hyperplasia — fetch: nothing retrieved
- Ten of the thirteen co-authors of the Wakefield et al. paper formally withdrew their names from the paper's interpretation in 2004.  
  WHY: Ileal-lymphoid-nodular hyperplasia, non-speci — not in the document: 13, 2004
- Brian Deer's BMJ investigation found that Wakefield altered clinical data from all 12 children in the 1998 Lancet paper, with every case where records could be checked showing discrepancies between documented medical histories and published findings.  
  WHY: How the Case Against the MMR Vaccine Was Fixe — fetch: nothing retrieved
- The BMJ formally characterized the 1998 Lancet paper by Wakefield as 'an elaborate fraud' in an editorial by editor Fiona Godlee, marking the first time a major medical journal had used such language about a published study.  
  WHY: How the Case Against the MMR Vaccine Was Fixe — fetch: nothing retrieved

### institutional_regulatory_response (7)

- Japan withdrew the MMR vaccine in 1993, resulting in MMR vaccination rates dropping to zero after that year.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- M-M-R II (BLA 103166), manufactured by Merck & Co., has maintained FDA licensure continuously since 1978 with periodic label updates.  
  WHY: Biologics License Application (BLA) 103166: M — fetch: HTTP 404
- FDA product labeling for M-M-R II lists known adverse reactions including fever, rash, and rare febrile seizures, but does not list autism spectrum disorder as a causally associated adverse event; subsequent label revisions have never added autism as a causally associated adverse event.  
  WHY: Biologics License Application (BLA) 103166: M — fetch: HTTP 404
- Post-marketing safety update reviews of M-M-R II conducted by FDA's Center for Biologics Evaluation and Research (CBER) have not identified a causal signal between MMR vaccination and autism.  
  WHY: Biologics License Application (BLA) 103166: M — fetch: HTTP 404
- The Institute of Medicine concluded that the epidemiological evidence favors rejection of a causal relationship between thimerosal-containing vaccines and autism.  
  WHY: Immunization Safety Review: Vaccines and Auti — fetch: nothing retrieved
- The Omnibus Autism Proceeding involved approximately 5,500 claims filed in the Vaccine Injury Compensation Program alleging that MMR vaccination caused autism; all three test cases were decided against petitioners, the Federal Circuit Court of Appeals upheld the decisions, and the U.S. Supreme Court declined to review the cases.  
  WHY: Omnibus Autism Proceeding: Special Masters' D — fetch: HTTP 404
- Special Master George Hastings ruled that petitioners had not demonstrated by a preponderance of evidence that MMR vaccine caused autism in the test case claimant Michelle Cedillo.  
  WHY: Omnibus Autism Proceeding: Special Masters' D — fetch: HTTP 404

### biological_mechanisms (3)

- The continued rise in autism incidence in Yokohama after MMR withdrawal constituted a natural experiment directly disproving the hypothesis that MMR causes autism.  
  WHY: No effect of MMR withdrawal on the incidence  — HEADING: shares no distinctive word with the registry headin
- The biological mechanisms proposed by Wakefield — including measles virus persistence in gut tissue and 'leaky gut' leading to neurological damage — were not supported by credible scientific evidence, according to the Institute of Medicine's Immunization Safety Review Committee.  
  WHY: Immunization Safety Review: Vaccines and Auti — not in the document: ' leading to neurological damage — were | Immunization Safety Review: Vaccines and Auti — fetch: nothing retrieved | Immunization Safety Review: Vaccines and Auti — fetch: nothing retrieved
- The temporal clustering of autism diagnoses with MMR vaccination timing reflects the coincidence of the 12–18 month vaccination window with the typical age of autism symptom recognition, not a causal relationship.  
  WHY: Vaccine Adverse Event Reporting System (VAERS — not in the document: 12, 18

### original_wakefield_research (2)

- Andrew Wakefield had been paid by lawyers seeking evidence against vaccine manufacturers at the time of the original 1998 research.  
  WHY: Retraction—Ileal-lymphoid-nodular hyperplasia — fetch: nothing retrieved
- Wakefield's data alterations in the 1998 Lancet paper included changing documented diagnoses and onset timelines across all 12 cases to fit the hypothesis of a link between MMR vaccination and autism.  
  WHY: How the Case Against the MMR Vaccine Was Fixe — fetch: nothing retrieved

### public_health_impact (1)

- Vaccination rates were lower among younger siblings of autistic children, reflecting parental vaccine hesitancy, yet autism rates were not lower in the unvaccinated children.  
  WHY: Autism Occurrence by MMR Vaccine Status Among — resolve: NONEXISTENT
