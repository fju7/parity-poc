# Outside review packet — The Melanoma Result

Page under review: `site/whatholdsup/melanoma.html`
sha256 (first 16): `2727429064d69721`
Built: 2026-09-09

This packet is the piece, plus three things that did not exist at the last
review: every inference the piece makes with the facts it rests on, the full
list of what we hold and what we could not read, and the list of places our
own machinery has not looked.

You are NOT being given our own findings or our adjudication record. That is
deliberate. You exist to find what our checks cannot see, and a reader shown
our findings anchors on them.

---

## What has changed since the last outside review

The last outside review of this piece read a file whose sha256 begins
`a788f00ab1521235`, on 2026-09-08. Since then **284 changes to the prose** have gone
in; 284 of them reconcile to a written decision and **0 do not**.

That number is the reason this is a full review and not a delta review.
Most of the piece is not the piece that was read. Do not go looking for
what changed — read it as a reader would, from the top, as though no
review had happened.

---

## Appendix A — every inference the piece makes, and its reasoning

The piece distinguishes what it REPORTS from what it INFERS. Below are all 46
inferences, each with the exact words from the documents it rests on and the
step taken from those words to the claim.

**This is the most useful thing in the packet to attack.** A reported figure
can be checked against a document and we have already done that for every one.
A step from facts to a conclusion cannot be checked that way. If a step does
not follow, or follows only under an assumption the piece does not state, that
is a finding — and it is the kind our machinery is structurally unable to see.

Every span below was checked against the bytes of the named document at build
time. None failed.

### J01

**The sentence.** 0 Phase 3 efficacy numbers released

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S013] "hasResults":false

**The step we take.** The zero is a count over the documents this issue holds, not over the world. S001 announces that both endpoints were met and gives no figure for either; S013, the trial's own registry record, carries hasResults false. Every other held document reporting a figure for this programme reports it for KEYNOTE-942, the 157-patient Phase 2b, and says so. So: zero efficacy figures for INTerpath-001 in anything we hold. THE CARD DOES NOT SAY THAT. It says '0 Phase 3 efficacy numbers released', which a reader takes as a claim about the world rather than about our shelf, and the caption has no room for the scope this binding names. Recorded so the mismatch is visible to the editor rather than invisible to everyone.

### J02

**The sentence.** Why this is worth a whole article Five outlets whose articles we hold named KEYNOTE-942 when attributing the 49% figure — The ASCO Post, Dermatology Times, Practical Dermatology, MLQ News and OncLive.

**Rests on:**
  - [S006] the combination demonstrated a 49% reduction in the risk of recurrence or death (hazard ratio [HR] = 0.51, 95% confidence interval [CI] = 0.294–0.887)
  - [S016] intismeran plus pembrolizumab reduced the risk of recurrence or death by 49% compared with pembrolizumab alone (HR, 0.51; 95% CI, 0.294-0.887)
  - [S018] At 5-year follow-up, intismeran plus pembrolizumab was associated with a 49% reduction in the risk of recurrence or death (HR, 0.51; 95% CI, 0.294 to 0.887)
  - [S011] The Phase 3 result builds on the Phase 2b KEYNOTE-942 study. At five years, intismeran plus Keytruda reduced the risk of recurrence or death by 49% versus Keytruda alone
  - [S017] Five-year follow-up data from the phase 2b KEYNOTE-942/mRNA-4157-P201 trial (NCT03897881) presented at the 2026 American Society of Clinical Oncology Annual Meeting showed that the combination reduced the risk of recurrence or death by 49%

**The step we take.** A count over the coverage we hold, checked outlet by outlet. Each of the five names KEYNOTE-942 or its phase 2b in the same sentence as the 49% figure, so each attributed the figure correctly. The enumeration is of outlets that used the 49% figure itself; KOL Pulse carries the same result as hazard ratios rather than as 49%, which is why it is treated separately in the next sentence and is not a sixth here.

### J03

**The sentence.** A post logged by KOL Pulse identified the figure as coming from an earlier phase 2 trial without naming KEYNOTE-942; KOL Pulse’s own text names the trial throughout and attributes the circulating hazard ratios to it.

**Rests on:**
  - [S019] In a phase 2 trial earlier this year the vaccine with immunotherapy has shown ~49% lower risk of recurrence or death vs immunotherapy alone
  - [S019] hazard-ratio figures circulating on announcement day are these KEYNOTE-942 Phase 2b numbers

**The step we take.** Both halves come from S019 and they are different authors. The ~49%-as-phase-2 wording with no trial named is inside a social post KOL Pulse logged, not KOL Pulse's own text. KOL Pulse's own text names KEYNOTE-942 eleven times and says the circulating hazard ratios are its Phase 2b numbers. The earlier version of this sentence credited the outlet with the post's omission; it does not have it.

### J04

**The sentence.** The OncLive article was obtained on 3 September, attributes the figures to the phase 2b trial like the rest, and is named again.

**Rests on:**
  - [S017] Five-year follow-up data from the phase 2b KEYNOTE-942/mRNA-4157-P201 trial (NCT03897881) presented at the 2026 American Society of Clinical Oncology Annual Meeting showed that the combination reduced the risk of recurrence or death by 49% (HR, 0.51; 95% CI, 0.294-0.887)

**The step we take.** The article is in the library, acquired 3 September after every automated fetch returned 403, and the span above is its own sentence attributing the figures to the phase 2b trial. Naming an outlet the page had removed for want of the document is only honest if the document is now held and says what we say it says; both are checkable against the library and the span.

### J05

**The sentence.** A reader who sees "49% reduction" three paragraphs under "Phase 3 succeeds" comes away with a sense of how large this effect is.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).

**The step we take.** The release states the endpoints were met and gives the 49% figure only for the earlier Phase 2b trial. A reader meeting the two within a few paragraphs has no cue that they belong to different trials, so the figure reads as the magnitude of the result just announced.

### J06

**The sentence.** That sense is drawn from 157 patients in an open-label trial, and the study that could correct it has released no number describing the size of its own effect.

**Rests on:**
  - [S004] Among 157 randomly assigned patients
  - [S004] The phase IIb open-label KEYNOTE-942
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).

**The step we take.** Two halves. The 157 patients and the open-label design are both stated in S004, which is the paper the impression comes from. That the Phase 3 has released no effect size is the same bounded negative as the zero card: S001 states that the endpoints were met and gives no figure.

### J07

**The sentence.** An HR of 0.51 does not mean 49% of patients were saved.

**Rests on:**
  - [S025] The hazard ratio is an estimate of the ratio of the hazard rate in the treated versus the control group. For example if there are two groups, group 1 and group 2, HR = 4.5 for treatment means that the risk (of relapse) for group 2 is 4.5 times that of group 1. If HR = 1 then Group 1 h (t) = Group 2 h (t).
  - [S001] the combination demonstrated a 49% reduction in the risk of recurrence or death (HR=0.51; [95% CI, 0.294-0.887])

**The step we take.** 0.51 is the hazard ratio this programme reported, and a hazard ratio is a ratio of hazard rates between two groups, not a count or share of individuals. So it cannot be read as a percentage of patients.

### J08

**The sentence.** That is a gap of roughly 20 percentage points at the five-year mark — a far more tangible figure than the hazard ratio, and the one that rarely reaches a headline.

**Rests on:**
  - [S014] landmark 5-y RFS rates of 68.8% (95% CI, 56.3%-78.3%) for intismeran + pembro vs 49.1% (95% CI, 33.3%-63.0%) for pembro alone

**The step we take.** 68.8 minus 49.1 is 19.7, which the sentence calls roughly 20 percentage points. Both rates and both intervals are in one sentence of S014; the subtraction is ours and the word 'roughly' is doing the rounding.

### J09

**The sentence.** Take one treated and one untreated patient at random: at a hazard ratio of 0.510 there is about a 66% chance the treated one goes longer without recurrence, against 50% if the therapy did nothing.

**Rests on:**
  - [S023] for any randomly selected pair of patients, one from the treatment group and one from the control group, the hazard ratio is the
  - [S004] The HR (95% CI) for RFS was 0.510 (0.294 to 0.887).

**The step we take.** S023 gives the one patient-level reading a hazard ratio does support: for a randomly chosen treated/untreated pair, the hazard ratio maps to the odds that the treated patient does better. Applied to S004's 0.510 that is 1/(1+0.510) ≈ 0.66, against 0.50 for a therapy that did nothing. The arithmetic is ours; both inputs are quoted.

### J10

**The sentence.** First, does the range cross 1.0?

**Rests on:**
  - [S022] interval to determine whether it includes effect sizes of importance
  - [S022] 95 % confidence intervals repeatedly in valid applications , 95 % of them, on average, will contain (i.e., include or cover) the true effect size.

**The step we take.** The question the explainer tells a reader to ask first. S022 describes the interval as the thing to read for which effect sizes it includes, and gives the coverage meaning that makes 1.0's presence or absence the salient fact. Framing it as a question is ours; the reason it is the right question is theirs.

### J11

**The sentence.** Because 1.0 means no difference at all.

**Rests on:**
  - [S025] The hazard ratio is an estimate of the ratio of the hazard rate in the treated versus the control group. For example if there are two groups, group 1 and group 2, HR = 4.5 for treatment means that the risk (of relapse) for group 2 is 4.5 times that of group 1. If HR = 1 then Group 1 h (t) = Group 2 h (t).

**The step we take.** Singh and Mukhopadhyay define the hazard ratio as a ratio of two groups' hazard rates and state that if HR = 1 the two hazard functions are equal. Two quantities whose ratio is 1 are the same quantity, so a hazard ratio of 1.0 is the value at which the two groups' hazard rates do not differ.

### J12

**The sentence.** If the range includes 1.0, then "this treatment does nothing" is still among the possibilities the data cannot rule out.

**Rests on:**
  - [S022] The P value is then the probability that the chosen test statistic would have been at least as large as its observed value if every model assumption were correct, including the test hypothesis.
  - [S025] The hazard ratio is an estimate of the ratio of the hazard rate in the treated versus the control group. For example if there are two groups, group 1 and group 2, HR = 4.5 for treatment means that the risk (of relapse) for group 2 is 4.5 times that of group 1. If HR = 1 then Group 1 h (t) = Group 2 h (t).

**The step we take.** A confidence interval is the set of effect sizes not rejected at the corresponding cut-off, and a hazard ratio of 1 is the value at which the groups' hazard rates are equal. So if 1.0 lies inside the interval, 'no difference' is one of the values the data do not exclude.

### J13

**The sentence.** All four intervals are from KEYNOTE-942, the 157-patient Phase 2b.

**Rests on:**
  - [S004] The HR (95% CI) for RFS was 0.510 (0.294 to 0.887).
  - [S004] Among 157 randomly assigned patients
  - [S004] The phase IIb open-label KEYNOTE-942

**The step we take.** 'All four' ranges over the four intervals drawn in the chart above it, and each is a KEYNOTE-942 figure: S004 is the KEYNOTE-942 paper, it states the trial is phase IIb and open-label, and it enrolled 157. The claim is bounded by the chart, which is on this page, so the count is checkable by looking.

### J14

**The sentence.** Amber bars cross the 95% no-effect line; green ones clear it.

**Rests on:**
  - [S003] hazard ratio [HR] for recurrence or death, 0·561 [95% CI 0·309-1·017]; two-sided p=0·053
  - [S004] The HR (95% CI) for RFS was 0.510 (0.294 to 0.887).
  - [S022] 95 % confidence intervals repeatedly in valid applications , 95 % of them, on average, will contain (i.e., include or cover) the true effect size.

**The step we take.** The colours are ours and the crossing is the documents'. S003's 2023 interval, 0·309 to 1·017, contains 1.0; S004's five-year 0.294 to 0.887 does not. The chart colours the first amber and the second green. S022 supplies what the 95% line means, and the caption says in its next sentence that the split is a convention rather than a verdict.

### J15

**The sentence.** What time did to the top two bars When KEYNOTE-942 first reported in 2023, its recurrence result was HR 0.561, 95% CI 0.309–1.017 — the interval crossed 1.0, so on a two-sided 5% criterion "no effect" could not be ruled out.

**Rests on:**
  - [S003] hazard ratio [HR] for recurrence or death, 0.561 [95% CI 0.309-1.017]; two-sided p=0.053
  - [S025] The hazard ratio is an estimate of the ratio of the hazard rate in the treated versus the control group. For example if there are two groups, group 1 and group 2, HR = 4.5 for treatment means that the risk (of relapse) for group 2 is 4.5 times that of group 1. If HR = 1 then Group 1 h (t) = Group 2 h (t).

**The step we take.** The Lancet reports the interval as 0.309 to 1.017, and a hazard ratio of 1 is the value at which the two groups' hazard rates are equal. 1.0 lies between 0.309 and 1.017, so a two-sided 95% interval does not exclude no difference. The criterion is named because this trial's own prespecified analysis was one-sided at alpha 0.10, under which the same data did clear its threshold — an unqualified 'could not be ruled out' would imply the trial failed a test it never set itself.

### J16

**The sentence.** By the three-year readout at ASCO 2024, since published in full, the interval no longer crossed it: HR 0.510, 95% CI 0.288–0.906 — though that paper states plainly that its analyses were descriptive only and not intended for formal hypothesis testing, so this is an interval that stopped including 1.0 rather than a threshold anyone crossed.

**Rests on:**
  - [S007] HR 0.510 80% CI 0.351 to 0.743 95% CI 0.288 to 0.906
  - [S025] The hazard ratio is an estimate of the ratio of the hazard rate in the treated versus the control group. For example if there are two groups, group 1 and group 2, HR = 4.5 for treatment means that the risk (of relapse) for group 2 is 4.5 times that of group 1. If HR = 1 then Group 1 h (t) = Group 2 h (t).

**The step we take.** The three-year paper's 95% interval runs from 0.288 to 0.906. 1.0 is above 0.906, so unlike the first readout's interval this one does not contain the no-difference value.

### J17

**The sentence.** The universal misreading A p-value of 0.05 does not mean a 95% chance the drug works.

**Rests on:**
  - [S022] the P value is degraded into a dichotomy in which results are declared "statistically significant" if P falls on or below a cut-off (usually 0.05) and declared "nonsignificant" otherwise

**The step we take.** 0.05 is named in the source only as the conventional cut-off. Greenland et al. state that the P value is not a hypothesis probability, so a p of 0.05 cannot be read as a 95% chance that the drug works.

### J18

**The sentence.** It means: if the no-effect hypothesis and the other assumptions behind the analysis were all correct, a result at least this extreme would turn up about 5% of the time.

**Rests on:**
  - [S022] The P value is then the probability that the chosen test statistic would have been at least as large as its observed value if every model assumption were correct, including the test hypothesis.

**The step we take.** Greenland et al. define the P value as the probability of a test statistic at least as extreme as the one observed, computed on the assumption that the test hypothesis AND every other model assumption is correct. The earlier wording here — 'if the drug were useless, you would see a result this good 5% of the time' — conditioned on the test hypothesis alone and dropped the rest of the model, which is the misinterpretation that paper exists to correct. The sentence now carries the whole condition.

### J19

**The sentence.** A one-sided test asks only "is it better?" A two-sided test asks "is it different, in either direction?" For a symmetric test, and when the one-sided test points the way the effect actually went, the two-sided p-value is about double the one-sided one, so the same data gives 0.0266 one way and 0.053 the other — identical evidence, measured against a different question.

**Rests on:**
  - [S005] reduced the risk of recurrence or death by 44% (HR=0.56 [95% CI, 0.309-1.017]; one-sided p value=0.0266) compared with KEYTRUDA alone
  - [S003] hazard ratio [HR] for recurrence or death, 0.561 [95% CI 0.309-1.017]; two-sided p=0.053

**The step we take.** The company release reports one-sided p = 0.0266 and the Lancet reports two-sided p = 0.053 for the same hazard ratio and the same interval. The pair shows what the one-sided and two-sided questions do to the same data.

### J20

**The sentence.** So 0.0266 was inside its own prespecified threshold by a wide margin , and 0.053 is a near miss only against a 0.05 line this trial never used.

**Rests on:**
  - [S007] The trial was designed with approximately 80% power to detect a hazard ratio (HR) of 0.5 with a one-sided a of 0.10 after 40 RFS events.
  - [S005] reduced the risk of recurrence or death by 44% (HR=0.56 [95% CI, 0.309-1.017]; one-sided p value=0.0266) compared with KEYTRUDA alone
  - [S003] hazard ratio [HR] for recurrence or death, 0.561 [95% CI 0.309-1.017]; two-sided p=0.053
  - [S022] the P value is degraded into a dichotomy in which results are declared "statistically significant" if P falls on or below a cut-off (usually 0.05) and declared "nonsignificant" otherwise

**The step we take.** The three-year paper records that the trial was designed against a one-sided alpha of 0.10. The company release reports one-sided p = 0.0266 and the Lancet reports two-sided p = 0.053 for the same comparison. 0.0266 is below 0.10; 0.053 is above 0.05 but 0.05 is not the threshold this trial registered.

### J21

**The sentence.** 0.0266 reads as a clear win and 0.053 reads as a near miss, and they are the same result.

**Rests on:**
  - [S005] reduced the risk of recurrence or death by 44% (HR=0.56 [95% CI, 0.309-1.017]; one-sided p value=0.0266) compared with KEYTRUDA alone
  - [S003] hazard ratio [HR] for recurrence or death, 0.561 [95% CI 0.309-1.017]; two-sided p=0.053

**The step we take.** Both figures describe the same comparison in the same trial — the release's one-sided p and the Lancet's two-sided p, either side of the same hazard ratio 0.561 and interval 0.309-1.017. They differ in which test was reported, not in what was observed.

### J22

**The sentence.** The confidence interval is the tell: 0.309–1.017 crosses 1.0, which is exactly what a two-sided 95% interval keys on — the convention journals print, and not the threshold this trial set for itself, which was a one-sided alpha of 0.10 and which 0.0266 was inside.

**Rests on:**
  - [S003] hazard ratio [HR] for recurrence or death, 0.561 [95% CI 0.309-1.017]; two-sided p=0.053
  - [S025] The hazard ratio is an estimate of the ratio of the hazard rate in the treated versus the control group. For example if there are two groups, group 1 and group 2, HR = 4.5 for treatment means that the risk (of relapse) for group 2 is 4.5 times that of group 1. If HR = 1 then Group 1 h (t) = Group 2 h (t).

**The step we take.** The two-sided 95% interval is 0.309 to 1.017 and 1.0 falls inside it, which is why the two-sided p of 0.053 sits just above 0.05: the interval and the test are the same statement about the same data. The added clause names which threshold the 1.0 crossing belongs to: the two-sided 0.05 convention journals print, not this trial's prespecified one-sided alpha of 0.10. Both are documents we hold — S019 states the alpha outright, and S007 prints it as 'a one-sided a of 0.10', the Greek alpha extracting as a bare a.

### J23

**The sentence.** A therapy that reduces the hazard of recurrence by 8% and one that halves it both produce that sentence.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S011] The companies have not disclosed hazard ratios, confidence intervals, p-values, median follow-up or event counts for the Phase 3 trial.

**The step we take.** Since the announcement gives no effect size, the same sentence 'met its endpoint' would have been written for a small benefit and a large one. The sentence therefore does not distinguish between them.

### J24

**The sentence.** This is why the absence of a hazard ratio in the Phase 3 announcement matters: "met its endpoint" is the floor of what could be said, not a summary of what was found.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S011] The companies have not disclosed hazard ratios, confidence intervals, p-values, median follow-up or event counts for the Phase 3 trial.

**The step we take.** The release states only that the endpoints were met and, as MLQ News records, discloses no hazard ratio, interval, p-value or event count. 'Met its endpoint' is therefore compatible with any effect size large enough to clear the threshold, and reports nothing about which.

### J25

**The sentence.** For adjuvant PD-1 inhibitors specifically — the comparison arm in this very trial — neither of the two placebo-controlled trials whose registry records we hold — KEYNOTE-054 and KEYNOTE-716 — has posted an overall-survival result at all.

**Rests on:**
  - [S020] "reportingStatus":"NOT_POSTED"
  - [S026] "reportingStatus":"NOT_POSTED"
  - [S020] "anticipatedPostingDate":"2026-11"
  - [S026] "anticipatedPostingDate":"2033-10"

**The step we take.** Both records mark the overall-survival measure NOT_POSTED with a posting date still ahead of it. So neither trial has posted a result, which is what the sentence now says. It USED to say they had 'reported no statistically significant overall survival benefit' — words that read as a null finding rather than as an absent one, and the change-sentence review caught the contradiction with the very next sentence. That is the MISSING_NUMBER_AS_MISSING_EVIDENCE class this page criticises in others.

### J26

**The sentence.** KEYNOTE-054 and KEYNOTE-716 are both pembrolizumab against placebo; each lists overall survival as a secondary endpoint, and each registry record marks that result NOT_POSTED with a posting date still ahead of it — November 2026 for KEYNOTE-054, October 2033 for KEYNOTE-716.

**Rests on:**
  - [S020] "reportingStatus":"NOT_POSTED"
  - [S026] "reportingStatus":"NOT_POSTED"
  - [S020] "anticipatedPostingDate":"2026-11"
  - [S026] "anticipatedPostingDate":"2033-10"

**The step we take.** Both records are held in full and were read again on 3 September after this sentence was challenged. In each, the overall-survival measure appears in the posted results section as a DECLARATION with reportingStatus NOT_POSTED and an anticipated posting date — November 2026 for KEYNOTE-054, October 2033 for KEYNOTE-716 — and no measurement classes at all. An earlier version of this sentence said each had posted a result carrying no statistical analysis. That was wrong, and wrong in a way worth recording: it came from reading the trial-level hasResults flag as true and finding the measure listed, without reading the field on the measure itself. The page gate caught it.

### J27

**The sentence.** CheckMate 238 ’s arms are nivolumab and ipilimumab, so there is no placebo arm to report against.

**Rests on:**
  - [S021] Nivolumab Versus Ipilimumab

**The step we take.** CheckMate 238 randomises nivolumab against ipilimumab. Its registry title states both arms, so there is no placebo arm in it and it cannot bear on a claim about trials against placebo.

### J28

**The sentence.** It is not standard care because the dose was 10 mg/kg and five patients died of immune-related events — not because it failed on survival.

**Rests on:**
  - [S029] this phase 3 trial evaluated ipilimumab at a dose of 10 mg per kilogram in patients who had undergone complete resection of stage III melanoma
  - [S029] In the ipilimumab group, 5 patients (1.1%) died owing to immune-related adverse events.
  - [S029] The rate of overall survival at 5 years was 65.4% in the ipilimumab group, as compared with 54.4% in the placebo group (hazard ratio for death, 0.72; 95.1% CI, 0.58 to 0.88; P = 0.001).

**The step we take.** Two facts from the same paper, set against each other. EORTC 18071 gave ipilimumab at 10 mg/kg, and five patients in that arm died of immune-related adverse events. The same paper reports the survival benefit that arm produced. So the reason the regimen is not standard care is its toxicity at that dose, not a failure on the endpoint — which is the distinction the sentence draws.

### J29

**The sentence.** In this programme, overall survival has been reported only as an exploratory analysis in the smaller trial, on an "n=14" — fourteen deaths among 157 patients, seven in each arm.

**Rests on:**
  - [S004] Exploratory end points included overall survival (OS)
  - [S004] Overall, 7 of 107 patients (6.5%) in the intismeran plus pembrolizumab arm and 7 of 50 (14.0%) in the pembrolizumab arm died
  - [S004] Among 157 randomly assigned patients
  - [S002] encouraging trend toward improved OS (HR=0.471; [95% CI, 0.165-1.345]; n=14)

**The step we take.** Overall survival is listed among the exploratory end points in S004, so it was never a tested one. The deaths are seven and seven, which is the fourteen the companies label n=14 in S002, among the 157 patients S004 randomly assigned. Every figure in the sentence is printed; the addition is ours.

### J30

**The sentence.** One caveat the figures on this page raise themselves: intismeran is an intramuscular injection that caused injection-site pain in 59.6% of patients and chills in 51.0% in the earlier trial; the Phase 3 comparator is a saline injection.

**Rests on:**
  - [S002] injection site pain (59.6%), and chills (51.0%)
  - [S013] "nctId":"NCT05933577"

**The step we take.** Two things already on the page, put together. S002 reports injection-site pain in 59.6% and chills in 51.0% in the earlier trial. The Phase 3 registry record S013 gives the comparator as a saline placebo injection. A therapy that reactogenic against a saline injection is one where a patient or an investigator may sometimes infer the arm, which is what the caveat says.

### J31

**The sentence.** Morning Glory Sciences — we give its argument on its merits rather than on its authority — the Phase 2b population was stage IIIB–IV, the Phase 3 adds node-negative disease, and “absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit.” Pharmacy Times makes the opposite case about the same patients: resected stage IIB or IIC melanoma “can face risks of recurrence and melanoma-specific mortality similar to those observed in stage III disease.” Neither reading appears in any of the general coverage we hold.

**Rests on:**
  - [S009] The Phase 2b population was stage IIIB-IV; the Phase 3 adds stage IIB and IIC - node-negative disease . Absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit.
  - [S010] patients with resected stage IIB or IIC melanoma can face risks of recurrence and melanoma-specific mortality similar to those observed in stage III disease

**The step we take.** The page now makes NO claim about this outlet's standing, and that is the point of the sentence's present form. Three characterisations were tried and all three failed: 'the English edition of a non-English industry site' (withdrawn 3 September, inferred from an /en/ URL and a strapline), 'an outlet we can find no other publication citing' (falsified 4 September by a citation in the Irish Journal of Medical Science, and the removal that correction announced never actually happened — the clause stayed live until 9 September), and 'a specialist outlet' (the wording corrections.md said replaced it, which never reached the page and rests on nothing better than the other two). What survives is what we can show: S009 makes the stage-population argument and S010 makes the opposing one, both quoted, and the page tells the reader to weigh the argument rather than the source. Adding any adjective here would be the fourth attempt at a claim we have never been able to support.

### J32

**The sentence.** The trials do not share a population: KEYNOTE-942 enrolled stage IIIB–IV, the Phase 3 enrolled stage IIB–IV , widening it downward — adding IIB, IIC and IIIA below the earlier trial's floor of IIIB.

**Rests on:**
  - [S004] Eligible patients with resected stage IIIB to IV cutaneous melanoma
  - [S001] Distant Metastasis-Free Survival (DMFS) in Patients With Completely Resected Stage IIB-IV Melanoma

**The step we take.** S004 enrolled 'resected stage IIIB to IV'; S001's own headline says 'Completely Resected Stage IIB-IV'. IIB and IIC sit below IIIB, so the Phase 3's floor is lower — the widening the sentence describes, read off the two stage ranges rather than asserted.

### J33

**The sentence.** And most simply, there is nothing to put beside them: the Phase 3 has released no effect size, so quoting 0.51 next to “met its endpoints” is not a comparison but a substitution — the reader supplies the missing number from the smaller, older, differently-designed trial.

**Rests on:**
  - [S011] The companies have not disclosed hazard ratios, confidence intervals, p-values, median follow-up or event counts for the Phase 3 trial.
  - [S004] Intismeran plus pembrolizumab continued to prolong RFS (hazard ratio [HR], 0.510 [95% CI, 0.294 to 0.887) and DMFS (HR, 0.411 [95% CI, 0.200 to 0.843]), with a favorable trend in overall survival (HR, 0.471 [95% CI, 0.165 to 1.345]) versus pembrolizumab.

**The step we take.** No Phase 3 effect size has been released, and the 0.51 in circulation is the five-year Phase 2b figure from a different trial and population. Placing them side by side offers the reader no second quantity to compare, so the Phase 2b number occupies the place where the Phase 3 number would go.

### J34

**The sentence.** Those are KEYNOTE-942 figures, from the five-year release; the Phase 3 announcement gave no adverse-event rates for its own 1,137 patients.

**Rests on:**
  - [S002] fatigue (59.6%), injection site pain (59.6%), and chills (51.0%)
  - [S011] It did not provide a detailed adverse-event table or rates for the 1,137-patient trial.

**The step we take.** The three percentages are the five-year KEYNOTE-942 release's, verbatim. MLQ News, reading the Phase 3 announcement, records that it gave no adverse-event table or rates for the 1,137-patient trial. So the percentages in the bullet above belong to the smaller earlier trial, and there is no Phase 3 equivalent to compare them with. The Phase 3 release does carry adverse-event percentages, but they are KEYTRUDA label text about other trials, which is why the sentence says rates for its own 1,137 patients rather than percentages at all.

### J35

**The sentence.** The three-year paper reports a hazard ratio of 0.425 on nine deaths, 95% CI 0.114 to 1.584; the five-year analysis reports 0.471 on fourteen, 95% CI 0.165 to 1.345.

**Rests on:**
  - [S007] 0.425 80% CI 0.179 to 1.004 95% CI 0.114 to 1.584
  - [S004] the OS HR (95% CI) was 0.471 (0.165 to 1.345)
  - [S004] Overall, 7 of 107 patients (6.5%) in the intismeran plus pembrolizumab arm and 7 of 50 (14.0%) in the pembrolizumab arm died
  - [S007] An early preliminary trend in OS favored combination versus pembrolizumab (3.7% [4/107] v 10.0% [5/50]; HR, 0.425 [80% CI, 0.179 to 1.004]

**The step we take.** Two survival analyses, now read at the same width. S007's Table 1 prints both intervals for the three-year OS hazard ratio in one row — 0.425, 80% CI 0.179 to 1.004, 95% CI 0.114 to 1.584 — and the 95% one is the figure the page now gives, so it can be set against S004's five-year 0.471 (0.165 to 1.345) rather than beside it at a different width. Nine deaths, ours by addition from 4 of 107 and 5 of 50; fourteen from 7 and 7. Both intervals contain 1.0.

### J36

**The sentence.** Is the effect real scores 3.94; how large is it scores 1.0.

**Rests on:**
  - [S001] randomized, double-blind, placebo- and active-comparator-controlled global Phase 3 trial
  - [S018] The companies did not disclose hazard ratios, absolute event rates, P values, or other phase 3 efficacy estimates in the topline announcement.

**The step we take.** The two numbers are the published rubric applied by hand to the six dimension scores shown above, and the working for each is printed beside it so a reader can redo the arithmetic. They diverge because the evidence does: the release describes a randomised, double-blind, placebo- and active-comparator-controlled Phase 3, which is what the direction dimensions reward, and discloses no efficacy estimate at all, which is what the magnitude dimension measures. Neither figure is reported by any document; both are ours, computed here.

### J37

**The sentence.** Rigor scores 5 — a double-blind, placebo-controlled, 1,137-patient Phase 3 is as good as trial design gets.

**Rests on:**
  - [S001] randomized, double-blind, placebo- and active-comparator-controlled global Phase 3 trial
  - [S001] The trial enrolled 1,137 patients who, following complete surgical resection, were randomized 2:1

**The step we take.** Our rubric's rigor dimension scores trial design. The release records a randomised, double-blind, placebo- and active-comparator-controlled Phase 3 of 1,137 patients, which carries every design feature the top score names.

### J38

**The sentence.** Reproducibility scores 4 because the earlier Phase 2b and the much larger Phase 3 point in the same direction on RFS and DMFS, but no Phase 3 effect size has been released, so the Phase 2b magnitude has not been reproduced.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S004] The HR (95% CI) for RFS was 0.510 (0.294 to 0.887).

**The step we take.** Reproducibility asks whether an independent study found the same thing. S001 records that the larger, blinded Phase 3 met the primary RFS endpoint and the key secondary DMFS endpoint — the two the Phase 2b had moved — so the direction is reproduced. It is 4 and not 5 because S004's 0.510 is the only effect estimate in the programme and the Phase 3 has released none, so there is nothing to set beside it: what has been reproduced is the direction and not the size.

### J39

**The sentence.** Consensus scores 4 because the held sources agree on the directional Phase 3 result while the missing effect size leaves no numerical magnitude to agree on.

**Rests on:**
  - [S006] The trial met its primary endpoint of recurrence-free survival and a key secondary endpoint of distant metastasis–free survival.
  - [S009] met both its primary endpoint of recurrence-free survival (RFS) and the key secondary endpoint of distant metastasis-free survival (DMFS) at a prespecified interim analysis
  - [S010] At a prespecified interim analysis, the combination produced statistically significant and clinically meaningful improvements in recurrence-free survival (RFS) and distant metastasis-free survival (DMFS) compared with pembrolizumab alone.
  - [S011] The combination met its primary recurrence-free survival endpoint and key secondary distant metastasis-free survival endpoint at a prespecified interim analysis.
  - [S016] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S017] Efficacy endpoints were met for RFS (primary) and DMFS (key se
  - [S018] met the study’s primary endpoint of recurrence-free survival (RFS) and key secondary endpoint of distant metastasis-free survival (DMFS), according to the companies.
  - [S019] On August 19, 2026 it met BOTH endpoints — recurrence-free survival and distant metastasis-free survival — the first positive Phase 3 ever for an individualized neoantigen therapy.

**The step we take.** Consensus asks whether the sources we hold agree. All eight pieces of coverage in Appendix B that report the Phase 3 announcement state that the trial met its prespecified endpoints, and none disputes it. The sentence is scoped to the held sources in its own words — 'the held sources agree' — so it makes no claim about coverage we do not hold and is not a universal negative. It is 4 and not 5 because every one of these accounts traces to the companies' own release: there is agreement but only one underlying witness, and the missing effect size leaves no magnitude to agree on.

### J40

**The sentence.** Recency scores 5 because the central evidence is the August 2026 Phase 3 announcement, supported by 2026 longer-term follow-up of the earlier trial.

**Rests on:**
  - [S001] August 19, 2026 6:45 am EDT
  - [S002] June 1, 2026 8:00 am EDT

**The step we take.** Recency scores the age of the evidence. S001 is datelined 19 August 2026 and S002, the most recent underlying readout, 1 June 2026. Both are inside the window the rubric's top band names, so the dimension takes 5 on the dates alone.

### J41

**The sentence.** Source quality scores 3 rather than 5 for the same reason: the claim currently rests on a corporate press release, which the rubric ranks as industry analysis, not the peer-reviewed publication it will eventually become.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S018] The companies did not disclose hazard ratios, absolute event rates, P values, or other phase 3 efficacy estimates in the topline announcement.

**The step we take.** Our rubric scores source quality by what the claim currently rests on. The only account of this result is the companies' own announcement, which as Practical Dermatology records disclosed no efficacy estimates; there is no peer-reviewed publication of the Phase 3 to rest on yet.

### J42

**The sentence.** “Landmark trial succeeds” and “real: 3.94, size: 1.0” describe the same event, and only one of them tells you the numbers are still missing.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S011] The companies have not disclosed hazard ratios, confidence intervals, p-values, median follow-up or event counts for the Phase 3 trial.

**The step we take.** The release states the endpoints were met and, as MLQ News records, discloses no hazard ratio, interval, p-value or event count. Our two scores read 3.94 for whether the effect is real and 1.0 for how large it is, and both are computed on this page from the six dimension scores shown. The headline and the pair describe the same announcement; only the pair carries the fact that the magnitude is missing, which a single averaged number did not.

### J43

**The sentence.** That single release moves both scores, and both upward whatever the numbers say, because the rubric is measuring whether the evidence has been shown rather than whether it is good: is it real rises about six-tenths of a point as source quality goes to 5, and how large is it rises from 1.0 to 4 or 5 as soon as any effect size exists.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S018] The companies did not disclose hazard ratios, absolute event rates, P values, or other phase 3 efficacy estimates in the topline announcement.

**The step we take.** What the rubric does when the missing evidence arrives. S001 states the endpoints were met and S018 records that no hazard ratio, absolute rate or p-value was disclosed. Source quality is 3 because the claim rests on a release, and data support is 1 because no effect size exists; a full dataset moves the first to 5 and the second to 4 or 5 whatever the numbers say, because both dimensions score whether the evidence has been shown rather than whether it flatters. The arithmetic of the six-tenths is ours, over the published weights.

### J44

**The sentence.** If someone quotes "49%" at you, ask which trial.

**Rests on:**
  - [S001] The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS).
  - [S004] Intismeran plus pembrolizumab continued to prolong RFS (hazard ratio [HR], 0.510 [95% CI, 0.294 to 0.887) and DMFS (HR, 0.411 [95% CI, 0.200 to 0.843]), with a favorable trend in overall survival (HR, 0.471 [95% CI, 0.165 to 1.345]) versus pembrolizumab.

**The step we take.** The 49% figure belongs to the Phase 2b five-year analysis, and the Phase 3 announcement carries no effect size at all. So the question that settles which result a quoted 49% describes is which trial it came from.

### J45

**The sentence.** A 2018 erratum covering thirteen NEJM articles at once ( N Engl J Med 2018;379:2185 ) applies to this paper.

**Rests on:**
  - [S030] Prolonged Survival in Stage III Melanoma with Ipilimumab Adjuvant Therapy
  - [S030] 10.1056/NEJMoa1611299
  - [S029] This article has been corrected. See N Engl J Med. 2018 Nov 9;379(22):2185

**The step we take.** Two facts, both literally in the held records, and one inference of arithmetic. S030 is the PubMed record of the erratum: its title enumerates the articles it covers, one of which is 'Prolonged Survival in Stage III Melanoma with Ipilimumab Adjuvant Therapy', and its comment-correction list carries 10.1056/NEJMoa1611299 — so the notice applies to this paper. The count of thirteen is ours, by counting the titles that record enumerates. S029's own header says the same thing from the other side. Nothing here characterises what the notice SAYS: we do not hold it, and the sentence on the page says so.

### J46

**The sentence.** We have not been able to read it: NEJM returns 403, Europe PMC records the notice as neither open access nor in its archive, and neither PubMed nor Crossref carries an abstract for it; so we do not know whether it touches a figure on this page.

**Rests on:**
  - [S030] Prolonged Survival in Stage III Melanoma with Ipilimumab Adjuvant Therapy
  - [S029] This article has been corrected. See N Engl J Med. 2018 Nov 9;379(22):2185

**The step we take.** A scoped negative about our own searching, and it is ours by searching rather than by any document. What the held records give is that the notice exists and applies to this paper: S030 is its PubMed record and S029's own header points at it. That we could not READ it is the result of four retrievals run on 2026-09-09 and recorded in the S029 source entry — NEJM returned HTTP 403 to a script; the Europe PMC REST search for EXT_ID:31442371 returned isOpenAccess N, inPMC N and inEPMC N; the PubMed efetch record carries no AbstractText; the Crossref work for 10.1056/NEJMx180040 carries title and date with no abstract and no update-to. The sentence names all four places, which is the convention this page uses for a negative: scoped to where we looked, and dying to anyone who reads the notice. It makes no claim about what the notice says.


---

## Appendix B — what we hold, and what we could not read

Several claims in the piece are explicitly scoped to our own library — "in any
of the coverage we hold", "every outlet whose article we hold". Those claims
cannot be evaluated without knowing what that library contains, so here it is.

The rows marked below are the ones that matter most to you. A document we could
not read in full is a place where a figure could be hiding, and the single
worst error this publication has made came from exactly that gap: a set of
figures removed as unsupported that were in a document we had acquired and not
read. If you can reach any of these, please do.

| id | access | title |
|---|---|---|
| S001 | full_text_held | Merck & Moderna — Phase 3 INTerpath-001 met RFS and DMFS endpoints |
| S002 | abstract_held | Merck & Moderna — five-year KEYNOTE-942 data, ASCO 2026 |  <-- WE COULD NOT READ THIS IN FULL
| S003 | abstract_held | KEYNOTE-942: a randomised, phase 2b study — The Lancet, 2024 |  <-- WE COULD NOT READ THIS IN FULL
| S004 | full_text_held | Khattak, Carlino, Meniawy et al. — Intismeran Autogene Plus Pembrolizumab Versus Pembrolizumab  |
| S005 | abstract_held | Merck & Moderna — first detailed KEYNOTE-942 results |  <-- WE COULD NOT READ THIS IN FULL
| S006 | full_text_held | The ASCO Post — INTerpath-001 meets primary and key secondary endpoints |
| S007 | full_text_held | Three-Year Update of a Randomized Phase IIb Study of the Individualized Neoantigen Therapy Inti |
| S008 | full_text_held | Weber JS, Khattak MA, Carlino MS, et al. Individualized neoantigen therapy mRNA-4157 (V940) plu |
| S009 | full_text_held | Morning Glory Sciences — INTerpath-001 |
| S010 | full_text_held | Pharmacy Times — Phase 3 Trial Marks First Success for Personalized mRNA Cancer Therapy in Rese |
| S011 | full_text_held | MLQ News — Moderna and Merck's personalized melanoma therapy meets two Phase 3 endpoints |
| S013 | full_text_held | INTerpath-001 — ClinicalTrials.gov record. NCT05933577. |
| S014 | full_text_held | KEYNOTE-942 five-year update — ASCO 2026 abstract 9500. J Clin Oncol 44 (suppl 16; abstr 9500) |
| S015 | full_text_held | The ASCO Post, June 2026 — Vaccine Plus Pembrolizumab Reduces Risk of Recurrence in High-Risk R |
| S016 | full_text_held | Dermatology Times — Personalized mRNA-Based Melanoma Vaccine Meets Primary Endpoints in Landmar |
| S017 | full_text_held | OncLive — Intismeran Autogene Plus Pembrolizumab Meets RFS, DMFS End Points in Resected Melanom |
| S018 | full_text_held | Practical Dermatology — Intismeran Plus Pembrolizumab Meets Dual Phase 3 Melanoma Endpoints |
| S019 | full_text_held | KOL Pulse — INTerpath-001 trial profile |
| S020 | full_text_held | KEYNOTE-054 — ClinicalTrials.gov record. NCT02362594. |
| S021 | full_text_held | CheckMate 238 — ClinicalTrials.gov record. NCT02388906. |
| S022 | full_text_held | Greenland, Senn, Rothman, Carlin, Poole, Goodman, Altman — Statistical tests, P values, confide |
| S023 | full_text_held | Spruance, Reid, Grace, Samore — Hazard Ratio in Clinical Trials. Antimicrob Agents Chemother, 2 |
| S024 | full_text_held | Survival Analysis — StatPearls, NCBI Bookshelf |
| S025 | full_text_held | Singh, Mukhopadhyay — Survival analysis in clinical trials: Basics and must know areas. Perspec |
| S026 | full_text_held | KEYNOTE-716 — ClinicalTrials.gov record. NCT03553836. |
| S027 | full_text_held | Moderna & Merck — five-year KEYNOTE-942 data, January 2026 announcement |
| S028 | abstract_held | Riaz L, Komal W, Qureshi R, Khan M. FDA Approval of daratumumab and hyaluronidase-fihj plus VRd |  <-- WE COULD NOT READ THIS IN FULL
| S029 | full_text_held | Eggermont, Chiarion-Sileni, Grob et al. — Prolonged Survival in Stage III Melanoma with Ipilimu |
| S030 | full_text_held | PubMed record for the 2018 NEJM erratum, PMID 31442371 — the bibliographic record, NOT the noti |

---

## Appendix C — the universal negatives

These are the sentences that assert nothing exists. Our checks can prove a
string is in a document; they can never prove that nothing anywhere says
otherwise. Each of these can be destroyed by a single counterexample, and
finding one would be the most valuable outcome of this review.

This list is ours, made by reading the piece. It is not a guarantee that it is
complete — if you find another claim of this shape, treat it the same way.

Two of them (marked DECLARED) are also declared in machine-readable form and a
search of our own library runs against them on every publish. That search can
only see documents we hold; it is not evidence about anything outside Appendix
B, and it has already falsified one sentence on this page once.

One negative was REMOVED from this list on 2026-09-09 because it is FALSIFIED,
not because it is doubtful: "an outlet we can find no other publication citing",
about Morning Glory Sciences. We hold the disproof. The publisher's Crossref
deposit for DOI 10.1007/s11845-026-04315-0 carries a twelve-item reference list
whose reference 12 cites that outlet by name, and anyone with the DOI can
reproduce it. A correction saying the clause had been removed was published on
4 September; the clause was nevertheless still on the page five days later. It is
gone now, and so is every other characterisation of that outlet — three were
attempted and none could be supported. A negative that has been falsified does
not belong on a list of negatives inviting you to falsify them.

**The two most exposed claims are 8 and 9.** Every other negative here is
scoped to something a reader can check — "we hold", "this page", "the registry
record". Those two are scoped to the world.

1. DECLARED — **"We looked: no hazard ratio, interval or p-value for this trial
   appears in either company release, in any of the specialist or general
   coverage we hold, or in the trial's own registry record, which as of
   2 September 2026 carries no posted results at all…"** Scoped to what we
   hold. Appendix B is the list. Anything outside it that carries a Phase 3
   effect size destroys this.

2. DECLARED — **"Every survival figure in the programme is exploratory and
   rests on a handful of deaths."** This ranges over the whole programme: both
   trials, every release, both papers, four registry records. The next two
   sentences name the two figures we found (0.425 on nine deaths; 0.471 on
   fourteen). A third survival figure anywhere in the programme, or either of
   those two turning out to be something other than exploratory, destroys it.

3. **"For adjuvant PD-1 inhibitors specifically — the comparison arm in this
   very trial — neither of the two placebo-controlled trials whose registry
   records we hold — KEYNOTE-054 and KEYNOTE-716 — has posted an
   overall-survival result at all. That is an absence of a finding, not a null
   one."** Two questions, and they are separate. Is it true of those two? And
   does the scoping mislead, because a reader takes it for a claim about the
   field? The paragraph that follows deliberately excludes CheckMate 238 and
   says why; check that the exclusion is honest and not convenient.

4. **"Every outlet whose article we hold attributed those figures correctly to
   KEYNOTE-942 in its own voice"** — six outlets, all named. Two ways to break
   it: an outlet that misattributes, or the qualification "in its own voice"
   doing work it should not. That phrase was added so that an outlet quoting
   someone else loosely would not count against us. Decide whether that is a
   fair distinction or a hedge that makes the sentence unfalsifiable.

5. **"Neither reading appears in any of the general coverage we hold."**
   (The Morning Glory / Pharmacy Times disagreement about stage IIB–IIC.)
   Scoped to Appendix B.

6. **"this page holds no document about one"** — a CTLA-4 inhibitor. A claim
   about our own library, checkable against Appendix B.

7. **"the Phase 3 announcement gave no adverse-event rates for its own 1,137
   patients"**. The release does contain adverse-event percentages; they are
   KEYTRUDA label text describing other trials, which is why the sentence is
   scoped to "its own 1,137 patients". Is that scoping enough, or does the
   sentence still leave a reader with a false picture of the release?

8. **"No hazard ratio, no interval, no percentage has been published."**
   (Under "Not established".) This one is NOT scoped to what we hold. As
   written it is a claim about the world. Either it is defensible as written or
   it needs the scope the sentence in 1 carries.

9. **"Merck and Moderna have not published one"** — a subgroup breakdown by
   stage. Also unscoped, and a single company slide, poster or supplementary
   table destroys it.

10. **"Melanoma is not one of the topics our pipeline covers, so nothing here
    was produced by the scoring system that runs the site."** A claim about our
    own process. You cannot check it from outside and we are flagging it for
    that reason: take it as an assertion we are making, not as something this
    packet evidences.

---

## Appendix D — where our own machinery has not looked

This is a coverage statement, not a findings statement. It says which parts of
the page our checks have and have not examined, so you know where the absence
of a flag means nothing at all.

- **sentences the gate has seen** — warn: 219 sentence(s) on the page did not exist in the draft the gate judged (fingerprints recorded by the gate)
- **empirical sentences never judged** — warn: the gate budget for this issue is spent, so this cannot be cleared by re-gating — 43 sentence(s) carrying figures, trials or registry ids have never been examined by any role: Why this is worth a whole article Five outlets whose articles we hold named KEYNOTE-942 wh || A single hazard ratio summarising five years assumes the ratio held steady across those fi || There is one patient-level reading a hazard ratio does support.

The sentences no role has read:
  1. The Melanoma Result — What Holds Up What Holds Up What this is The rubric Issue one Issue two Issue three Who pays for this Issue one Evidence review Published 26 August 2026 · Updated 9 September 2026 · event dated 19 August 2026
  2. 14 deaths the whole Phase 2b survival analysis
  3. 0.165–1.345 the interval around that Phase 2b trend
  4. Why this is worth a whole article Five outlets whose articles we hold named KEYNOTE-942 when attributing the 49% figure — The ASCO Post, Dermatology Times, Practical Dermatology, MLQ News and OncLive.
  5. A post logged by KOL Pulse identified the figure as coming from an earlier phase 2 trial without naming KEYNOTE-942; KOL Pulse’s own text names the trial throughout and attributes the circulating hazard ratios to it.
  6. Several said plainly that no Phase 3 efficacy numbers had been released.
  7. A single hazard ratio summarising five years assumes the ratio held steady across those five years.
  8. For a therapy whose effect may build as the immune response develops, that is worth naming — and the figures on this page that drift with follow-up are what a changing ratio looks like from outside.
  9. There is one patient-level reading a hazard ratio does support.
  10. Take one treated and one untreated patient at random: at a hazard ratio of 0.510 there is about a 66% chance the treated one goes longer without recurrence, against 50% if the therapy did nothing.
  11. Spruance and colleagues put the limit of the measure well: it is the difference between the odds of winning a race and the margin of victory.
  12. The hazard ratio tells you who is likely to win.
  13. It does not tell you by how much.
  14. Two questions do most of the work.
  15. First, does the range cross 1.0?
  16. Second, and the one readers skip: how wide is it, and what would the far end mean if it were true?
  17. The first question is the convention you will meet everywhere.
  18. It is also a yes/no line drawn through a continuous quantity, which the statisticians cited at the foot of this page argue is the habit that causes most of the trouble.
  19. These are 95% intervals, the convention readers meet elsewhere.
  20. The trial registered a one-sided alpha of 0.10; its later three-year paper reports both 80% and 95% intervals for the updated analysis because the trial’s own error-control convention differs from the 95% convention drawn here.
  21. Amber bars cross the 95% no-effect line; green ones clear it.
  22. That split is a convention, not a verdict.
  23. At five years the point estimate was unchanged at 0.510 and the interval read 0.294–0.887 .
  24. Both bounds came in, the upper from 0.906 to 0.887 and the lower from 0.288 to 0.294, so the interval narrowed slightly.
  25. The crossing was resolved at year three, not year five, and what the last two years added was two more years of it holding rather than a sharper measurement.
  26. This trial's own threshold is on the record: the three-year paper says the trial was designed with approximately 80% power to detect a hazard ratio (HR) of 0.5 against a one-sided alpha of 0.10 — a permissive threshold, and a normal choice for a phase 2b trial built to find a signal rather than sett
  27. And ipilimumab is not a neutral comparator either: it is the one adjuvant therapy in this disease with a demonstrated survival benefit against placebo, so failing to separate from it is a harder test than placebo, not an uninformative one.
  28. That is a claim about PD-1 inhibitors and not about adjuvant checkpoint inhibitors as a class; a CTLA-4 inhibitor is a different drug against a different target.
  29. One adjuvant checkpoint inhibitor has shown a survival benefit against placebo in this disease.
  30. In EORTC 18071, adjuvant ipilimumab versus placebo in resected stage III melanoma reported overall survival as a prespecified secondary endpoint: 65.4% versus 54.4% at five years, HR 0.72 (95.1% CI 0.58–0.88), p=0.001.
  31. It is not standard care because the dose was 10 mg/kg and five patients died of immune-related events, not because it failed on survival.
  32. So the translation from recurrence to survival is possible in this disease.
  33. It has not yet been shown for a PD-1 inhibitor.
  34. The two are easy to read as one.
  35. The key secondary endpoint, DMFS, is investigator-assessed too.
  36. One caveat the figures on this page raise themselves: intismeran is an intramuscular injection that caused injection-site pain in 59.6% of patients and chills in 51.0% in the earlier trial; the Phase 3 comparator is a saline injection.
  37. Where a therapy is that much more reactogenic than its placebo, patients and their doctors can sometimes infer the arm — and the primary endpoint is investigator-assessed.
  38. Blinding on paper is not always blinding in the room.
  39. Central adjudication is the standard answer, and this trial does not use it.
  40. Morning Glory Sciences — we give its argument on its merits rather than on its authority — the Phase 2b population was stage IIIB–IV, the Phase 3 adds node-negative disease, and “absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit.” Pharmacy 
  41. The August announcement was a prespecified interim look — both company releases say so.
  42. The registry does not: its record has not been updated since 24 September 2025, so it carries nothing about the announcement either way.
  43. In the Lancet report, immune-mediated adverse events were similar — 36% in the combination arm and 36% in the monotherapy arm — while grade 3 or worse treatment-related events were not: 25% versus 18%.
  44. At five years the company release puts immune-related events at 45.2% versus 44%, over a longer window than the Lancet’s.
  45. Reading only the first pair would tell you the added therapy costs nothing.
  46. The three-year paper reports a hazard ratio of 0.425 on nine deaths, 95% CI 0.114 to 1.584; the five-year analysis reports 0.471 on fourteen, 95% CI 0.165 to 1.345.
  47. The earlier interval is the wider of the two, which is what nine deaths buys you against fourteen.
  48. Whether the benefit holds in stage IIB, IIC and IIIA patients, whom the earlier trial never enrolled.
  49. Reproducibility scores 4 because the earlier Phase 2b and the much larger Phase 3 point in the same direction on RFS and DMFS, but no Phase 3 effect size has been released, so the Phase 2b magnitude has not been reproduced.
  50. Consensus scores 4 because the held sources agree on the directional Phase 3 result while the missing effect size leaves no numerical magnitude to agree on.
  51. Recency scores 5 because the central evidence is the August 2026 Phase 3 announcement, supported by 2026 longer-term follow-up of the earlier trial.
  52. Readers saw 3.4 , which was the correct total of the working printed beneath it — but that working weighted two of the six dimensions differently from the rubric, which puts the same six scores at 3.35 .
  53. That single release moves both scores, and both upward whatever the numbers say, because the rubric is measuring whether the evidence has been shown rather than whether it is good: is it real rises about six-tenths of a point as source quality goes to 5, and how large is it rises from 1.0 to 4 or 5 
  54. What the numbers actually say will show up in later revisions of rigor and consensus, not in these two.
  55. The nearest scheduled comparator readout is KEYNOTE-054’s overall-survival result, anticipated in its registry record for November 2026; KEYNOTE-716’s is anticipated for October 2033.
  56. Every numerical trial result above traces to a company release, a peer-reviewed paper, a conference abstract or a trial registry record.
  57. Claims about what an outlet reported necessarily trace to the named coverage itself.
  58. The pre-publication checks test whether bound spans match held documents, whether figures appear in held documents and whether bound sources are represented in the reader-facing source set; they do not independently classify a document as news or primary.
  59. MLQ News — Moderna and Merck’s personalized melanoma therapy meets two Phase 3 endpoints Coverage.
  60. The outlet that enumerated what the announcement did not contain, quoted on this page.
  61. Dermatology Times — Personalized mRNA-Based Melanoma Vaccine Meets Primary Endpoints Practical Dermatology — Intismeran Plus Pembrolizumab Meets Dual Phase 3 Melanoma Endpoints OncLive — Intismeran Autogene Plus Pembrolizumab Meets RFS, DMFS End Points in Resected Melanoma Three of the five outlets 
  62. Held so that what this page says about them can be checked against them.
  63. The ASCO Post, June 2026 — Vaccine Plus Pembrolizumab Reduces Risk of Recurrence in High-Risk Resected Melanoma The five-year landmark rates as this page first carried them, before they were moved to the ASCO abstract that reports them.
  64. KOL Pulse — INTerpath-001 trial profile The trial profile that logged the announcement-day posts, including the one this page quotes and the one that gave the figure as phase 2 without naming the trial.
  65. Primary KEYNOTE-942 five-year update — ASCO 2026 meeting abstract 9500 Conference abstract.
  66. Source of the five-year landmark RFS and OS rates and their confidence intervals; the abstract states that no alpha was assigned to this analysis.
  67. Primary KEYNOTE-942 three-year update — ASCO 2024 abstract LBA9512 Conference abstract and presentation record.
  68. Source of the protocol statement that the trial was designed with a one-sided alpha of 0.10.
  69. Primary INTerpath-001 — ClinicalTrials.gov, NCT05933577 Registry record.
  70. Source of the Phase 3 population, placebo description and investigator-assessed RFS and DMFS endpoints.
  71. The record was last updated 24 September 2025 and carries no posted results.
  72. Primary KEYNOTE-054 — ClinicalTrials.gov, NCT02362594 Registry record.
  73. Overall survival is NOT_POSTED, with an anticipated posting date of November 2026.
  74. Primary KEYNOTE-716 — ClinicalTrials.gov, NCT03553836 Registry record.
  75. Overall survival is NOT_POSTED, with an anticipated posting date of October 2033.
  76. Primary CheckMate 238 — ClinicalTrials.gov, NCT02388906 Registry record.
  77. Source of the nivolumab-versus-ipilimumab active-comparator arms.
  78. Primary Eggermont et al. — EORTC 18071 overall survival, N Engl J Med 2016 DOI 10.1056/NEJMoa1611299; PMID 27717298; PMCID PMC5648545.
  79. Source of the adjuvant ipilimumab-versus-placebo five-year overall-survival result and immune-related deaths.
  80. A 2018 erratum covering thirteen NEJM articles at once ( N Engl J Med 2018;379:2185 ) applies to this paper.
  81. We have not been able to read it: NEJM returns 403, Europe PMC records the notice as neither open access nor in its archive, and neither PubMed nor Crossref carries an abstract for it; so we do not know whether it touches a figure on this page.
  82. Every figure we quote appears in the current PubMed record of this paper, which post-dates the erratum.
  83. Primary Greenland et al. — Statistical tests, P values, confidence intervals, and power Eur J Epidemiol 2016;31:337–350.
  84. Methodological source for the cautions against significance dichotomies and common p-value misreadings.
  85. Primary Spruance, Reid, Grace & Samore — Hazard Ratio in Clinical Trials Antimicrob Agents Chemother 2004;48(8):2787–2792.
  86. Source for the proportional-hazards assumption, the pairwise-probability interpretation and the race analogy.
  87. Primary Survival Analysis — StatPearls, NCBI Bookshelf Source for the direction a hazard ratio moves in: risk rises as the value goes above 1 and falls as it goes below.
  88. Primary Singh & Mukhopadhyay — Survival analysis in clinical trials: basics and must-know areas Perspect Clin Res 2011;2(4):145–148.
  89. Source for what a hazard ratio of 1 means, and for the caution that a hazard ratio is not a proportion of patients benefited.
  90. An outside reviewer read this page against the packet we send out, and found six sentences that were wrong.
  91. Four were errors of fact, one was a comparison two figures could not bear, and one described our own checks as doing something they do not do.
  92. The reviewer also made two errors of their own, and those are recorded here too.
  93. The registry does not say what we said it says.
  94. We wrote that the August announcement was a prespecified interim look and the register says so .
  95. The word interim appears nowhere in the NCT05933577 record, and that record has not been updated since 24 September 2025 — eleven months before the announcement it was being cited about.
  96. The interim fact is real and comes from the Merck and Moderna releases, which both use the phrase.
  97. The wider problem was ours: we had been using the registry's silence as evidence that no Phase 3 number exists, and a file nobody has touched since last September is a stale record rather than a live absence.
  98. Where the registry still appears as a negative, its last-update date now appears with it.
  99. An interval moved the wrong way.
  100. We wrote that at five years the upper bound had come in from 0.906, the lower bound had drifted out from 0.288 .
  101. The lower moved from 0.288 to 0.294, which is inward on any reading — closer to 1.0, closer to the point estimate, closer to the other bound.
  102. The interval narrowed slightly at both ends and the page now says that.
  103. Two adverse-event figures that do not belong beside each other.
  104. We set 45.2% against 44% for any-grade immune-related events, then 25% against 18% for grade 3 or worse, in a single sentence built as one contrast.
  105. They are different categories, from different documents, at different lengths of follow-up: the first pair is the five-year company release, the second is the Lancet 's two-year cut.
  106. The Lancet reports both on the same patients at the same cut — immune-mediated events 36% in each arm, grade 3 or worse treatment-related 25% against 18% — and that is the comparison now on the page, with the five-year figures given separately and their window named.
  107. Setting two correctly sourced numbers side by side where they cannot bear the comparison is the subject of this article.
  108. We did it in our own summary.
  109. A sentence that outlived the scorecard it described.
  110. When we split the score in two on 3 September we left standing a line saying the full dataset would move the score by roughly a full point, in whichever direction the numbers point .
  111. Source quality going to 5 lifts is the effect real by about six-tenths of a point; data support coming off 1 lifts how large is it from 1.0 to 4 or 5.
  112. And both move upward whatever the numbers say, because the rubric measures whether the evidence has been shown, not whether it is flattering.
  113. The sentence now says that, which is the more interesting fact about our own rubric and one we had obscured.
  114. Our sentence about adjuvant PD-1 inhibitors never reporting a survival benefit against placebo was correct and still stands.
  115. The paragraph around it was not doing what we thought.
  116. It opened by saying adjuvant melanoma trials have a history of recurrence benefits that sometimes never did translate into survival, listed three negatives, and closed by noting that this page held no document about a CTLA-4 inhibitor — true, and doing work a true sentence should not do.
  117. In EORTC 18071, adjuvant ipilimumab against placebo in resected stage III melanoma reported overall survival as a prespecified secondary endpoint: 65.4% against 54.4% at five years, HR 0.72 (95.1% CI 0.58–0.88), p=0.001.
  118. The paper is now held and cited, and the page says that the translation from recurrence to survival is possible in this disease and has not yet been shown for a PD-1 inhibitor.
  119. Listing three negatives and omitting the one positive left a reader with something we did not check and could not have defended.
  120. We told readers that every number on this page traced to a primary document and none to a news report, and that a check refuses publication otherwise.
  121. The check does not classify documents that way.
  122. It tests whether bound spans match the documents we hold, whether figures appear in those documents, and whether bound sources reach the reader in the source list.
  123. It has no opinion on what counts as news.
  124. The sentence now describes what the checks do, and the source enumeration now includes conference abstracts, which is what the five-year rates actually rest on.
  125. This is the second time on this page that a careful check has been described by careless prose.
  126. The entry below says that is the failure worth keeping in view, and it did not take the first time.
  127. What the blinding does not cover.
  128. We wrote that an assessor who does not know the arm cannot favour it, and printed, a few hundred words later, that the therapy caused injection-site pain in 59.6% of patients and chills in 51.0%.
  129. The Phase 3 comparator is a saline injection.
  130. Where a therapy is that much more reactogenic than its placebo, patients and their doctors can sometimes infer the arm — and the primary endpoint is investigator-assessed, as is the key secondary.
  131. Both halves were on the page and we had never put them together.
  132. The caveat is now in the blinding section.
  133. The reviewer was wrong twice, and this log should say so.
  134. Asked to check our claim about overall survival in KEYNOTE-054 and KEYNOTE-716, the reviewer confirmed an earlier version of it — that both trials had posted a survival result carrying no statistical analysis.
  135. Both registry records mark the measure NOT_POSTED , with anticipated posting dates of November 2026 and October 2033; the reviewer had read one field and not the one that mattered.
  136. We had already corrected this on 4 September, and accepting the confirmation would have put the error back.
  137. The reviewer also proposed attaching the three-year paper's 80% interval, 0.351–0.743, to the 2023 readout.
  138. It belongs to the three-year hazard ratio of 0.510, and no 80% interval for the 2023 result exists in any document we hold.
  139. We record them because an outside review is not a one-way audit, and a log that only ever reports the reviewer catching us describes something that did not happen.
  140. The nearest scheduled answer to the survival question is now on the page: KEYNOTE-054's overall-survival result is anticipated in its registry record for November 2026, and KEYNOTE-716's for October 2033.
  141. The hazard-ratio explainer now names the assumption underneath a single hazard ratio — that the ratio held steady across the whole follow-up, which the three-year paper's own methods assume in fitting a Cox proportional-hazards model — and adds the one patient-level reading a hazard ratio does suppo
  142. The confidence-interval chart now says that its amber and green split is a convention rather than a verdict, and that this trial registered a one-sided alpha of 0.10 rather than the 95% convention the chart draws.
  143. The Not established list now names stage IIIA alongside IIB and IIC, since the Phase 3 added all three below the earlier trial's floor.
  144. The two figures in the summary strip that belong to the Phase 2b now say so.
  145. The three scores we had never explained — reproducibility, consensus and recency, together more than half of is the effect real — now carry their reasoning.
  146. And the three-year survival interval is now given at 95%, 0.114–1.584, so that it can be read against the five-year 0.165–1.345 rather than beside it at a different width; at equal width the earlier interval is the wider of the two, which is what nine deaths buys against fourteen.
  147. We overstated our own error, and readers saw that.
  148. Since 4 September this page has told readers that the composite it printed was out by 0.05 against its own working .
  149. The working printed beside 3.4 came to 3.40 exactly, and 3.4 is the number it produces; no reader was ever shown a figure that disagreed with the arithmetic underneath it, and no rounding was involved.
  150. What differed was the working itself: reproducibility and recency were shown at 15% each where the rubric gives them 20% and 10% .
  151. That is a real error, it is the one that put the total 0.05 high, and it is recorded in the entry below — but it is not the error we confessed to.
  152. A page that prints its arithmetic and totals it correctly, from weights that are not the published ones, is not a page whose display disagrees with its own working.
  153. The distinction matters because the 2 September entry below already records a correction notice that was worse than the error it corrected, and named that as the failure worth keeping in view.
  154. This is the same failure, in the entry that was supposed to have learned from it.
  155. The commit history settles it: from 26 August the page printed (3×.25)+(1×.20)+(4×.15)+(4×.15)+(5×.15)+(5×.10) , and on 3 September the commit that published the rubric corrected the same working to the rubric's weights in one change.
  156. The page now says less about one outlet than we promised it would.
  157. The 4 September notice said the Morning Glory Sciences clause had been replaced with a specialist outlet, and we give its argument on its merits .
  158. It has not been, and it will not be.
  159. Three characterisations of that outlet have now been attempted — the English edition of a non-English site, an outlet no other publication cites, and a specialist outlet — and the first two were withdrawn as unsupportable.
  160. The third has no better support than they did.
  161. What the record actually holds on the outlet's standing is one citation: reference 12 of a letter in the Irish Journal of Medical Science , which the publisher deposited to Crossref and which we have now read there, in a letter whose own text we have never read.
  162. One citation in one reference list establishes that the outlet is cited.
  163. It establishes nothing about whether it is specialist, authoritative, or anything else.
  164. So the sentence now carries no characterisation at all.
  165. It names the outlet, gives its argument, and tells you to weigh the argument.
  166. Saying less is what we can actually support, and a fourth adjective would be the same mistake with a different word.
  167. And what the review did not catch.
  168. Publishing the corrections above meant binding every sentence on this page to the words it rests on, which is the check our own account of ourselves depends on and which had fallen behind.
  169. Doing it found three more things.
  170. We had credited KOL Pulse with giving the 49% figure as a phase 2 result without naming the trial; the outlet names KEYNOTE-942 throughout and attributes the circulating hazard ratios to it, and the wording we praised belongs to a post it logged, not to the outlet.
  171. That sentence now says whose it is.
  172. The New England Journal paper behind the ipilimumab counterexample was cited here before it was held: the entry above says the paper is now held and cited , and on the day that was drafted the library contained nothing.
  173. It has been obtained and the sentence is now true.
  174. And nine documents this page rests on were missing from the list of sources a reader sees — including the coverage the consensus score rests on, which a reader cannot check against a list that does not name it.
  175. Three small figures went the other way: a word we could not support from a document, a comparison we can now state as two numbers rather than one, and an arithmetic step of our own we had printed as though a document reported it.
  176. Two days of changes, and an admission about this log before them.
  177. Most of what follows was written at the time and filed under the headings for 28 August and 2 September, which dated our own corrections to before we made them.
  178. The paragraphs are unchanged; only the date above them is.
  179. Nothing was removed to make room.
  180. The composite readers saw was not weighted the way the rubric weights it.
  181. The published page scored this assessment 3.4 , beside a working that gave reproducibility and recency 15% each.
  182. The rubric gives them 20% and 10% .
  183. So the printed number was the correct total of the arithmetic printed underneath it: no reader was ever shown a figure that disagreed with the working beside it, and no rounding was involved, because that working came to 3.40 exactly.
  184. What was wrong was the working.
  185. Two dimensions carried weights that were not the rubric's, and the two errors did not cancel — they left the total 0.05 high.
  186. The rubric was published the same day and the weights were corrected to match it, at which point the same six scores came to 3.35 .
  187. The composite was abolished shortly afterwards, for a different reason.
  188. The correction is recorded here because it happened to a figure readers could see.
  189. We had misquoted our own rubric.
  190. Under what it actually says, a score of 1 is right and needs no explaining away.
  191. And the third figure came back after all.
  192. On 2 September we said a “five-year topline of 20 January 2026” reporting a one-sided nominal p = 0.0075 would stay out until somebody produced it.
  193. What the registry actually says about overall survival.
  194. We had written that KEYNOTE-054 and KEYNOTE-716 each posted an overall-survival result that carries no statistical analysis at all .
  195. Both records mark the measure NOT_POSTED with a posting date still ahead of it — November 2026 for KEYNOTE-054, October 2033 for KEYNOTE-716.
  196. A result withheld and a result not yet due are different things, and the first reads as evasion where the second is a schedule.
  197. The sentence now says which one this is.
  198. CheckMate 238 was never evidence for what we used it for.
  199. We had counted it among three trials that had not shown a survival benefit against placebo, and explained in the next breath that it has no placebo arm.
  200. Counting a trial that cannot answer the question makes a two-trial observation look like a three-trial one.
  201. The paragraph now sets it aside explicitly, and names its arms — every patient in it received an active treatment.
  202. Four fixes, all of them the kind this piece exists to catch in other people.
  203. Our p-value gloss said that if the drug were useless you would see a result this good about 5% of the time, which quietly drops every other assumption the calculation rests on; the assumptions are now part of the sentence.
  204. We had defined distant metastasis-free survival as time until the cancer spreads, omitting death, which is half the endpoint.
  205. Twice we described patients as recurring where the measure counts recurrence or death.
  206. And we said the Phase 3 is blinded against the assessment bias the earlier trial carried, when what blinding addresses is the direction that bias can run in — both trials keep investigator assessment.
  207. What we said about Morning Glory Sciences, and what we did not do about it.
  208. We had described it as the English edition of a non-English industry site.
  209. We could not stand that up, and we replaced it with a narrower claim: that it is an outlet we can find no other publication citing.
  210. A 2026 letter in the Irish Journal of Medical Science cites it in its reference list, and on 4 September we published a correction saying so — a correction which stated that the clause was gone and that the sentence now read differently.
  211. It was on the page when that correction was published, and it stayed there until 9 September.
  212. The replacement wording the correction named has never been on this page at all.
  213. This paragraph, in the version first drafted for this entry, repeated the falsified clause as though it were the correction: it was written on 8 September by the outside reviewer, from a diff of two page states, without reading the corrections file that said the claim was false.
  214. The clause is now removed, and so is every other characterisation of the outlet.
  215. And one hazard ratio did circulate under the Phase 3’s name.
  216. This article’s subject happened in public on announcement day, and the page now shows it.
  217. A melanoma oncologist posted, in a roundup we hold, Exciting announcement today from Phase3 INTerpath001 followed by RFS HR=0.51 and DMFS HR=0.41.
  218. The outlet that logged the post said so itself on the same page.
  219. Every numerical trial result above traces to a company release, a peer-reviewed paper, a conference abstract or a trial registry record; claims about what an outlet reported trace to the named coverage itself.

The model-based fact-check gate has now run its budgeted number of times for
this issue. The sentences listed above as unread will not be read by it before
publication, which makes them exactly the sentences worth your attention.

Two further known blind spots, recorded in `docs/whatholdsup-open-gaps.md`:
the page's meta description ships as prose that no check reads, and material
inside `<q>` quotation marks is invisible to the test that decides whether a
sentence is empirical — so a figure that appears only inside a quotation is not
required to have a binding row.

---

## The piece

The full page follows as HTML. Read it as a reader would.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Melanoma Result — What Holds Up</title>
<meta name="description" content="Merck and Moderna announced a Phase 3 melanoma success and released no Phase 3 numbers. What was actually published, and what it will and will not support.">
<link rel="canonical" href="https://whatholdsup.org/melanoma">
<meta property="og:type" content="article">
<meta property="og:site_name" content="What Holds Up">
<meta property="og:title" content="The Melanoma Result — What Holds Up">
<meta property="og:description" content="Merck and Moderna announced a Phase 3 melanoma success and released no Phase 3 numbers. What was actually published, and what it will and will not support.">
<meta property="og:url" content="https://whatholdsup.org/melanoma">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The Melanoma Result — What Holds Up">
<meta name="twitter:description" content="Merck and Moderna announced a Phase 3 melanoma success and released no Phase 3 numbers. What was actually published, and what it will and will not support.">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,400;0,500;0,600;1,400&family=Karla:ital,wght@0,300;0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<div class="wrap">
<nav class="sitenav">
  <a class="brand" href="/">What Holds Up</a>
  <a href="/what-this-is">What this is</a>
  <a href="/the-rubric">The rubric</a>
  <a href="/melanoma" aria-current="page">Issue one</a>
  <a href="/cdk46">Issue two</a>
  <a href="/deskilling">Issue three</a>
  <a href="/who-pays-for-this">Who pays for this</a>
</nav>


<header>
  <div class="kicker-row">
    <span class="pill acc">Issue one</span>
    <span class="pill inert">Evidence review</span>
    <span class="meta">Published 26 August 2026 &middot; Updated <a href="#updates">9 September 2026</a> &middot; event dated 19 August 2026</span>
  </div>
  <h1>The Melanoma Result</h1>
  <div class="domain">whatholdsup.org</div>
  <p class="standfirst">Merck and Moderna announced that a large trial of a personalised mRNA cancer therapy succeeded in melanoma. Several outlets called it a landmark. This is what was actually released, what was not, and what the numbers underneath it will and will not support.</p>
</header>

<div class="strip">
  <div data-whu="restates"><b>1,137</b><span>patients in the Phase&nbsp;3 trial</span></div>
  <div><b>0</b><span>Phase&nbsp;3 efficacy numbers released</span></div>
  <div><b>14 deaths</b><span>the whole Phase 2b survival analysis</span></div>
  <div data-whu="restates"><b>0.165–1.345</b><span>the interval around that Phase 2b trend</span></div>
</div>

<div class="finding">
  <span class="kicker">The short version</span>
  <p><strong>The Phase 3 announcement reports no numerical Phase 3 results.</strong> It reports a result — the trial met its primary endpoint of recurrence-free survival and its key secondary endpoint of distant metastasis-free survival, which is a real and significant finding. It describes the trial in detail, and it does quote hazard ratios, but every one of them belongs to an earlier, smaller trial, and the release says so. Of the study it is actually announcing it says only that the endpoints were met, "statistically significant and clinically meaningful". No hazard ratio, no interval, no p-value, no percentage.</p>
  <p>So the numbers carried in the coverage — the 49% reduction in the hazard of recurrence or death, the 59% reduction in the hazard of distant metastasis or death, both from the five-year follow-up — describe <strong>a different trial</strong>: an open-label study of 157 patients, not the blinded study of 1,137 that was announced.</p>
  <p>And the one endpoint that would tell you whether anyone <em>lives longer</em> rests, at five years, on an analysis the companies label only <strong>"n=14"</strong>. The label is the release's and it does not say fourteen of what; the paper does, in its own sentence: <q>7 of 107 patients (6.5%) in the intismeran plus pembrolizumab arm and 7 of 50 (14.0%) in the pembrolizumab arm died</q>. Fourteen deaths, seven in each arm &mdash; not fourteen patients. They call it an encouraging trend. The interval around it runs from a hazard ratio of 0.165 — a rate of death about 84% lower than the comparison group's — to 1.345, about 35% higher. Both ends are rate comparisons, not numbers of lives.</p>
  <p>None of this means the treatment does not work. It probably does. It means the public has not been shown how well. Most specialist outlets attributed the earlier trial's figures correctly. The problem is not misattribution; it is the work those correctly attributed figures still do next to a Phase&nbsp;3 headline. What follows is the layer beneath even the careful reporting.</p>
</div>

<section>
  <div class="section-head">
    <h2>What was announced, and what was not</h2>
    <p>What correct attribution still leaves open.</p>
  </div>

  <p class="lede">On 19 August 2026, Merck and Moderna announced that INTerpath-001 — a randomised, double-blind, placebo- and active-comparator-controlled Phase 3 trial in 1,137 patients — met its primary endpoint of recurrence-free survival and its key secondary endpoint of distant metastasis-free survival at an interim analysis.</p>

  <p>That is a real and significant result. A double-blind trial of that size is the strongest instrument this field has, and it agreed with the smaller study that preceded it.</p>

  <p><strong>The release contains no hazard ratio, no confidence interval, no p-value and no percentage describing the size of that effect.</strong> It does contain hazard ratios — 0.51 for recurrence, 0.411 for distant metastasis — but those are the five-year results of KEYNOTE-942, the 157-patient trial that preceded this one, and the release says so. Of the 1,137-patient trial it is announcing, the release states that both endpoints were met and gives no figure for either. No numbers have been released since. The companies say <q>These data will be presented at an upcoming international medical meeting and shared with regulatory authorities.</q> Announcing topline results ahead of a conference presentation is routine, and this piece is not an accusation that anything improper happened. It is about what a reader can and cannot conclude in the interval.</p>

  <div class="note">
    <span class="kicker">Why this is worth a whole article</span>
    <p>Five outlets whose articles we hold named KEYNOTE-942 when attributing the 49% figure &mdash; The ASCO Post, Dermatology Times, Practical Dermatology, MLQ News and OncLive. A post logged by KOL Pulse identified the figure as coming from an earlier phase 2 trial without naming KEYNOTE-942; KOL Pulse&rsquo;s own text names the trial throughout and attributes the circulating hazard ratios to it. Several said plainly that no Phase 3 efficacy numbers had been released. <a href="https://mlq.ai/news/moderna-mercks-personalized-melanoma-therapy-meets-two-phase-3-endpoints/">MLQ News</a>: <q>The companies have not disclosed hazard ratios, confidence intervals, p-values, median follow-up or event counts for the Phase 3 trial.</q> <a href="https://practicaldermatology.com/news/intismeran-plus-pembrolizumab-meets-dual-phase-3-melanoma-endpoints/2488176/">Practical Dermatology</a>: <q>The companies did not disclose hazard ratios, absolute event rates, P values, or other phase 3 efficacy estimates in the topline announcement.</q> And <a href="https://www.dermatologytimes.com/view/personalized-mrna-based-melanoma-vaccine-meets-primary-endpoints-in-landmark-phase-3-trial">Dermatology Times</a>: <q>Detailed phase 3 efficacy metrics (e.g., HRs) were not disclosed; OS and other secondary endpoints remain immature</q> (An earlier version of this sentence named OncLive and FierceBiotech when we held neither. The OncLive article was obtained on 3&nbsp;September, attributes the figures to the phase 2b trial like the rest, and is named again. FierceBiotech we still do not hold, so it is not.)</p>
    <p>The problem is not misattribution. What is left is subtler and harder to fix: the figures are <strong>correctly attributed and still doing work they cannot do.</strong> A reader who sees "49% reduction" three paragraphs under "Phase 3 succeeds" comes away with a sense of how large this effect is. That sense is drawn from 157 patients in an open-label trial, and the study that could correct it has released no number describing the size of its own effect. Nobody has to be careless for that to happen.</p>
  </div>
</section>

<section>
  <div class="section-head">
    <h2>How to read a cancer trial result</h2>
    <p>Five terms that carry almost all the meaning, each explained with a real number from this story.</p>
  </div>

  <div class="term">
    <div class="term-hd">
      <span class="term-name">Hazard ratio</span>
      <span class="term-sym">HR</span>
    </div>
    <p>A comparison of how <em>fast</em> something is happening in two groups. An HR of 1.0 means the groups are identical. Below 1.0 means the treatment group is doing better; above 1.0 means worse.</p>
    <p>The value is a rate, not a headcount. <strong>An HR of 0.51 does not mean 49% of patients were saved.</strong> It means that at any given moment during the trial, someone in the treatment group was recurring or dying at about half the rate of someone in the comparison group. A single hazard ratio summarising five years assumes the ratio held steady across those five years. For a therapy whose effect may build as the immune response develops, that is worth naming &mdash; and the figures on this page that drift with follow-up are what a changing ratio looks like from outside.</p>
    <div class="worked">
      <span class="lbl">In this story</span>
      At five years of follow-up, KEYNOTE-942 reported a recurrence-free survival hazard ratio of <b>0.510</b>. Reported as a percentage that becomes "a 49% reduction in the hazard of recurrence or death" — a correct restatement of the ratio, and still a relative rate rather than a share of patients spared.
    </div>
    <div class="warn">
      <span class="lbl">The number that matters more</span>
      Relative reductions sound larger than they feel. The <b>absolute</b> figures, at five years: <b>68.8%</b> of combination patients were recurrence-free (95% CI 56.3&ndash;78.3) versus <b>49.1%</b> on pembrolizumab alone (33.3&ndash;63.0). That is a gap of roughly <b>20 percentage points</b> at the five-year mark — a far more tangible figure than the hazard ratio, and the one that rarely reaches a headline. It describes that moment in the follow-up, not the whole of it; the gap may be wider or narrower earlier and later. There is one patient-level reading a hazard ratio does support. Take one treated and one untreated patient at random: at a hazard ratio of 0.510 there is about a 66% chance the treated one goes longer without recurrence, against 50% if the therapy did nothing. Spruance and colleagues put the limit of the measure well: it is the difference between the odds of winning a race and the margin of victory. The hazard ratio tells you who is likely to win. It does not tell you by how much.
    </div>
  </div>

  <div class="term">
    <div class="term-hd" data-whu="restates">
      <span class="term-name">Confidence interval</span>
      <span class="term-sym">95% CI</span>
    </div>
    <p>Every trial measures a sample, not the world. The confidence interval is the range of true effects reasonably consistent with what the researchers saw. A narrow interval means the trial pinned the answer down. A wide one means it did not.</p>
    <p><strong>Two questions do most of the work. First, does the range cross 1.0?</strong> Because 1.0 means no difference at all. If the range includes 1.0, then "this treatment does nothing" is still among the possibilities the data cannot rule out. <strong>Second, and the one readers skip: how wide is it, and what would the far end mean if it were true?</strong> The first question is the convention you will meet everywhere. It is also a yes/no line drawn through a continuous quantity, which the statisticians cited at the foot of this page argue is the habit that causes most of the trouble.</p>

    <div class="ci">
      <div class="ci-row">
        <div class="ci-lab"><b>Recurrence-free</b>first readout, 2023 · HR 0.561</div>
        <div class="ci-track">
          <div class="ci-axis"></div><div class="ci-null" style="left:66.67%"></div>
          <div class="ci-bar cross" style="left:20.60%; width:47.20%"></div>
          <div class="ci-pt cross" style="left:37.40%"></div>
        </div>
      </div>
      <div class="ci-row">
        <div class="ci-lab"><b>Recurrence-free</b>5-year · HR 0.510</div>
        <div class="ci-track">
          <div class="ci-axis"></div><div class="ci-null" style="left:66.67%"></div>
          <div class="ci-bar ok" style="left:19.60%; width:39.53%"></div>
          <div class="ci-pt ok" style="left:34.00%"></div>
        </div>
      </div>
      <div class="ci-row">
        <div class="ci-lab"><b>Distant metastasis-free</b>5-year · HR 0.411</div>
        <div class="ci-track">
          <div class="ci-axis"></div><div class="ci-null" style="left:66.67%"></div>
          <div class="ci-bar ok" style="left:13.33%; width:42.87%"></div>
          <div class="ci-pt ok" style="left:27.40%"></div>
        </div>
      </div>
      <div class="ci-row">
        <div class="ci-lab"><b>Overall survival</b>exploratory · HR 0.471 · "n=14"</div>
        <div class="ci-track">
          <div class="ci-axis"></div><div class="ci-null" style="left:66.67%"></div>
          <div class="ci-bar cross" style="left:11.00%; width:78.67%"></div>
          <div class="ci-pt cross" style="left:31.40%"></div>
        </div>
      </div>
      <div class="ci-scale">
        <div></div>
        <div class="ci-ticks" data-whu="scale">
          <span class="t0" style="left:0%">0</span><span style="left:33.33%">0.5</span><span style="left:66.67%">1.0 — no effect</span><span class="t1" style="right:0">1.5</span>
        </div>
      </div>
    </div>
    <p class="ci-cap">All four intervals are from KEYNOTE-942, the 157-patient Phase 2b. These are 95% intervals, the convention readers meet elsewhere. The trial registered a one-sided alpha of 0.10; its later three-year paper reports both 80% and 95% intervals for the updated analysis because the trial&rsquo;s own error-control convention differs from the 95% convention drawn here. Amber bars cross the 95% no-effect line; green ones clear it. That split is a convention, not a verdict. The Phase 3 has no bar here, because it has released no effect size to draw.</p>

    <div class="worked">
      <span class="lbl">What time did to the top two bars</span>
      When KEYNOTE-942 first reported in 2023, its recurrence result was <b>HR 0.561, 95% CI 0.309–1.017</b> — the interval crossed 1.0, so on a two-sided 5% criterion "no effect" could not be ruled out. By the three-year readout at ASCO 2024, since published in full, the interval no longer crossed it: <b>HR 0.510, 95% CI 0.288–0.906</b> — though that paper states plainly that its analyses were <b>descriptive only</b> and not intended for formal hypothesis testing, so this is an interval that stopped including 1.0 rather than a threshold anyone crossed. At five years the point estimate was unchanged at <b>0.510</b> and the interval read <b>0.294–0.887</b>. Both bounds came in, the upper from 0.906 to 0.887 and the lower from 0.288 to 0.294, so the interval narrowed slightly. The crossing was resolved at year three, not year five, and what the last two years added was two more years of it holding rather than a sharper measurement. More data, more certainty, and a recurrence effect that <b>held up rather than fading</b> — one of the better signs that an effect is real.<br><br>
      Not everything moved that way. Distant metastasis-free survival was a <b>62%</b> reduction in hazard at three years and <b>59%</b> at five. That is a small easing, well inside the noise of a trial this size, and we mention it because a piece that only reported the numbers moving in the flattering direction would be doing the thing this article is about.
    </div>
    <div class="warn">
      <span class="lbl">What the bottom bar is telling you</span>
      The overall survival interval runs <b>0.165 to 1.345</b>. At one end the treated group's rate of death would be about a sixth of the control group's; at the other it would be about a third higher. It is that wide because it rests on fourteen deaths, seven in each arm — the companies report the count alongside the hazard ratio, so the sparseness is disclosed rather than hidden. Reported as survival rates, the same analysis reads <b>92.2%</b> alive at five years versus <b>71.3%</b> &mdash; 95% CI 84.2&ndash;96.3 and <b>35.4&ndash;89.6</b>. Look at that second interval: on seven deaths in fifty patients it runs from a third of them alive to nine in ten, which is another way of saying the same thing the hazard ratio says. A large observed gap, and one the data can neither confirm nor rule out. (The full paper reports its landmark rates only to 48 months &mdash; its figure legend says so &mdash; which is why the five-year rates above come from the report of the analysis rather than from the paper.) This is what "an encouraging trend" looks like underneath, and it is why the trend is labelled exploratory. The five-year analyses were <b>descriptive</b>: they were not designed to test a hypothesis. No p-value was released for this survival analysis at all, which is what a descriptive analysis means: the figures are reported, and nothing is being tested against a threshold registered in advance.
    </div>
  </div>

  <div class="term">
    <div class="term-hd">
      <span class="term-name">p-value</span>
      <span class="term-sym">p</span>
    </div>
    <p>The probability of seeing a result at least this good <em>if the treatment actually did nothing</em>. A small p-value means the result would be a surprising fluke. By convention, below 0.05 is called statistically significant — an arbitrary line, but a widely used one.</p>
    <div class="warn">
      <span class="lbl">The universal misreading</span>
      A p-value of 0.05 does <b>not</b> mean a 95% chance the drug works. It means: if the no-effect hypothesis and the other assumptions behind the analysis were all correct, a result at least this extreme would turn up about 5% of the time. The assumptions are part of the claim, not a footnote to it. It describes the surprise, not the probability of the conclusion.
    </div>
    <div class="worked">
      <span class="lbl">In this story — and this is the interesting part</span>
      The April 2023 press release reported KEYNOTE-942 as <b>one-sided p = 0.0266</b>. When the same data were published in <em>The Lancet</em>, they came with <b>two-sided p = 0.053</b>, although the prespecified analysis was one-sided.<br><br>
      A one-sided test asks only "is it better?" A two-sided test asks "is it different, in either direction?" For a symmetric test, and when the one-sided test points the way the effect actually went, the two-sided p-value is about double the one-sided one, so the same data gives 0.0266 one way and 0.053 the other — identical evidence, measured against a different question. Neither is dishonest, and a one-sided test pre-specified for a mid-stage trial is a normal choice. This trial's own threshold is on the record: the three-year paper says the trial was <q>designed with approximately 80% power to detect a hazard ratio (HR) of 0.5</q> against a one-sided alpha of 0.10 &mdash; a permissive threshold, and a normal choice for a phase 2b trial built to find a signal rather than settle one &mdash; and the ASCO 2024 deck states the same threshold in its own words &mdash; <q>1-sided alpha of 0.1 per protocol</q>. So <b>0.0266 was inside its own prespecified threshold by a wide margin</b>, and 0.053 is a near miss only against a 0.05 line this trial never used. <b>0.0266 reads as a clear win and 0.053 reads as a near miss, and they are the same result.</b> The confidence interval is the tell: 0.309–1.017 crosses 1.0, which is exactly what a two-sided 95% interval keys on &mdash; the convention journals print, and not the threshold this trial set for itself, which was a one-sided alpha of 0.10 and which 0.0266 was inside.
    </div>
  </div>

  <div class="term">
    <div class="term-hd">
      <span class="term-name">"Met its primary endpoint"</span>
    </div>
    <p>Before a trial starts, researchers register one main question and a statistical threshold for answering it. "Met its primary endpoint" means the threshold was crossed. It is a pass/fail statement.</p>
    <p><strong>It contains no information about size.</strong> A therapy that reduces the hazard of recurrence by 8% and one that halves it both produce that sentence. This is why the absence of a hazard ratio in the Phase 3 announcement matters: "met its endpoint" is the floor of what could be said, not a summary of what was found.</p>
    <div class="worked">
      <span class="lbl">Also worth knowing</span>
      The Phase 3 result came at an <b>interim analysis</b> — a pre-planned look before the trial finishes. Peeking early raises the odds of a false positive, so interim looks use a stricter threshold to compensate. Passing one is a real result, not a preliminary hint. But the trial continues, and the final picture can move.
    </div>
  </div>

  <div class="term">
    <div class="term-hd">
      <span class="term-name">What is being measured</span>
      <span class="term-sym">RFS · DMFS · OS</span>
    </div>
    <p>Three different questions, routinely blurred together in coverage.</p>
    <p><strong>Recurrence-free survival (RFS)</strong> — how long until the cancer comes back anywhere, or the patient dies. <strong>Distant metastasis-free survival (DMFS)</strong> — how long until it spreads to distant organs or the patient dies; the spread is the more dangerous kind of return. <strong>Overall survival (OS)</strong> — how long until death, from any cause.</p>
    <div class="warn">
      <span class="lbl">The distinction that matters most</span>
      OS is the only endpoint that measures <b>length of life</b> directly. DMFS tells you the cancer did not reach distant organs — a clinically important outcome in its own right, not a stand-in for survival. RFS tells you the cancer stayed away anywhere, or the patient survived. All three are meaningful and none is a substitute for another. Adjuvant melanoma trials have a history of recurrence benefits that took years to translate into survival benefits, and sometimes never did. For adjuvant <b>PD-1</b> inhibitors specifically &mdash; the comparison arm in this very trial &mdash; neither of the two placebo-controlled trials whose registry records we hold &mdash; KEYNOTE-054 and KEYNOTE-716 &mdash; has posted an overall-survival result at all. That is an absence of a finding, not a null one. CheckMate&nbsp;238, the third record we hold, cannot bear on the question at all. Its two arms are labelled <q>Ipilimumab and Placebo matching Nivolumab</q> and <q>Nivolumab and Placebo matching Ipilimumab</q>: the placebos are the dummies that keep it blinded, one for each drug, and every patient in it received an active treatment. There is no placebo group to compare against. That rests on three registry records. <b>KEYNOTE-054</b> and <b>KEYNOTE-716</b> are both pembrolizumab against placebo; each lists overall survival as a secondary endpoint, and each registry record marks that result <q>NOT_POSTED</q> with a posting date still ahead of it &mdash; November 2026 for KEYNOTE-054, October 2033 for KEYNOTE-716. The measure is declared; the number is not there. <b>CheckMate 238</b>&rsquo;s arms are nivolumab and ipilimumab, so there is no placebo arm to report against. And ipilimumab is not a neutral comparator either: it is the one adjuvant therapy in this disease with a demonstrated survival benefit against placebo, so failing to separate from it is a harder test than placebo, not an uninformative one. That is a claim about PD-1 inhibitors and not about adjuvant checkpoint inhibitors as a class; a CTLA-4 inhibitor is a different drug against a different target. One adjuvant checkpoint inhibitor has shown a survival benefit against placebo in this disease. In EORTC 18071, adjuvant ipilimumab versus placebo in resected stage III melanoma reported overall survival as a prespecified secondary endpoint: 65.4% versus 54.4% at five years, HR 0.72 (95.1% CI 0.58&ndash;0.88), p=0.001. It is not standard care because the dose was 10 mg/kg and five patients died of immune-related events &mdash; not because it failed on survival. So the translation from recurrence to survival is possible in this disease. It has not yet been shown for a PD-1 inhibitor. In this programme, overall survival has been reported only as an exploratory analysis in the smaller trial, on an "n=14" &mdash; fourteen deaths among 157 patients, seven in each arm. The Phase 3 is still measuring it.
    </div>
  </div>
</section>

<section>
  <div class="section-head">
    <h2>The two trials, side by side</h2>
    <p>The two are easy to read as one. Different sizes, different patients, different rigour &mdash; and only one has published numbers.</p>
  </div>
  <div class="tablewrap" data-whu="restates">
    <table>
      <thead>
        <tr><th></th><th>KEYNOTE-942</th><th>INTerpath-001</th></tr>
      </thead>
      <tbody>
        <tr><td>Phase</td><td>2b</td><td><strong>3</strong></td></tr>
        <tr><td>Patients</td><td class="num">157 (107 vs 50)</td><td class="num"><strong>1,137</strong> (2:1)</td></tr>
        <tr><td>Population</td><td>Stage IIIB–IV resected</td><td>Stage <strong>IIB</strong>–IV resected</td></tr>
        <tr><td>Blinding</td><td><span class="absent">Open-label</span> — everyone knew who got what</td><td><strong>Double-blind, placebo- and active-comparator-controlled</strong></td></tr>
        <tr><td>Recurrence-free survival</td><td class="num">HR 0.510 (0.294–0.887)<br>at 5 years</td><td class="absent">met endpoint · not released</td></tr>
        <tr><td>Distant metastasis-free</td><td class="num">HR 0.411 (0.200–0.843)</td><td class="absent">met endpoint · not released</td></tr>
        <tr><td>Overall survival</td><td class="num">HR 0.471 (0.165–1.345)<br>exploratory, "n=14"</td><td class="absent">still being measured</td></tr>
      </tbody>
    </table>
  </div>

  <h3 class="mini">Why the blinding row matters</h3>
  <p>KEYNOTE-942 was <strong>open-label</strong>: patients and doctors both knew which arm they were in, and the primary endpoint was judged by those same investigators. That is a genuine weakness. A doctor who knows a patient received an experimental therapy may, entirely unconsciously, scan and interpret differently.</p>
  <p>The Phase 3 substantially reduces that problem. It is double-blind and placebo-controlled, so nobody assessing a recurrence knows which treatment produced it. <strong>It is the more trustworthy trial by a wide margin</strong> &mdash; seven times larger, and blinded against the <em>direction</em> the earlier trial&rsquo;s assessment bias could run in. Not against investigator assessment itself, which both trials keep, as the next paragraph sets out. Which is precisely why it is frustrating that its numbers are the ones we do not have.</p>
  <p>One detail has had little attention. Merck's own description of the Phase 3 defines its primary endpoint as recurrence <strong>"as assessed by the investigator"</strong> rather than by central adjudication. That leaves clinical judgement in the endpoint, though the double-blind design substantially protects against it running in one direction: an assessor who does not know the arm cannot favour it. The key secondary endpoint, DMFS, is investigator-assessed too. One caveat the figures on this page raise themselves: intismeran is an intramuscular injection that caused injection-site pain in 59.6% of patients and chills in 51.0% in the earlier trial; the Phase 3 comparator is a saline injection. Where a therapy is that much more reactogenic than its placebo, patients and their doctors can sometimes infer the arm &mdash; and the primary endpoint is investigator-assessed. Blinding on paper is not always blinding in the room. Central adjudication is the standard answer, and this trial does not use it. An independent review committee would move that judgement to blinded central assessors rather than remove it, and adjuvant melanoma therapies have been approved on investigator-assessed recurrence before. It is a difference worth knowing about, not a flaw.</p>

  <h3 class="mini">And one thing almost nothing we read mentioned</h3>
  <p>Of the coverage we hold, two specialist outlets touched it, and they disagree. Morning Glory Sciences &mdash; we give its argument on its merits rather than on its authority &mdash; the Phase 2b population was stage IIIB&ndash;IV, the Phase 3 adds node-negative disease, and &ldquo;absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit.&rdquo; Pharmacy Times makes the opposite case about the same patients: resected stage IIB or IIC melanoma &ldquo;can face risks of recurrence and melanoma-specific mortality similar to those observed in stage III disease.&rdquo; Neither reading appears in any of the general coverage we hold.</p>

  <p><strong>Which of them is right cannot be settled from anything published.</strong> It would take the Phase 3&rsquo;s own results broken down by stage, and there are none. Morning Glory says as much in the same article, and it is the more important half of its argument: <q>Because the Phase 3 hazard ratios have not been disclosed, those 157-patient figures cannot be placed alongside the 1,137-patient result. They belong to the Phase 2b population, not to this one.</q> That is not a rhetorical point. We looked: no hazard ratio, interval or p-value for this trial appears in either company release, in any of the specialist or general coverage we hold, or in the trial&rsquo;s own registry record, which as of 2 September 2026 carries <b>no posted results at all</b> and gives an estimated primary completion date of <b>26 October 2029</b> (<a href="https://clinicaltrials.gov/study/NCT05933577">NCT05933577</a>). The August announcement was a prespecified interim look &mdash; both company releases say so. The registry does not: its record has not been updated since 24 September 2025, so it carries nothing about the announcement either way.</p>

  <p><strong>One hazard ratio does appear under the trial&rsquo;s name, and it is this article&rsquo;s subject happening in public.</strong> On announcement day a melanoma oncologist posted &mdash; in a roundup we hold &mdash; <q>Exciting announcement today from Phase3 INTerpath001</q> followed by <q>RFS HR=0.51</q> and <q>DMFS HR=0.41</q>. Those are the Phase&nbsp;2b&rsquo;s figures. The outlet that logged the post said so itself, warning on the same page that the <q>Hazard ratios circulating on announcement day are these Phase 2b figures</q>. Nobody released a Phase&nbsp;3 effect size; a Phase&nbsp;3 effect size circulated anyway.</p>

  <p><strong>So putting the two sets of figures side by side would mislead, and here is exactly how.</strong> The trials do not share a population: KEYNOTE-942 enrolled stage IIIB&ndash;IV, the Phase 3 enrolled <strong>stage IIB&ndash;IV</strong>, widening it downward &mdash; adding IIB, IIC and IIIA below the earlier trial's floor of IIIB. The upper end did not move: stage IV was in both. They do not share a design: the earlier trial was open-label, this one is double-blind with the outcomes assessor masked too. They do not share a statistical standing: the Phase 2b&rsquo;s later analyses are, in its own words, <q>descriptive only</q>, against a one-sided alpha of 0.10, while the Phase 3 crossed a prespecified interim threshold. And most simply, there is nothing to put beside them: the Phase 3 has released no effect size, so quoting 0.51 next to &ldquo;met its endpoints&rdquo; is not a comparison but a substitution &mdash; the reader supplies the missing number from the smaller, older, differently-designed trial. The structure produces that effect even where every outlet attributes correctly, which is what the outlet-by-outlet check found.</p>

  <p>Those newly-included patients start at lower risk of recurrence, which leaves less room for absolute benefit, and Pharmacy Times&rsquo; counter is that their risk may be closer to stage III than the staging suggests. Whether the effect holds up across that wider range is a real open question, and exactly the kind of thing a subgroup breakdown would answer. Merck and Moderna have not published one.</p>
</section>

<section>
  <div class="section-head">
    <h2>What is established, and what is not</h2>
    <p>As of 2 September 2026. The registry was checked that day: <a href="https://clinicaltrials.gov/study/NCT05933577">NCT05933577</a> still carries no posted results.</p>
  </div>
  <div class="grid2">
    <div class="known">
      <h3>Established</h3>
      <ul>
        <li>A large, well-designed, properly blinded Phase 3 crossed its pre-registered threshold on recurrence at an interim analysis.</li>
        <li>In the earlier Phase 2b at five years, patients on the combination were recurring or dying at about <strong>half the rate</strong> (HR 0.510, 0.294–0.887) and reaching distant metastasis or dying at about <strong>two-fifths the rate</strong> (HR 0.411, 0.200–0.843).</li>
        <li>The recurrence effect <strong>held up over five years</strong> rather than fading, and its interval stopped including the no-effect line by year three and stayed clear — often a sign an effect is real, though the three-year analysis was descriptive rather than a formal test.</li>
        <li>In the Lancet report, immune-mediated adverse events were similar — 36% in the combination arm and 36% in the monotherapy arm — while grade 3 or worse treatment-related events were not: 25% versus 18%. At five years the company release puts immune-related events at 45.2% versus 44%, over a longer window than the Lancet&rsquo;s. Reading only the first pair would tell you the added therapy costs nothing. The second pair says otherwise.</li>
        <li>Most of the side effects attributed to the vaccine were mild to moderate — fatigue 59.6%, injection-site pain 59.6%, chills 51.0%. Those are KEYNOTE-942 figures, from the five-year release; the Phase&nbsp;3 announcement gave no adverse-event rates for its own 1,137 patients.</li>
      </ul>
    </div>
    <div class="unknown">
      <h3>Not established</h3>
      <ul><ul>
        <li><strong>How large the Phase 3 effect is.</strong> No hazard ratio, no interval, no percentage has been published.</li>
        <li><strong>Whether anyone lives longer, and by how much.</strong> Every survival figure in the programme is exploratory and rests on a handful of deaths. The three-year paper reports a hazard ratio of <b>0.425</b> on nine deaths, 95% CI 0.114 to 1.584; the five-year analysis reports <b>0.471</b> on fourteen, 95% CI 0.165 to 1.345. The earlier interval is the wider of the two, which is what nine deaths buys you against fourteen. Both are wide enough to hold a large benefit and a small harm at once. The question is open, not answered either way.</li>
        <li>Whether the benefit holds in stage IIB, IIC and IIIA patients, whom the earlier trial never enrolled.</li>
        <li>Durability beyond five years, in any trial.</li>
        <li>Whether the approach works in any cancer other than melanoma.</li>
        <li>What it will cost, or who will be able to get it.</li>
      </ul>
    </div>
  </div>
</section>

<section>
  <div class="section-head">
    <h2>Scoring the central claim</h2>
    <p>Our <a href="/the-rubric">published six-dimension rubric</a>, applied by hand. The arithmetic is shown so you can disagree with it.</p>
  </div>

  <div class="note">
    <span class="kicker">What this score is and is not</span>
    <p>This is <strong>not engine output.</strong> Melanoma is not one of the topics our pipeline covers, so nothing here was produced by the scoring system that runs the site. One of us applied the published rubric to one claim, by hand, and the working is below.</p>
    <p>We are also part-way through rebuilding how the engine reaches a verdict, for reasons set out in <a href="/who-pays-for-this">Who Pays for This</a>. Publishing a machine score today would imply a confidence in that machine we do not currently have.</p>
  </div>

  <div class="score" data-whu="computed">
    <p class="claim" data-whu="restates">"Intismeran autogene plus pembrolizumab improves recurrence-free survival versus pembrolizumab alone in resected stage IIB–IV melanoma."</p>

    <div class="dimrow"><span class="nm">Source quality</span><span class="bar"><span class="fill" style="width:60%;background:var(--partly)"></span></span><span class="sc">3 / 5</span></div>
    <div class="dimrow"><span class="nm">Data support</span><span class="bar"><span class="fill" style="width:20%;background:var(--nope)"></span></span><span class="sc">1 / 5</span></div>
    <div class="dimrow"><span class="nm">Reproducibility</span><span class="bar"><span class="fill" style="width:80%;background:var(--holds)"></span></span><span class="sc">4 / 5</span></div>
    <div class="dimrow"><span class="nm">Consensus</span><span class="bar"><span class="fill" style="width:80%;background:var(--holds)"></span></span><span class="sc">4 / 5</span></div>
    <div class="dimrow"><span class="nm">Recency</span><span class="bar"><span class="fill" style="width:100%;background:var(--holds)"></span></span><span class="sc">5 / 5</span></div>
    <div class="dimrow"><span class="nm">Rigor</span><span class="bar"><span class="fill" style="width:100%;background:var(--holds)"></span></span><span class="sc">5 / 5</span></div>

    <div class="composite two">
      <div class="half">
        <span class="qn">Is the effect real?</span>
        <span class="val">3.94</span>
        <span class="band">Moderate</span>
        <span class="why">(3×.25 + 4×.20 + 4×.15 + 5×.10 + 5×.10) ÷ .80</span>
      </div>
      <div class="half">
        <span class="qn">How large is it?</span>
        <span class="val">1.0</span>
        <span class="band">Weak</span>
        <span class="why">(1×.20) ÷ .20</span>
      </div>
    </div>
  </div>

  <p>Two scores, not one, because these are two questions and one number cannot answer both. <strong>Is the effect real</strong> scores 3.94; <strong>how large is it</strong> scores 1.0. The gap between them is the story. <strong>Rigor scores 5</strong> — a double-blind, placebo-controlled, 1,137-patient Phase 3 is as good as trial design gets. <strong>Data support scores 1</strong> &mdash; the rubric's anchor for 1 is <q>purely qualitative assertion with no numeric support</q>, which is what a statement that two endpoints were met, with no figure for either, is. <strong>Reproducibility scores 4</strong> because the earlier Phase 2b and the much larger Phase 3 point in the same direction on RFS and DMFS, but no Phase 3 effect size has been released, so the Phase 2b magnitude has not been reproduced. <strong>Consensus scores 4</strong> because the held sources agree on the directional Phase 3 result while the missing effect size leaves no numerical magnitude to agree on. <strong>Recency scores 5</strong> because the central evidence is the August 2026 Phase 3 announcement, supported by 2026 longer-term follow-up of the earlier trial.</p>
  <p>So the study is excellent and the evidence released about it is almost nothing. Those are different things, and until 3 September this scorecard averaged them into a single number that was wrong about both halves &mdash; understating the trial and overstating what is known about the size of what it found. Readers saw <b>3.4</b>, which was the correct total of the working printed beneath it &mdash; but that working weighted two of the six dimensions differently from the rubric, which puts the same six scores at <b>3.35</b>. That is recorded below. An outside reviewer said so and the scorecard was split. Only one of the six dimensions, data support, asks whether an effect size exists at all, so the magnitude score rests on that dimension alone; the <a href='/the-rubric'>rubric</a> says so rather than hiding it. <strong>Source quality scores 3</strong> rather than 5 for the same reason: the claim currently rests on a corporate press release, which the rubric ranks as industry analysis, not the peer-reviewed publication it will eventually become.</p>
  <p>This is what a headline cannot do. &ldquo;Landmark trial succeeds&rdquo; and &ldquo;real: 3.94, size: 1.0&rdquo; describe the same event, and only one of them tells you the numbers are still missing.</p>

  <div class="note">
    <span class="kicker">What would settle this</span>
    <p><strong>The full Phase 3 dataset</strong> — presented at a medical meeting or published in a journal, with the hazard ratio, the confidence interval and the breakdown by disease stage. That single release moves both scores, and both upward whatever the numbers say, because the rubric is measuring whether the evidence has been shown rather than whether it is good: <q>is it real</q> rises about six-tenths of a point as source quality goes to 5, and <q>how large is it</q> rises from 1.0 to 4 or 5 as soon as any effect size exists. What the numbers actually say will show up in later revisions of rigor and consensus, not in these two.</p>
    <p><strong>Overall survival, on enough events to mean something.</strong> Until it reads out on enough events, the honest sentence is that this therapy reduces recurrence and distant metastasis — and that whether it extends life is an open question rather than a settled no. The nearest scheduled comparator readout is KEYNOTE-054&rsquo;s overall-survival result, anticipated in its registry record for November 2026; KEYNOTE-716&rsquo;s is anticipated for October 2033.</p>
  </div>
</section>

<section>
  <div class="section-head">
    <h2>If you have melanoma right now</h2>
    <p>The part of this that is not academic.</p>
  </div>
  <div class="patient">
    <p><strong>This treatment is not available.</strong> It is investigational, approved by no regulator, and cannot be prescribed. In practice that means a clinical trial.</p>
    <ol>
      <li><strong>The question is trial eligibility, not treatment.</strong> The INTerpath programme is running across several cancers. Ask your oncologist whether anything is enrolling near you and whether your stage and surgical status fit.</li>
      <li><strong>Your standard-of-care decision did not change this month.</strong> Adjuvant pembrolizumab is the comparison arm in this trial precisely because it is the established treatment — and everyone in the trial received it.</li>
      <li><strong>It is manufactured per patient.</strong> The therapy is built from an individual tumour's own mutations, so it requires surgically removed tumour tissue and takes weeks to produce. That constrains who can realistically receive it even after approval.</li>
      <li><strong>If someone quotes "49%" at you, ask which trial.</strong> It is a figure from 157 patients in an open-label study, not the result announced this month — and it describes a rate of recurrence, not a share of patients cured.</li>
    </ol>
    <p class="disclaim">We assess published evidence. This is not medical advice, cannot account for your individual situation, and is no substitute for your oncologist — who can see your pathology, your stage and your history, none of which a page like this knows.</p>
  </div>
</section>

<section>
  <div class="section-head">
    <h2>Sources</h2>
    <p>Primary sources first. Every numerical trial result above traces to a company release, a peer-reviewed paper, a conference abstract or a trial registry record. Claims about what an outlet reported necessarily trace to the named coverage itself. The pre-publication checks test whether bound spans match held documents, whether figures appear in held documents and whether bound sources are represented in the reader-facing source set; they do not independently classify a document as news or primary.</p>
  </div>
  <div class="sources">
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://www.merck.com/news/merck-and-moderna-announce-phase-3-interpath-001-trial-of-intismeran-autogene-plus-keytruda-met-endpoints-of-recurrence-free-survival-rfs-and-distant-metastasis-free-survival-dmfs-in-patient/">Merck &amp; Moderna — Phase 3 INTerpath-001 met RFS and DMFS endpoints</a>
        <span class="note">19 August 2026. Source of the trial design, enrolment, blinding and randomisation. Contains no efficacy numbers, which is the finding.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://www.merck.com/news/moderna-and-merck-present-5-year-data-for-intismeran-autogene-in-combination-with-keytruda-pembrolizumab-in-patients-with-high-risk-stage-iii-iv-melanoma-following-complete-resection-at-the-20/">Merck &amp; Moderna — five-year KEYNOTE-942 data, ASCO 2026</a>
        <span class="note">1 June 2026. Source of HR 0.510 (0.294–0.887), HR 0.411 (0.200–0.843), the exploratory OS figure HR 0.471 (0.165–1.345) reported as "n=14", and the adverse-event rates.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://pubmed.ncbi.nlm.nih.gov/38246194/">KEYNOTE-942: a randomised, phase 2b study — <em>The Lancet</em>, 2024</a>
        <span class="note">The peer-reviewed publication. Source of HR 0.561 (0.309–1.017) with <strong>two-sided p = 0.053</strong>, the stage IIIB–IV enrolment, the 107/50 arm sizes, the open-label design, and grade 3+ treatment-related events at 25% versus 18%.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://ascopubs.org/doi/10.1200/JCO-26-00835">Five-year results — <em>Journal of Clinical Oncology</em>, 1 June 2026</a>
        <span class="note">The peer-reviewed five-year analysis, published the day it was presented. Median follow-up 60.3 months, data cutoff 15 December 2025, and the statement that the five-year analyses were descriptive.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-an-investigational-individualized-neoantigen-therapy-in-combination-with-keytruda-pembrolizumab-demonstrated-superior-recurrence-free-survival-in/">Merck &amp; Moderna — first detailed KEYNOTE-942 results</a>
        <span class="note">16 April 2023. The source of the one-sided p = 0.0266. It is the company's figure, and the peer-reviewed Lancet paper prints the two-sided 0.053 instead. We have not opened the conference abstract of the same analysis, so this page does not say the one-sided value appears nowhere but here.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag sec">Trade</span>
      <span>
        <a href="https://ascopost.com/news/august-2026/interpath-001-trial-of-mrna-based-individualized-neoantigen-therapy-meets-primary-and-key-secondary-endpoints-in-patients-with-high-risk-resected-melanoma/">The ASCO Post — INTerpath-001 meets primary and key secondary endpoints</a>
        <a href="https://www.morningglorysciences.com/en/intismeran-interpath-001-phase3-melanoma-2026-en/">Morning Glory Sciences — INTerpath-001</a>
        <span class="note">Specialist coverage. Source of the quoted argument that absolute recurrence risk is lower in the stage IIB and IIC patients the Phase 3 adds.</span>
        <a href="https://www.pharmacytimes.com/view/phase-3-trial-marks-first-success-for-personalized-mrna-cancer-therapy-in-resected-melanoma">Pharmacy Times — Phase 3 trial marks first success</a>
        <span class="note">Specialist coverage. Source of the quoted argument that resected stage IIB and IIC melanoma can carry recurrence and mortality risks similar to stage III.</span>
        <a href="https://mlq.ai/news/moderna-mercks-personalized-melanoma-therapy-meets-two-phase-3-endpoints/">MLQ News — Moderna and Merck&rsquo;s personalized melanoma therapy meets two Phase&nbsp;3 endpoints</a>
        <span class="note">Coverage. The outlet that enumerated what the announcement did not contain, quoted on this page.</span>
        <a href="https://www.dermatologytimes.com/view/personalized-mrna-based-melanoma-vaccine-meets-primary-endpoints-in-landmark-phase-3-trial">Dermatology Times — Personalized mRNA-Based Melanoma Vaccine Meets Primary Endpoints</a>
        <a href="https://practicaldermatology.com/news/intismeran-plus-pembrolizumab-meets-dual-phase-3-melanoma-endpoints/2488176/">Practical Dermatology — Intismeran Plus Pembrolizumab Meets Dual Phase&nbsp;3 Melanoma Endpoints</a>
        <a href="https://www.onclive.com/view/intismeran-autogene-plus-pembrolizumab-meets-rfs-dmfs-end-points-in-resected-melanoma">OncLive — Intismeran Autogene Plus Pembrolizumab Meets RFS, DMFS End Points in Resected Melanoma</a>
        <span class="note">Three of the five outlets that named KEYNOTE-942 when attributing the 49% figure. Held so that what this page says about them can be checked against them.</span>
        <a href="https://ascopost.com/news/june-2026/vaccine-plus-pembrolizumab-reduces-risk-of-recurrence-in-high-risk-resected-melanoma/">The ASCO Post, June 2026 — Vaccine Plus Pembrolizumab Reduces Risk of Recurrence in High-Risk Resected Melanoma</a>
        <span class="note">The five-year landmark rates as this page first carried them, before they were moved to the ASCO abstract that reports them.</span>
        <a href="https://kolpulse.com/kol-pulse-trial-profile-interpath001">KOL Pulse — INTerpath-001 trial profile</a>
        <span class="note">The trial profile that logged the announcement-day posts, including the one this page quotes and the one that gave the figure as phase&nbsp;2 without naming the trial.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://ascopubs.org/doi/10.1200/OA-25-00008">Three-Year Update of a Randomized Phase IIb Study of the Individualized Neoantigen Therapy Intismeran Autogene (mRNA-4157, V940) Plus Pembrolizumab Versus Pembrolizumab in Resected Melanoma — <em>JCO Oncology Advances</em>, 2026</a>
        <span class="note">DOI 10.1200/OA-25-00008. The Three-Year Update, published in JCO Oncology Advances on 12&nbsp;February 2026. Its own words on what these analyses are: <q>These subsequent analyses are not intended for formal hypothesis testing (ie, are descriptive only)</q>. It reports the recurrence hazard ratio with an <b>80% confidence interval</b> of 0.351&ndash;0.743 in the text, and the 95% interval 0.288&ndash;0.906 in its results table; the 95% interval is the one quoted above, so that it can be read beside the others on this page.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.9500">KEYNOTE-942 five-year update — ASCO 2026 meeting abstract 9500</a>
        <span class="note">Conference abstract. Source of the five-year landmark RFS and OS rates and their confidence intervals; the abstract states that no alpha was assigned to this analysis.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://meetings.asco.org/abstracts-presentations/230175">KEYNOTE-942 three-year update — ASCO 2024 abstract LBA9512</a>
        <span class="note">Conference abstract and presentation record. Source of the protocol statement that the trial was designed with a one-sided alpha of 0.10.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://clinicaltrials.gov/study/NCT05933577">INTerpath-001 — ClinicalTrials.gov, NCT05933577</a>
        <span class="note">Registry record. Source of the Phase 3 population, placebo description and investigator-assessed RFS and DMFS endpoints. The record was last updated 24 September 2025 and carries no posted results.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://clinicaltrials.gov/study/NCT02362594">KEYNOTE-054 — ClinicalTrials.gov, NCT02362594</a>
        <span class="note">Registry record. Overall survival is NOT_POSTED, with an anticipated posting date of November 2026.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://clinicaltrials.gov/study/NCT03553836">KEYNOTE-716 — ClinicalTrials.gov, NCT03553836</a>
        <span class="note">Registry record. Overall survival is NOT_POSTED, with an anticipated posting date of October 2033.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://clinicaltrials.gov/study/NCT02388906">CheckMate 238 — ClinicalTrials.gov, NCT02388906</a>
        <span class="note">Registry record. Source of the nivolumab-versus-ipilimumab active-comparator arms.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC5648545/">Eggermont et al. — EORTC 18071 overall survival, <em>N Engl J Med</em> 2016</a>
        <span class="note">DOI 10.1056/NEJMoa1611299; PMID 27717298; PMCID PMC5648545. Source of the adjuvant ipilimumab-versus-placebo five-year overall-survival result and immune-related deaths. A 2018 erratum covering thirteen <em>NEJM</em> articles at once (<a href="https://pubmed.ncbi.nlm.nih.gov/31442371/"><em>N Engl J Med</em> 2018;379:2185</a>) applies to this paper. We have not been able to read it: NEJM returns 403, Europe PMC records the notice as neither open access nor in its archive, and neither PubMed nor Crossref carries an abstract for it; so we do not know whether it touches a figure on this page. Every figure we quote appears in the current PubMed record of this paper, which post-dates the erratum.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4877414/">Greenland et al. — Statistical tests, P values, confidence intervals, and power</a>
        <span class="note"><em>Eur J Epidemiol</em> 2016;31:337&ndash;350. Methodological source for the cautions against significance dichotomies and common p-value misreadings.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC478551/">Spruance, Reid, Grace &amp; Samore — Hazard Ratio in Clinical Trials</a>
        <span class="note"><em>Antimicrob Agents Chemother</em> 2004;48(8):2787&ndash;2792. PMID 15273082; PMCID PMC478551. Source for the proportional-hazards assumption, the pairwise-probability interpretation and the race analogy.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://www.ncbi.nlm.nih.gov/books/NBK560604/">Survival Analysis — StatPearls, NCBI Bookshelf</a>
        <span class="note">Source for the direction a hazard ratio moves in: risk rises as the value goes above 1 and falls as it goes below.</span>
      </span>
    </div>
    <div class="src">
      <span class="tag">Primary</span>
      <span>
        <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC3227332/">Singh &amp; Mukhopadhyay — Survival analysis in clinical trials: basics and must-know areas</a>
        <span class="note"><em>Perspect Clin Res</em> 2011;2(4):145&ndash;148. Source for what a hazard ratio of 1 means, and for the caution that a hazard ratio is not a proportion of patients benefited.</span>
      </span>
    </div>
  </div>
</section>

<footer id="updates">


  <p><strong>Updated 9 September 2026.</strong> An outside reviewer read this
  page against the packet we send out, and found six sentences that were wrong.
  Four were errors of fact, one was a comparison two figures could not bear, and
  one described our own checks as doing something they do not do. All six are
  corrected below. The reviewer also made two errors of their own, and those are
  recorded here too.</p>

  <p><strong>The registry does not say what we said it says.</strong> We wrote
  that the August announcement was a prespecified interim look <q>and the
  register says so</q>. It does not. The word <em>interim</em> appears nowhere
  in the NCT05933577 record, and that record has not been updated since
  <b>24 September 2025</b> &mdash; eleven months before the announcement it was
  being cited about. The interim fact is real and comes from the Merck and
  Moderna releases, which both use the phrase. The sentence now says so. The
  wider problem was ours: we had been using the registry's silence as evidence
  that no Phase 3 number exists, and a file nobody has touched since last
  September is a stale record rather than a live absence. Where the registry
  still appears as a negative, its last-update date now appears with it.</p>

  <p><strong>An interval moved the wrong way.</strong> We wrote that at five
  years <q>the upper bound had come in from 0.906, the lower bound had drifted
  out from 0.288</q>. Both bounds came in. The lower moved from 0.288 to 0.294,
  which is inward on any reading &mdash; closer to 1.0, closer to the point
  estimate, closer to the other bound. The interval narrowed slightly at both
  ends and the page now says that.</p>

  <p><strong>Two adverse-event figures that do not belong beside each
  other.</strong> We set 45.2% against 44% for any-grade immune-related events,
  then 25% against 18% for grade 3 or worse, in a single sentence built as one
  contrast. They are different categories, from different documents, at
  different lengths of follow-up: the first pair is the five-year company
  release, the second is the <em>Lancet</em>'s two-year cut. The <em>Lancet</em>
  reports both on the same patients at the same cut &mdash; immune-mediated
  events 36% in each arm, grade 3 or worse treatment-related 25% against 18%
  &mdash; and that is the comparison now on the page, with the five-year figures
  given separately and their window named. Setting two correctly sourced numbers
  side by side where they cannot bear the comparison is the subject of this
  article. We did it in our own summary.</p>

  <p><strong>A sentence that outlived the scorecard it described.</strong> When
  we split the score in two on 3 September we left standing a line saying the
  full dataset would move <q>the score</q> by roughly a full point, <q>in
  whichever direction the numbers point</q>. Neither half survives the split.
  Source quality going to 5 lifts <em>is the effect real</em> by about
  six-tenths of a point; data support coming off 1 lifts <em>how large is it</em>
  from 1.0 to 4 or 5. And both move upward whatever the numbers say, because the
  rubric measures whether the evidence has been shown, not whether it is
  flattering. The sentence now says that, which is the more interesting fact
  about our own rubric and one we had obscured.</p>

  <p><strong>The counterexample we had excluded.</strong> Our sentence about
  adjuvant PD-1 inhibitors never reporting a survival benefit against placebo
  was correct and still stands. The paragraph around it was not doing what we
  thought. It opened by saying adjuvant melanoma trials have a history of
  recurrence benefits that <q>sometimes never did</q> translate into survival,
  listed three negatives, and closed by noting that this page held no document
  about a CTLA-4 inhibitor &mdash; true, and doing work a true sentence should
  not do. There is such a trial. In EORTC 18071, adjuvant ipilimumab against
  placebo in resected stage III melanoma reported overall survival as a
  <em>prespecified</em> secondary endpoint: <b>65.4% against 54.4%</b> at five
  years, HR 0.72 (95.1% CI 0.58&ndash;0.88), p=0.001. It is not standard care
  because the dose was 10 mg/kg and five patients died of immune-related events,
  not because it failed on survival. The paper is now held and cited, and the
  page says that the translation from recurrence to survival is possible in this
  disease and has not yet been shown for a PD-1 inhibitor. Listing three
  negatives and omitting the one positive left a reader with something we did
  not check and could not have defended.</p>

  <p><strong>What our checks actually test.</strong> We told readers that every
  number on this page traced to a primary document and none to a news report,
  and that a check refuses publication otherwise. The check does not classify
  documents that way. It tests whether bound spans match the documents we hold,
  whether figures appear in those documents, and whether bound sources reach the
  reader in the source list. It has no opinion on what counts as news. The
  sentence now describes what the checks do, and the source enumeration now
  includes conference abstracts, which is what the five-year rates actually rest
  on. This is the second time on this page that a careful check has been
  described by careless prose. The entry below says that is the failure worth
  keeping in view, and it did not take the first time.</p>

  <p><strong>What the blinding does not cover.</strong> We wrote that an
  assessor who does not know the arm cannot favour it, and printed, a few
  hundred words later, that the therapy caused injection-site pain in 59.6% of
  patients and chills in 51.0%. The Phase 3 comparator is a saline injection.
  Where a therapy is that much more reactogenic than its placebo, patients and
  their doctors can sometimes infer the arm &mdash; and the primary endpoint is
  investigator-assessed, as is the key secondary. Both halves were on the page
  and we had never put them together. The caveat is now in the blinding
  section.</p>

  <p><strong>The reviewer was wrong twice, and this log should say so.</strong>
  Asked to check our claim about overall survival in KEYNOTE-054 and
  KEYNOTE-716, the reviewer confirmed an earlier version of it &mdash; that both
  trials had posted a survival result carrying no statistical analysis. They
  have posted nothing. Both registry records mark the measure
  <b>NOT_POSTED</b>, with anticipated posting dates of November 2026 and October
  2033; the reviewer had read one field and not the one that mattered. We had
  already corrected this on 4 September, and accepting the confirmation would
  have put the error back. The reviewer also proposed attaching the three-year
  paper's 80% interval, 0.351&ndash;0.743, to the 2023 readout. It belongs to
  the three-year hazard ratio of 0.510, and no 80% interval for the 2023 result
  exists in any document we hold. Neither error reached the page. We record them
  because an outside review is not a one-way audit, and a log that only ever
  reports the reviewer catching us describes something that did not
  happen.</p>

  <p><strong>Also changed.</strong> The nearest scheduled answer to the survival
  question is now on the page: KEYNOTE-054's overall-survival result is
  anticipated in its registry record for November 2026, and KEYNOTE-716's for
  October 2033. The hazard-ratio explainer now names the assumption underneath a
  single hazard ratio &mdash; that the ratio held steady across the whole
  follow-up, which the three-year paper's own methods assume in fitting a Cox
  proportional-hazards model &mdash; and adds the one patient-level reading a
  hazard ratio does support, roughly a 66% chance that a treated patient goes
  longer without recurrence, against 50% if the therapy did nothing. The
  confidence-interval chart now says that its amber and green split is a
  convention rather than a verdict, and that this trial registered a one-sided
  alpha of 0.10 rather than the 95% convention the chart draws. The
  <q>Not established</q> list now names stage IIIA alongside IIB and IIC, since
  the Phase 3 added all three below the earlier trial's floor. The two figures in
  the summary strip that belong to the Phase 2b now say so.
   The three scores we had never explained &mdash;
  reproducibility, consensus and recency, together more than half of <em>is the
  effect real</em> &mdash; now carry their reasoning.
   And the three-year survival interval is now given at 95%,
  0.114&ndash;1.584, so that it can be read against the five-year
  0.165&ndash;1.345 rather than beside it at a different width; at equal width
  the earlier interval is the wider of the two, which is what nine deaths buys
  against fourteen.</p>

  <p><strong>We overstated our own error, and readers saw that.</strong> Since
  4 September this page has told readers that the composite it printed was
  <q>out by 0.05 against its own working</q>. It was not. The working printed
  beside <b>3.4</b> came to <b>3.40</b> exactly, and 3.4 is the number it
  produces; no reader was ever shown a figure that disagreed with the arithmetic
  underneath it, and no rounding was involved. What differed was the working
  itself: reproducibility and recency were shown at <b>15%</b> each where the
  rubric gives them <b>20%</b> and <b>10%</b>. That is a real error, it is the
  one that put the total 0.05 high, and it is recorded in the entry below &mdash;
  but it is not the error we confessed to. A page that prints its arithmetic and
  totals it correctly, from weights that are not the published ones, is not a
  page whose display disagrees with its own working. The distinction matters
  because the 2 September entry below already records a correction notice that
  was worse than the error it corrected, and named that as the failure worth
  keeping in view. This is the same failure, in the entry that was supposed to
  have learned from it. The commit history settles it: from 26 August the page
  printed <q>(3&times;.25)+(1&times;.20)+(4&times;.15)+(4&times;.15)+(5&times;.15)+(5&times;.10)</q>,
  and on 3 September the commit that published the rubric corrected the same
  working to the rubric's weights in one change.</p>

  <p><strong>The page now says less about one outlet than we promised it
  would.</strong> The 4 September notice said the Morning Glory Sciences clause
  had been replaced with <q>a specialist outlet, and we give its argument on its
  merits</q>. It has not been, and it will not be. Three characterisations of
  that outlet have now been attempted &mdash; the English edition of a non-English
  site, an outlet no other publication cites, and a specialist outlet &mdash; and
  the first two were withdrawn as unsupportable. The third has no better support
  than they did. What the record actually holds on the outlet's standing is one
  citation: reference 12 of a letter in the <em>Irish Journal of Medical Science</em>,
  which the publisher deposited to Crossref and which we have now read there, in a
  letter whose own text we have never read. One citation in one reference list
  establishes that the outlet is cited. It establishes nothing about whether it is
  specialist, authoritative, or anything else. So the sentence now carries no
  characterisation at all. It names the outlet, gives its
  argument, and tells you to weigh the argument. Saying less is what we can
  actually support, and a fourth adjective would be the same mistake with a
  different word.</p>

  <p><strong>And what the review did not catch.</strong> Publishing the
  corrections above meant binding every sentence on this page to the words it
  rests on, which is the check our own account of ourselves depends on and which
  had fallen behind. Doing it found three more things. We had credited
  <em>KOL&nbsp;Pulse</em> with giving the 49% figure as a phase&nbsp;2 result
  without naming the trial; the outlet names KEYNOTE-942 throughout and
  attributes the circulating hazard ratios to it, and the wording we praised
  belongs to a post it logged, not to the outlet. That sentence now says whose
  it is. The <em>New England Journal</em> paper behind the ipilimumab
  counterexample was cited here before it was held: the entry above says the
  paper <q>is now held and cited</q>, and on the day that was drafted the
  library contained nothing. It has been obtained and the sentence is now true.
  And nine documents this page rests on were missing from the list of sources a
  reader sees &mdash; including the coverage the consensus score rests on, which
  a reader cannot check against a list that does not name it. All nine are
  listed. Three small figures went the other way: a word we could not support
  from a document, a comparison we can now state as two numbers rather than one,
  and an arithmetic step of our own we had printed as though a document reported
  it.</p>

  <p><strong>Updated 4 September 2026.</strong> Two days of changes, and an
  admission about this log before them. Most of what follows was written at the
  time and filed under the headings for 28 August and 2 September, which dated
  our own corrections to before we made them. The paragraphs are unchanged; only
  the date above them is. Nothing was removed to make room.</p>

  <p><strong>The composite readers saw was not weighted the way the rubric weights
  it.</strong> The published page scored this assessment <b>3.4</b>, beside a working
  that gave reproducibility and recency <b>15%</b> each. The rubric gives them
  <b>20%</b> and <b>10%</b>. So the printed number was the correct total of the
  arithmetic printed underneath it: no reader was ever shown a figure that disagreed
  with the working beside it, and no rounding was involved, because that working came
  to 3.40 exactly. What was wrong was the working. Two dimensions carried weights that
  were not the rubric's, and the two errors did not cancel &mdash; they left the total
  <b>0.05</b> high. On 3 September the scorecard was marked as text the page works out
  for itself, which obliges it to show its arithmetic and to come to the number it
  prints. The rubric was published the same day and the weights were corrected to match
  it, at which point the same six scores came to <b>3.35</b>. The composite was
  abolished shortly afterwards, for a different reason. The correction is recorded here
  because it happened to a figure readers could see.</p>

  <p><strong>The scorecard was one number and is now two.</strong> An outside
  reviewer found that a single composite breaches this publication&rsquo;s own rule
  against expressing confidence in a result&rsquo;s <em>direction</em> and confidence in
  its <em>size</em> in one verdict. The corrected composite read <span data-whu="computed">3.35,
  from 3 / 5 &middot; 1 / 5 &middot; 4 / 5 &middot; 4 / 5 &middot; 5 / 5 &middot; 5 / 5 and
  (3&times;.25 + 1&times;.20 + 4&times;.20 + 4&times;.15 + 5&times;.10 + 5&times;.10)</span>
  &mdash; a number below what the trial design deserves and above what the disclosure
  supports. It is now 3.94 for whether the effect is real and 1.0 for how large it is.
  The <a href="/the-rubric">rubric</a> carries the split and says plainly that only one
  of the six dimensions measures magnitude at all.</p>

  <p><strong>We had misquoted our own rubric.</strong> We had scored data support 1
  and said the rubric&rsquo;s anchor for 1 was &ldquo;no data cited,&rdquo; which sat
  badly with a directional result having been cited. On 3&nbsp;September the rubric was
  published and the anchor turned out to read <q>purely qualitative assertion with no
  numeric support</q>. Under what it actually says, a score of 1 is right and needs no
  explaining away.</p>

  <p><strong>The five-year rates moved to the primary document.</strong> They had been
  credited to <em>The ASCO Post</em>, because the ASCO abstract that carries them
  returned an error to every automated attempt to fetch it. It was obtained by hand on
  3&nbsp;September and those figures now rest on it. The same abstract states in its own
  words that <q>No alpha was assigned to this analysis</q>, which is the plainest
  available support for a point this piece already made from the three-year paper.</p>

  <p><strong>And the third figure came back after all.</strong> On 2 September we said a &ldquo;five-year topline of 20 January 2026&rdquo; reporting a one-sided nominal p = 0.0075 would stay out until somebody produced it. On 3&nbsp;September our own page gate produced it. Moderna and Merck&rsquo;s announcement of that date is now held, and it reports the five-year recurrence result as <q>reducing the risk of recurrence or death by 49% (HR=0.510; [95% CI, 0.294-0.887]; one-sided nominal p=0.0075) compared to KEYTRUDA alone</q>. The figure was real. Our failure to find it was never evidence that it was not. Note the word the companies chose &mdash; <b>nominal</b> &mdash; which is what a p-value is called when no alpha has been assigned to the analysis that produced it, and the ASCO 2026 abstract for that same five-year readout, number 9500, says exactly that: <q>No alpha was assigned to this analysis</q>. So there are now three p-values on this page for one programme: 0.0266 and 0.053 are the 2023 primary analysis read one-sided and two-sided, and 0.0075 is a later analysis with more follow-up that was never a formal test at all.</p>

  <p><strong>What the registry actually says about overall survival.</strong> We
  had written that KEYNOTE-054 and KEYNOTE-716 <q>each posted an overall-survival
  result that carries no statistical analysis at all</q>. They have posted
  nothing. Both records mark the measure <b>NOT_POSTED</b> with a posting date
  still ahead of it &mdash; November 2026 for KEYNOTE-054, October 2033 for
  KEYNOTE-716. A result withheld and a result not yet due are different things,
  and the first reads as evasion where the second is a schedule. The sentence now
  says which one this is.</p>

  <p><strong>CheckMate 238 was never evidence for what we used it for.</strong>
  We had counted it among three trials that had not shown a survival benefit
  against placebo, and explained in the next breath that it has no placebo arm.
  Counting a trial that cannot answer the question makes a two-trial observation
  look like a three-trial one. The paragraph now sets it aside explicitly, and
  names its arms &mdash; every patient in it received an active treatment.</p>

  <p><strong>Statistical language, again.</strong> Four fixes, all of them the
  kind this piece exists to catch in other people. Our p-value gloss said that if
  the drug were useless you would see a result this good about 5% of the time,
  which quietly drops every other assumption the calculation rests on; the
  assumptions are now part of the sentence. We had defined distant
  metastasis-free survival as time until the cancer spreads, omitting death,
  which is half the endpoint. Twice we described patients as
  <q>recurring</q> where the measure counts recurrence or death. And we said the
  Phase 3 is blinded against the assessment bias the earlier trial carried, when
  what blinding addresses is the direction that bias can run in &mdash; both
  trials keep investigator assessment.</p>

  <p><strong>What we said about Morning Glory Sciences, and what we did not
  do about it.</strong> We had described it as the English edition of a
  non-English industry site. We could not stand that up, and we replaced it with
  a narrower claim: that it is an outlet we can find no other publication citing.
  That was wrong too. A 2026 letter in the <em>Irish Journal of Medical Science</em>
  cites it in its reference list, and on 4 September we published a correction
  saying so &mdash; a correction which stated that the clause was gone and that the
  sentence now read differently. <strong>The clause was not gone.</strong> It was
  on the page when that correction was published, and it stayed there until
  9 September. The replacement wording the correction named has never been on this
  page at all. This paragraph, in the version first drafted for this entry,
  repeated the falsified clause as though it were the correction: it was written
  on 8 September by the outside reviewer, from a diff of two page states, without
  reading the corrections file that said the claim was false. The clause is now
  removed, and so is every other characterisation of the outlet.</p>

  <p><strong>And one hazard ratio did circulate under the Phase 3&rsquo;s
  name.</strong> This article&rsquo;s subject happened in public on announcement
  day, and the page now shows it. A melanoma oncologist posted, in a roundup we
  hold, <q>Exciting announcement today from Phase3 INTerpath001</q> followed by
  RFS HR=0.51 and DMFS HR=0.41. Those are the Phase 2b&rsquo;s figures. The
  outlet that logged the post said so itself on the same page. Nobody released a
  Phase 3 effect size; a Phase 3 effect size circulated anyway.</p>

  <p><strong>Updated 2 September 2026.</strong> On 1 September we removed three
  figures from this page, saying they appeared in no document we held. That was
  true of what we held. It was not true of the literature, and for two of the
  three it was the wrong conclusion to draw. Both are restored. This entry
  replaces the one that stood here for part of yesterday, and the earlier entry
  is superseded rather than deleted &mdash; what it said is quoted below.</p>

  <p><strong>The five-year rates were real, and they are back.</strong> We had
  printed, at five years, 68.8% of combination patients recurrence-free against
  49.1%, and 92.2% alive against 71.3% on an interval of 35.4&ndash;89.6. A
  check we built that day asked whether every figure on the page appears in some
  document this issue holds, and these did not, so we took them off. What we
  held was the full <em>Journal of Clinical Oncology</em> paper, and that paper
  reports its landmark rates only to <b>48 months</b>. The five-year rates were
  reported from the same analysis in <em>The ASCO Post</em>, which we did not
  hold until today: <q>At 5 years, the recurrence-free survival rate was 68.8%
  (95% confidence interval [CI] = 56.3%&ndash;78.3%) in the combination arm and
  49.1% (95% CI = 33.3%&ndash;63.0%) in the monotherapy arm</q>, and
  <q>5-year rates of 92.2% (95% CI = 84.2%&ndash;96.3%) in the combination arm
  and 71.3% (95% CI = 35.4%&ndash;89.6%) in the pembrolizumab alone arm</q>.</p>

  <p><strong>What actually went wrong, then.</strong> Not the figures: the
  intervals. The page gave 68.8% and 71.3% without the confidence intervals
  that show what they are worth, and 35.4&ndash;89.6 is the whole point of the
  survival number &mdash; on seven deaths in fifty patients it runs from a third
  of that arm alive to nine in ten. The intervals are on the page now. The
  attribution was wrong too: these were credited to a paper that does not print
  them, and they are now credited to the document that does.</p>

  <p><strong>And the correction notice was worse than the error.</strong> The
  entry that stood here yesterday said the figures &ldquo;came from no
  document&rdquo; and that one &ldquo;exists nowhere&rdquo;. The check itself
  had been careful &mdash; it reports that a figure is in nothing we hold, and
  says in its own output that a miss is not a falsehood &mdash; and the sentence
  written around it was not. Accusing ourselves of inventing figures we had not
  invented is a worse failure than the missing intervals, and it is the one
  worth keeping in view: a check that states its limits precisely is no
  protection if the prose reporting it overstates.</p>

  <p><strong>The third figure has not come back.</strong> We also removed a &ldquo;five-year topline of 20 January 2026&rdquo; reporting a one-sided nominal p&nbsp;=&nbsp;0.0075, because we could not find the document, and we said it would stay out until somebody produced it.</p>

  <p><strong>What the source advocate and the counterexample hunt changed.</strong>
  Two adversarial checks ran on this issue for the first time. We had said the
  recurrence interval <em>cleared</em> the no-effect line at three years; the
  three-year paper says its analyses were <q>not intended for formal hypothesis
  testing (ie, are descriptive only)</q>, so the interval stopped including 1.0
  rather than crossing a threshold anyone tested. Our note on that paper said
  the journal blocked us and we had not read it &mdash; we hold it in full, and
  the note is rewritten. Its title was truncated, dropping the drug synonyms a
  reader needs to find it. The &ldquo;n=14&rdquo; label, which is the companies'
  own, reads as fourteen patients and is now glossed as fourteen deaths, seven
  in each arm. And a sentence about adjuvant trials opened wider than the claim
  it was making, which was only ever about PD-1 inhibitors against placebo.</p>

  <p><strong>What the trial's own threshold was.</strong> The section on
  one-sided and two-sided p-values left a reader to supply 0.05 as the line
  being missed. The trial prespecified a one-sided alpha of 0.10 &mdash; stated
  in the three-year paper and again in the ASCO 2024 presentation &mdash; so
  0.0266 was inside its own threshold by a wide margin, and 0.053 is a near miss
  only against a line this trial never used. The point of the section is
  unchanged and now rests on what the trial registered.</p>

  <p><strong>Two outlets disagree about the patients this trial newly
  includes</strong> &mdash; whether their recurrence risk is low enough that the
  same hazard ratio delivers less absolute benefit, or close enough to stage III
  that it does not. We had asked which of them is right as though the answer
  were available. It is not: no hazard ratio, interval or p-value for the
  Phase&nbsp;3 appears in either company release, in any coverage we hold, or in
  the trial's registry record, which carries no posted results and gives an
  estimated primary completion date of 26 October 2029. The section now says so,
  and says why placing the earlier trial's figures beside this result would
  mislead.</p>

  <p><strong>Updated 28 August 2026.</strong> The version of this assessment that was
  readable here until today differed from this one in more than forty places, and the
  log below it covered only an earlier round of edits. This entry is the rest of it.</p>

  <p><strong>What the coverage did.</strong> An earlier version characterised how most
  coverage had handled the earlier trial&rsquo;s figures. Checked outlet by outlet, that
  characterisation did not hold: most specialist outlets attributed the figures
  correctly, and the section now says so and leads with it. What is left is subtler and
  harder to fix &mdash; correctly attributed figures still doing work they cannot do,
  three paragraphs under a headline about a different trial.</p>

  <p><strong>Statistical language.</strong> Four corrections. We had called a 62%
  figure a &ldquo;risk reduction&rdquo; where it is a reduction in hazard. We had
  described the earlier trial&rsquo;s patients as &ldquo;unblinded,&rdquo; which
  suggests a blind that broke rather than a trial that was open-label from the start.
  We had said the Phase&nbsp;3 was blinded against &ldquo;exactly&rdquo; a bias that
  its investigator-assessed endpoint still partly carries. And we had given the survival
  rates without their intervals, which is what shows whether an observed gap is one
  the data can confirm. Those rates were themselves wrong, and were corrected on
  1&nbsp;September; see the entry below.</p>

  <p><strong>What the evidence supports.</strong> We had written that the honest
  sentence is that this therapy &ldquo;delays recurrence, not that it extends
  life.&rdquo; It reduces recurrence and distant metastasis; whether it extends life
  is an open question rather than a settled no, and the piece now says so.
  We had also presented the adverse-event figures in a way that read as a single
  comparison; any-grade immune-related events were similar and grade&nbsp;3 or worse
  were not, and both are now shown.</p>

  <p><strong>And today.</strong> An outside reviewer read the full
  assessment against our published standards and returned one finding: we gave the
  two-sided p-value from the <em>Lancet</em> publication without saying in the same
  sentence that the trial&rsquo;s prespecified analysis was one-sided. That sentence
  now says so. Reading our own fact-check output more closely than we had before
  turned up four more. We had written that three outlets each listed what the
  announcement was missing &mdash; hazard ratios, absolute event rates, p-values
  &mdash; when only one of them enumerated those metrics; the sentence now
  attributes to each outlet only what it actually said, and drops two we could not
  stand up. We had dated two outlets&rsquo; coverage to specific days we could not
  confirm from the articles themselves, and a source note to a day its article does
  not carry; those dates are gone and the attributions stand. We had said the
  trial&rsquo;s most common side effects were mild to moderate, where the
  company&rsquo;s release describes the events <em>attributed to the vaccine</em>
  specifically &mdash; the sentence now says that, and the three percentages were
  re-read off the release and are unchanged. And we had told a reader that the only
  route to this treatment is a clinical trial. We could not establish that expanded
  access is categorically unavailable, so the sentence no longer claims it is.</p>

  <p><strong>Updated 27 August 2026.</strong> After an outside review and two passes
  through our own pre-publication checks, we changed the following. Two sentences
  described a hazard ratio as if it counted lives, which the explainer in this piece
  says you cannot do; both are rewritten. We had called the announcement one that
  "reports no Phase 3 results" — it reports that both endpoints were met, and what it
  withholds is the numbers, so the piece now says that. We had written that the
  companies report the survival analysis "only as n=14" and do not say fourteen of
  what; they report the count alongside a hazard ratio and interval, and seven deaths
  occurred in each arm. We had skipped the three-year readout, which is where the
  recurrence interval actually cleared the no-effect line. We had described the Phase
  3's investigator-assessed endpoint as carrying the same weakness as the open-label
  trial; blinding substantially addresses it, and regulators have approved adjuvant
  melanoma therapies on investigator-assessed recurrence before. We had given the 59%
  figure without saying it describes distant metastasis or death. We had said no
  adjuvant PD-1 trial has shown a survival benefit, which is too absolute. What we
  can show is narrower: neither placebo-controlled trial whose registry record we
  hold has posted an overall-survival result at all. We had credited too few of the
  outlets that got this right, and named one where several deserved it. A first pass through our own checks of this page, which until now had only been run against the email summarising it, found eight sentences where the summary at the top said something the body below corrects: it called the trial&rsquo;s two endpoints co-primary when one is primary and one key secondary; it repeated an accusation against the coverage that the body itself retracts; it said the Phase&nbsp;3 was blinded against &ldquo;exactly&rdquo; a bias its own investigator-assessed endpoint still carries; it credited the five-year data with clearing the no-effect line when the body says year three; and it twice described a study that has released no effect size as having published nothing. All are corrected to match what the piece already said further down. The gap between the first detailed
  results and the peer-reviewed paper was nine months, not five &mdash; 16 April 2023 to
  18 January 2024, the dates those two documents carry. An earlier version of this
  entry said four and a half months, which is neither interval and rested on a
  December 2022 release this page does not hold. And we had
  called the earlier trial&rsquo;s patients &ldquo;unblinded,&rdquo; which suggests a blind that was
  broken; the trial was open-label from the start, and the piece now says so.</p>
  <p><strong>Corrections.</strong> If you think something here is wrong, write to <a href="mailto:corrections@whatholdsup.org">corrections@whatholdsup.org</a> with the specific claim and what is wrong with it. Acknowledged within 48 hours, resolved or explained within 10 business days.</p>
  <p><strong>Disclosure.</strong> What Holds Up is published by CivicScale, which sells healthcare software and has no outside investment. Neither Merck nor Moderna, nor any customer, saw this before publication. The full funding position is in <a href="/who-pays-for-this">Who Pays for This</a>.</p>
  <p><strong>Checking.</strong> Every numerical trial result above traces to a company release, a peer-reviewed paper, a conference abstract or a trial registry record; claims about what an outlet reported trace to the named coverage itself. The draft was checked twice. Both passes found errors and both sets are corrected. What materially changed: the five-year KEYNOTE-942 results replaced an earlier readout; distant metastasis-free survival eased from 62% to 59% over that period and is now stated next to the recurrence figure that improved; grade 3 or worse treatment-related events, 25% against 18%, were added; and the claim that the Phase 3 is free of the earlier trial's assessment bias was softened, because its primary endpoint is investigator-assessed too. A later pass replaced 30-month recurrence-free rates with the five-year figures, since the surrounding section discusses five-year results and quoting the earlier timepoint is the selective practice this piece criticises.</p>
</footer>

</div>

</body>
</html>

```
