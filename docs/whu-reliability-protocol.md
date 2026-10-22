# WHU Reliability Study: Protocol

Oct 18, 2026 · @Fred · Frozen by the commit that adds this file to the repository; later rulings are dated within

## Purpose

The study tests one claim: **What Holds Up's finished answers are more reliable than answers from frontier AI research tools used on their own.** If the claim fails, WHU has no product, so the protocol is written to give it a fair chance to fail.

"More reliable" means three things, each measured separately:

- **Citation support:** a cited source actually says what the sentence citing it says.
- **Conclusion calibration:** the answer's main conclusions match what the best available expert review concludes, with the same direction, size, scope and certainty.
- **Coverage:** the answer finds and uses that expert review.

The October 2026 pilot found WHU's citations held up better (1 of 16 sentences with a majority-judge problem, against 5 of 16 for Claude Research). That gap was not statistically established (p ≈ 0.17 two-sided), the sample barely reached conclusions, and WHU's rules were tuned on the pilot's four questions. This study fixes those weaknesses.

## Hypotheses and success threshold

WHU is declared more reliable only if **both** primary hypotheses hold against Claude Research, the primary comparator.

|  | Measure | Rate compared | Success means |
| --- | --- | --- | --- |
| **H1** (primary) | Citation support | Share of sampled cited claims judged not supported | WHU's rate is at most half Claude Research's, and the 95% interval for the difference excludes zero |
| **H2** (primary) | Conclusion calibration | Share of answer-key conclusions the answer overstates, understates, contradicts or omits | Same test as H1 |
| H3 (secondary) | Coverage | Share of questions where the answer cites the key review | Reported, no threshold |
| H4 (secondary) | All of the above | WHU against ChatGPT deep research and Gemini Deep Research | Reported, no threshold |

If only one of H1 and H2 holds, the result is reported as a partial advantage on that measure, not as "more reliable". The threshold of half is fixed now and cannot be changed after any result is seen.

## Systems compared

Every system gets the same question text, followed by: "Please research this and give me a well-sourced answer with citations."

| System | Role | Configuration |
| --- | --- | --- |
| What Holds Up | Tested system | Full publishing process: every check and gate through to a page that passes preflight. Code frozen at one commit for the whole study. The answer is what WHU would publish. |
| Claude Research mode (claude.ai) | Primary comparator, "the LLM alone" | Same model family WHU is built on. Research plan accepted unchanged, no follow-up questions. |
| ChatGPT deep research | Secondary | Paid plan, memory off, plan accepted unchanged, no follow-ups. |
| Gemini Deep Research | Secondary | Default model on the account used, plan accepted unchanged, no follow-ups. |

For every answer, record the date and time, the model or version shown, and the full export, hashed at capture. The three tools run within the same 48 hours for each question.

WHU uses far more time and money per answer than the tools. That is part of what is being tested, so cost and elapsed time are reported for every system (section on measures).

## Question selection

Four questions are drawn at random from published expert reviews: one from Cochrane (health), one from Campbell (social policy) and two from IPCC AR6 (climate), so three are outside health. Nobody picks a question by hand, so nobody can pick ones that suit WHU.

| Stratum | Questions | Sampling frame |
| --- | --- | --- |
| Health | 1 | Cochrane systematic reviews |
| Social policy | 1 | Campbell Systematic Reviews |
| Climate and environment | 2, from different AR6 reports | IPCC AR6 numbered Summary for Policymakers statements carrying calibrated language (a confidence level, or a likelihood term set in italics) |

**Eligible** if the review:

1. was published January 2024 to September 2026 (IPCC AR6: 2021 to 2023);
2. states its main conclusion with a certainty grade or an explicit statement of strength (GRADE, IPCC confidence terms, or equivalent);
3. can be put as one plain question a non-expert would ask;
4. has at least its full abstract publicly readable;
5. is not on a topic covered by a published WHU issue, the four test issues or the two practice issues.

Reviews that find the evidence insufficient stay eligible. They test whether a system claims more than the evidence allows.

**Drawing.** For each frame, the numbered eligible list is shuffled with a seed: the full 40-character hash of the commit that freezes this protocol, read as a hexadecimal integer. That seed can't be known until the protocol is frozen. The first eligible entry is the draw; the second IPCC question is the next eligible statement from a different AR6 report. If a drawn entry fails eligibility on closer reading, the next in the shuffle is taken, and the reason is logged.

**Wording.** Each question is written from the review's stated objective in plain words, without naming the review. All four are committed before any system runs.

## Answer keys

Each question gets an answer key, written from its review and frozen before any system runs. The keys are what conclusion calibration is scored against.

A key lists up to five of the review's main conclusions. Each one records:

- **Direction:** helps, harms, no difference, or unclear.
- **Size,** where the review states one, with its interval.
- **Certainty,** in the review's own terms (for example GRADE "low", IPCC "medium confidence").
- **Scope limits:** who and what the conclusion covers, and what it explicitly does not.
- **The review's own words** for the conclusion, quoted with its location.

Keys are drafted by Claude from the full text where it is available and checked before freezing: in Stage 1 by a second, separate Claude instance and any volunteer expert, in Stage 2 by a human reviewer with relevant expertise. A conclusion a checker disputes is corrected or dropped, and the change is logged. Keys are never shown to any system being tested.

**When a system disputes the key.** Expert answer keys contain errors. In TheoPhysEval (arXiv 2610.16733, October 2026), several expert reference answers turned out to be wrong after the model disputed them, and the contributors revised their own keys after seeing the model's answers. So a fixed procedure applies here, set before any results:

- Every case where a judge finds an answer contradicts a key conclusion is logged as a possible key dispute, whichever system wrote the answer.
- Disputes are settled by a reviewer who did not write that key and does not know which system raised the dispute, reading the review itself.
- A key may be corrected only on that reviewer's finding. The correction then applies to every system's answer on that question, and is recorded in the deviations log with the original wording kept.
- The number of key corrections is reported, with how each one changed every system's score.

## Measures

### M1. Citation support (H1)

From each answer, sample 10 specific factual claims at random with a fixed seed, or all of them if there are fewer. A specific factual claim states a number, names a study or body, or reports a finding. Cited and uncited claims are both sampled, so a system can't score well by citing nothing.

Statements about the answer's own process, such as which sources it read or could not open, are not claims about the topic and are not sampled. B21 already checks WHU's versions of these.

Each claim gets one label:

| Label | Meaning | Counts as a failure |
| --- | --- | --- |
| Supported | The source says it: numbers, scope, strength and causal language all match | No |
| Overstates | The source says something weaker | Yes |
| Understates | The source says something stronger | Yes |
| Absent | The source is on topic but doesn't contain the claim | Yes |
| Wrong source | A real source about something else | Yes |
| Contradicted | The source says the opposite | Yes |
| Uncited | No source is given for a specific claim | Yes, and reported separately |
| Unreachable | The source can't be retrieved | Excluded from the rate, reported. Above 20% of a system's sample is flagged. |

### M2. Conclusion calibration (H2)

For each conclusion in the answer key, the judge reads the whole answer and labels what it says about that conclusion: **Matches**, **Overstates** (stronger direction, size, scope or certainty), **Understates**, **Contradicts** or **Omits**. Everything except Matches counts as a failure. Scoring against the key, rather than against conclusions pulled out of each answer, means no extraction step can favour one system. At up to five conclusions per question, that is at most 40 items per system.

### M3. Coverage

Whether the answer cites the key review, and whether its main conclusion is represented (from M2).

### M4. Cost and time

For every answer: money spent (API spend, plus a share of subscription cost), elapsed time from question to finished answer, and, for WHU, the operator's hands-on time.

## Blinding

Judges and human reviewers never learn which system wrote what they are scoring, or that systems are being compared.

- **One plain format.** Every answer is converted to plain text with numbered references and URLs. Headings, layout and visual style are removed.
- **House style removed.** Phrases that identify WHU ("we hold", "What Holds Up", its confidence-line format, its notes on sources it hasn't read) and any tool's signature phrasing are rewritten to neutral wording by a fixed list, applied by script. The list is frozen with the protocol.
- **Blinding check.** Before scoring, a separate model is shown 20 random blinded claims per system and asked to guess the system. This is reported as a measured limitation, not a gate (ruled 19 October): on same-topic material in the practice run, every system was identified 20 of 20 times by its writing style, which the rules forbid rewording. The gate is the bias test: the judges' labels must not change when they are told who wrote a sentence.
- **Random order.** Items reach judges and reviewers in random order, mixed across systems and questions.

## AI judges

Two judges score every item: a Claude model and a ChatGPT model, both through their APIs, each run twice. Gemini is dropped as a judge. In the pilot it read conclusions too literally, misreported what it could reach, and hung on 4 of 5 attempts. It remains a system under test.

- **Models.** The strongest generally available model from each company on the start date, with exact versions recorded. They are not changed during the study.
- **Same evidence for both.** Each cited source is retrieved once by script and saved as a snapshot, with its hash and how much of it was readable (full text or abstract only). Both judges see the same snapshot, so one judge reaching a paywall and the other not can't create a disagreement.
- **What a judge sees.** For M1: the claim, about 400 characters around it, and the source snapshot. For M2: the whole blinded answer and one answer-key conclusion. Never the system's name, its reasoning notes, or any other judge's verdict.
- **Fixed prompt.** One prompt per measure, frozen with the protocol. It tells the judge to use only the evidence shown, not outside knowledge.
- **Agreement.** An item counts as agreed only when both judges give the same label in both runs. Anything else goes to a person.
- **Self-preference.** WHU and Claude Research are both built on Claude, so a Claude judge could favour both. The primary comparison is between those two, so the bias largely cancels. The ChatGPT judge and the human reviewers check it, and results are reported for each judge separately.

**Rulings from prep round 1 (19 October 2026).** A behaviour test of the M1 prompt on 16 pilot items, where all three pilot judges agreed, raised these questions. The test checked that the judges follow the prompt, not that they are right: no human-settled labels exist, so judge accuracy is measured only in Stage 2.

- **Claude judge model: Claude Opus 5.5, not Fable 5.1.** Fable 5.1 carries extra safety measures for biology and refused two biomedical sources outright. Opus 5.5 is the strongest generally available Claude model without them. The ChatGPT model is confirmed from OpenAI's model list, not inferred from a pricing page.
- **Refusals.** A refused item is retried once, unchanged. If it is refused again, the other judge's label stands alone and the item goes to a person, as a disagreement would. Refusal rates are reported per judge and per system. Inputs are never reworded to get past a refusal.
- **Framing words are part of the claim.** A superlative, ranking or "first" said about a source ("the most explicit", "the largest") must be supported like any other word. If the source doesn't support it, the label is Overstates.
- **A sentence citing two or more sources** is judged against all of them together, and the judge sees every cited snapshot.
- **Abstract-only snapshots.** If the snapshot holds only an abstract and the judge says Absent, the item is recorded as "Not verifiable (abstract only)". It is excluded from the rate like Unreachable, reported, and flagged above 20% of a system's sample.
- **Long sources are not cut.** A snapshot goes to the judge whole up to 150,000 tokens. Above that, a script keeps every section containing the claim's key terms, and those items are reported separately.
- **Source first in the prompt,** so it can be cached. The measured projection is about $280, or about $165 with caching, at pilot-sized sources. If the projection on the drawn questions' real sources goes above $300, Fred decides before the full run.

**Blinding rulings (19 October 2026).** Judges see one sentence and its sources, not a whole answer, so blinding works at the sentence level.

- **Citation markers.** WHU's export adds \[n\] markers from its bindings, in the same style as the tools' answers. This is done by script from stored data, not by rewording.
- **Process sentences are not sampled.** Sentences about how the answer was made (notes on unread sources, dated process notes, change history, the watch section) are excluded from sampling for every system. They are not claims about a source.
- **"In our reading" and similar phrases are deleted, not replaced.** Replacing them with a new phrase would create a new marker.
- **First person is not paraphrased.** A model rewrite would change the claim being judged.
- **Length and paragraph shape are not changed.** They are invisible at the sentence level.
- **The paid identifiability check runs before freezing.** A model sees 20 blinded sentences per system and guesses which system wrote each. With four systems, chance is 25%. If WHU is identified more than 50% of the time, the blinding is not good enough. The phrase list is then extended and the check re-run, and the result is reported either way.

**Audit stage design approved (19 October 2026)**, as written in docs/whu-audit-stage-design.md, with two additions:

- A sentence that still fails after three read-and-correct rounds is cut from the answer, and the cut is logged.
- The meta description and card text are read in the same pass as the body.

Order: build, one practice run on a question that is not in the study, measure cost and time, then freeze.

**Rulings from prep round 2 (19 October 2026).**

- **Refusals stay under the refusal rule.** Opus 5.5 refuses the same two sources Fable 5.1 did: a gut-microbiome trial and a vitamin D chapter. The Claude judge stays Opus 5.5. Refusal rates are reported as a result in their own right, because a judge that refuses ordinary biomedical sources is itself a finding about these tools.
- **The identifiability check was confounded, and its pass/fail role is replaced.** WHU's sentences came from different topics than the tools' sentences, so topic alone gave WHU away. The check is re-run on same-topic material (WHU's practice answer to a pilot question, against the three tools' answers to that question) and reported as a measured limitation, not as a gate. Writing style can't be hidden without rewording, which the rules forbid.
- **The gate is a bias test.** The judges are never told who wrote a sentence. The question is whether knowing would change their labels. The 16 test items are judged four ways: no author line (twice, to measure ordinary run-to-run change), "written by What Holds Up, an evidence-review publication", and "written by an AI chatbot". If either named condition changes at least two more labels than the repeat run did, the judges are sensitive to authorship, and the study must say so and report labels by condition.
- **Chart descriptions and rubric scores are not sampled.** They are WHU's own judgments, not claims about a source.
- **"This page" becomes "this report".** Deleting it breaks the sentence, and the tools use "this report" themselves. Sentences that refer to the answer itself are process sentences and are not sampled anyway.
- **Card and meta-description sentences are checked against the page body,** which has already been audited against the sources. A summary that says something the body doesn't is a finding.
- **Older issues.** The "audit complete" STOP skips deskilling, cdk46 and melanoma, which is correct for a gate. Deskilling was already read in full by hand. Cdk46 and melanoma get the audit stage after the practice run. Any source whose licence forbids AI processing (S001, NCCN) is never sent to a model. Sentences bound only to it are marked for a human read.

**Results from prep round 3 (19 October 2026).**

- **The bias test passed for both judges.** Across the 16 items, the repeat run changed 0 Claude labels and 1 ChatGPT label. Naming What Holds Up as the author changed 1 Claude label and 0 ChatGPT labels; "an AI chatbot" changed 0 and 1. The rule fails only at 2 or more changes beyond the repeat run.
- **Missing cited sources.** An item whose cited source has no snapshot is recorded as INCOMPLETE\_SOURCES and is not judged. Two pilot items fall into this (P34, P40).
- **Practice question: Q2, ultra-processed foods.** It had the fewest unreachable cited sources across the three tools' answers: 25, against 33 to 38 for the other three questions.
- **Cost.** OpenAI's cache only hit on identical prompts. The projection is about $125 at pilot-sized sources and about $199 at twice that, both under the $300 line.

**Budget ruling (approved by Fred, 20 October 2026).** The dry run put WHU's own process at about $44 per question. At eight questions, the study would have cost roughly $480–550, against a $300 line. Three changes bring it to about $200–245:

- **Four questions instead of eight.** Precision depends on the number of sentences judged, so more sentences are sampled per question to keep that number unchanged. The cost: less can be said about how WHU varies between topic areas, because each area has only one or two questions.
- **The audit's second reader checks a 10% sample of sentences marked as holding, plus every flagged sentence**, as docs/whu-audit-stage-design.md specifies. The dry run had it reading every sentence. This brings WHU's cost to about $31 per question.
- **Each judge reads each item once.** A random 20% sample gets a second read, so run-to-run consistency can still be reported. In the bias test, a repeat run changed 0 of 16 Claude labels and 1 of 16 ChatGPT labels.

If the practice run's measured cost would put the study over $300, Fred decides before the full run.

**The frozen WHU process (ruled 20 October 2026).** WHU's published issues use steps that depend on people: passage reading by the operator, an outside reviewer, verification by a second session, and the operator's acceptance. For the study, each such step is either done by a fixed, logged procedure or excluded. Every exclusion is named here and reported with the results.

- **Stages 1–3 (premise, research and source store, drafting and binding with checks B1–B24)** run as in WHU's process, done by Claude Code. Drafting time isn't metered, so it is reported as elapsed time.
- **Source fetching the scripts can't do** stays an operator step, because it is part of WHU's process. Each fetch is logged with its time.
- **Rulings go to the ruling model.** This covers gate adjudication, conclusion-judge decisions, audit findings and second-reader disagreements. The model uses one fixed prompt, frozen with the protocol and identified by its sha256. It sees only the finding, its sentence and the quoted source text. No advisor session rules during the study.
- **Operator passage reading and the internal pre-review are replaced by the audit stage,** which reads every sentence against its source. This is the main difference between the study's WHU and the WHU of the published issues, and the results say so.
- **Excluded:** outside review, verification by a second session, operator acceptance, and publication. A study answer ends at "ready for operator acceptance": every check passed except those four. Preflight runs in a study mode that records each of them as SKIPPED, with the reason.
- **Sentences that need a person** (HUMAN\_READ\_REQUIRED, or card and description wording left for a person) are operator steps, logged. Any left unread are cut from the answer, and the cut is logged.
- **Spending limits.** Each study issue has a $50 limit, set before the freeze. If an answer can't finish within it, that is recorded as a result, and the limit is not raised. The $25 daily limit stays, and runs pick up the next day.
- **No coaching.** The operator does only what this list prescribes, and every manual step is logged with its time.

**Practice run: a fresh issue on Q2 (WHU-P02), from the question alone.** The earlier pilot test issue on the same question (WHU-T02) was built by an older process and is moved out of reach before drafting starts. The conclusion judge was calibrated partly on T02's sentences, so its results on the practice run aren't out of sample. That matters for the practice run only, not the study.

**Practice run result (WHU-P02, completed 21 October 2026).** The frozen process ran from question to "ready for operator acceptance" in a fresh Claude Code session that had never seen the pilot's answers.

- **Answer:** 42 claim sentences, 17 sources. One operator step: five browser downloads, about 2 minutes.
- **Cost of the clean run:** $9.83, plus $4.28 lost to a day-cap stop before stages could resume. The figure includes three gate runs, the source advocate, the conclusion judge, the audit and every ruling. Four study questions project to about $40 for WHU's process, so about $140–210 for the study with judging.
- **Defects found and fixed before the freeze:**
  - **Sources delivered blank:** the audit could hand a reader an empty source, and the ruling model then overruled the readers who said so (GAP-015).
  - **Mismatched text copies:** the audit and the bindings read different extractions of the same PDF.
  - **Rulings made without context:** a lookup bug meant no ruling payload carried the text around a quotation.
  - **False notes on the advocate's quotations:** every one was checked against an empty string, so each was reported as not in the held text.
  - **Unchecked advocate quotations:** 22 of 29 were not in their source (GAP-018); after one re-ask, 3 of 28 remained absent.
  - **Conflicting rulings:** findings on one sentence were ruled one at a time and could return conflicting texts (GAP-019).
  - **Dangling references:** a ruling could remove a name that a later sentence still uses (GAP-016).
  - **Unrecorded recency failures:** a source the gate couldn't confirm as current produced no finding (GAP-014).
  - **Tags read as text:** source-list tags were read as part of the entries (GAP-017).
  - **No resume after a cap stop:** a stage stopped by the day cap lost its output.
- **The ruling model is the least stable part of the process.** Ruled together instead of one at a time, 7 of 13 sentences came out differently. On a seeded repeat of 6 rulings, it agreed with itself 4 times on decision and text, and 5 times on decision alone. The study measures this with a 20% repeat sample on every question and reports the agreement rate.

**Pre-freeze rulings (21 October 2026).**

- **One question per frame.** The four study questions are drawn one from each sampling frame: Cochrane, Campbell, the National Academies and IPCC AR6.
- **One more practice run, on a National Academies report published before January 2024.** That frame's reports are the longest sources the study will meet, up to about ten times WHU-P02's largest, so it is the hardest test of how long sources are cut down and checked. Campbell and IPCC sources fall within the range it tests.
- **Blinding: conversion defects are fixed, writing style is not.** For every system alike:
  - leftover markup is removed: Wikipedia tags, broken link fragments, "\[cite: n\]", and citation numbers stuck to names;
  - the "≈" and "\~" rules are made correct, so there is no "a about 15%";
  - "on this page" is deleted rather than rewritten;
  - British spellings are mapped to American by a fixed word list. Phrasing such as "on its own criteria" is the system's voice and stays, as do sentence length and tone.
- **The conclusion judge's prompt (M2) is tested before the freeze,** on the practice answer and the three tools' answers to the same question, as M1 was.
- **The audit gets checked by people too.** In Stage 2, the paid human reviewers check, for each question, every sentence the audit flagged and a random 20 of the sentences it passed. That gives the audit its own accuracy figure.
- **Open gaps.** GAP-009 does not block the study, because study pages have no footer, card or description, and the coverage check confirms changecheck reads every changed body sentence. GAP-011, -012 and -013 concern published issues only. All four stay open, to be fixed before those issues are next published.

**Frame and draw rulings (21 October 2026).**

- **The National Academies frame excludes the Health and Medicine Division.** Health questions come from the Cochrane frame. Without this exclusion, a National Academies draw could produce a second health question, against the protocol's intent that most questions fall outside health. The first practice draw did exactly that: a report on the long-term health effects of antimalarial drugs. That issue (WHU-P03) is withdrawn, and the practice question is redrawn from the corrected frame with a new seed, both logged with this reason.
- **The draw method for frames without a full eligibility list.** The candidate list is shuffled with the seed, eligibility is checked in that order, and the first eligible candidate is the draw. Every candidate checked is logged with its result and reason, and so is every page read to check it. This picks uniformly at random from the eligible set.
- **The IPCC unit is a numbered statement in a Summary for Policymakers that carries IPCC calibrated language** (a confidence level or a likelihood term). That includes the numbered sub-statements as well as the headlines. Most Working Group I headlines carry no calibrated term, though their sub-statements do. Counting headlines only would have dropped most of the physical science from the frame.
- **The vitamin D exclusion is narrow.** It removes only reviews of vitamin D supplementation in older adults, the question WHU tested in the pilot, not every vitamin D review.
- **M2 v2 frozen** (sha256 64a5a5b6…). The judges agreed on 45 of 48 behaviour-check items. One borderline case (B3, an answer saying trials "causally demonstrated" an effect a conclusion stated with moderate certainty) was labelled Matches by both judges, and is flagged for Stage 2's human reviewers. The prompt was not tuned to it.

**National Academies frame dropped (21 October 2026, amending rev 34).** Once health and medicine units were excluded, 262 reports remained in the 2017–2023 practice frame, and 66 in the study window. The practice redraw checked 227 of the 262 and found none eligible: 204 used no graded evidence scale and 23 had no Summary chapter to check. Outside health, National Academies reports don't grade their conclusions, so the frame is empty under the grade test. The rule excluding health units should have been checked against a sample of reports before it was adopted. Doing so would have shown the frame couldn't survive it.

- **Study frames are now** Cochrane (1 question), Campbell (1) and IPCC AR6 (2), with three questions outside health. Eligible counts: Cochrane 724, Campbell 24, IPCC AR6 400 of 419 numbered statements.
- **IPCC likelihood terms count only where IPCC sets them as calibrated, in italics.** A script checks this against the PDF. All nine statements that rely on a likelihood term alone passed.
- **The practice frame is IPCC AR5,** with 76 eligible numbered statements across its four Summaries for Policymakers. It predates the study window and isn't in the AR6 frame. Draw seed 20261022. The practice issue is WHU-P04. Its question and source are recorded only where a drafting session can't read them.

**Second practice run (WHU-P04, IPCC AR5 question; completed 22 October 2026).** The answer reached "ready for operator acceptance" with long sources: ten held, the largest 439,227 characters. Every batch the audit read carried all of its bound passages.

- **Cost:** $8.78 metered, of which $1.66 was a superseded advocate run, so about $7 for a clean run. Operator time: 1 minute, for one browser download. Session working time: about 77 minutes.
- **Defects found and fixed:**
  - **The advocate matched sentences to sources by name, not by binding.** A mismatch silently sent sentences to the wrong sources (GAP-020).
  - **Adding a source left its ledger entry empty.**
  - **The audit's trimming could leave out a bound passage.** When a document's passages were far apart, the window kept only one side. The delivery check stopped the run before any spend; now each bound passage gets its own window, and an oversized batch is split.
- **The advocate's quotations remain poor.** 12 of 23 were still not in the source after a re-ask. The ruling model is told so truthfully. This is reported per question as a measure of WHU's process.
- **Ruling-model consistency:** 4 of 5 repeated rulings agreed on decision and text, and 5 of 5 on decision alone.

**Freeze rulings (21 October 2026).**

- **Every frozen file is pinned.** These are: RUN.md, both judge prompts, the ruling and audit prompts, the blinding list and the spelling map. Code refuses to run if a file's sha256 differs from the one recorded at the freeze.
- **canary.py runs on study issues.** It is free, and it marks unreadable documents. Without it, an absence in a document the checks can't read would be reported as "absent" rather than "could not determine", which is wrong.
- **Recency finding ids carry the draft's sha,** as claim ids do, so a new finding can't be mistaken for an earlier, already-decided one.
- **The seed rule.** The seed is the full 40-character hash of the freeze commit, read as a hexadecimal integer.
  - Each frame's numbered eligible list is shuffled with that seed, and the first eligible entry is the draw.
  - The second IPCC question is the next eligible statement in the same shuffle that comes from a different AR6 report than the first.
  - At the draw, a candidate whose question duplicates one WHU has published or tested (the three published issues, the pilot's four questions, and the two practice questions) is ineligible, with the reason logged.
  - The same seed serves the bootstrap.
- **Checklist.**
  - **Done:** the frozen process (item 5), WHU outside health (item 6), the judge prompts (item 8) and the blinding list (item 9). For item 6, the IPCC practice run stands for the non-health frames. Campbell reviews are the same kind of document as Cochrane reviews in form and length, so a separate Campbell practice run would test nothing new.
  - **First step after the freeze:** measuring judging cost on the drawn questions' real sources (item 7).
  - **Covered by Stage 2:** the audit's ground truth (item 10).
- **The freeze commit holds this protocol,** exported from this doc, as docs/whu-reliability-protocol.md. It also holds the frozen files, the code they run and the three study frames, and nothing else.

## Human ground truth

People settle what the AI judges can't, and measure how often the judges are wrong when they agree.

**The study runs in two stages.** Stage 1 is AI judging only, with whatever volunteer reviewers come forward. Stage 2, paid human review of the items described below, goes ahead only if Stage 1 shows WHU meeting the half threshold on H1 or H2. A Stage 1 result is never presented as the study's finding. If it is published, it is labelled "AI judges only, not yet checked by people". The claim that WHU is more reliable requires Stage 2.

- **What goes to people:** every item the judges didn't agree on, plus a random 20% of agreed items, drawn evenly across systems.
- **Who:** reviewers with professional or graduate training in the question's field, recruited partly through the Substack reader-review call. Each item is scored by one reviewer, and a random 20% of those by a second, to measure agreement between people.
- **Blind:** reviewers see the same blinded material as the judges and never see AI verdicts before submitting. They record whether they read the full source or only an abstract.
- **Not the operator.** Fred does not score items. He knows which system wrote what, and the pilot showed that non-expert scoring stalls on technical claims.
- **Final labels:** a person's label wins wherever one exists. Agreed items no person reviewed keep the AI label, and the judges' error rate on the 20% audit is used to correct each system's rates, reported beside the uncorrected figures.

## Analysis plan

The primary test compares WHU with Claude Research on H1 and H2, using final labels after human review and judge-error correction.

- **Rates:** for each system, the failure rate on M1 (about 80 claims) and on M2 (at most 40 conclusions).
- **Intervals:** claims from the same answer are not independent, so intervals come from a bootstrap that resamples whole questions: 10,000 resamples, seed from the freezing commit's hash. Both the difference and the ratio of rates are reported.
- **Decision:** a hypothesis holds when WHU's rate is at most half of Claude Research's **and** the 95% interval for the difference excludes zero.
- **Reported with no threshold:** each system against each other, health against non-health questions, each judge separately, uncorrected AI-only results, and the direction of every failure (overstates against understates). The direction result settles the question the pilot left open, because the label set now includes Understates.

**Extension rule, used at most once.** Four questions give wide intervals, especially for M2. If WHU's rate meets the half threshold but the interval still includes zero, four more questions are drawn the same way, one per frame, and the analysis is rerun on all eight. The new seed is the hash of the commit that records the first results. If the threshold itself is missed, there is no extension: the result stands and is reported.

## Fairness and integrity rules

1. **WHU is frozen.** Its code, rules and prompts stay at one commit from the first question to the last answer. A fix found during the study waits until the study ends.
2. **No reruns.** Each system answers each question once. The only exception is a technical failure (a crash, a timeout, an empty export), which is logged with evidence before the rerun.
3. **No coaching.** WHU's operator does what WHU's process prescribes and nothing more. Every manual step is logged with its time, so it can be judged later whether a person, rather than the system, did the work.
4. **Everything saved as produced.** Every answer, source snapshot, judge reply and human label is saved and hashed when made, and none is edited afterwards.
5. **The order is fixed.** Protocol frozen, then questions drawn, then answer keys frozen, then systems run, then blinding, then judging, then human review, then analysis. Each step is committed before the next begins, and git timestamps are the record.

## Reporting and deviations

The results are published whatever they show, including if WHU fails. The write-up states the primary result first, in the terms of the hypotheses above, before any secondary finding.

Everything needed to check the result is released alongside it: questions, answer keys, all answers, source snapshots where licences allow, judge prompts and replies, human labels and the analysis code.

A **deviations log** is kept from the day the protocol is frozen. Every departure from this document goes in it, with its date, what changed, why, and whether it was decided before or after any result was seen. The log is published with the results.

## Open items before freezing

- [x] **OpenAI API key.** Confirmed on 19 October 2026: it is in backend/.env, which is gitignored and has never been committed.
- [x] **Human reviewers.** Decided: no paid reviewers in Stage 1. Payment is decided after Stage 1, only if its result justifies Stage 2.
- [x] **Answer-key checking in Stage 1.** Ruled 19 October: with no paid reviewers, a key is drafted by one Claude instance from the review's full text, then checked against the review by a second, separate instance; a volunteer with relevant expertise checks it too where one is available. Neither instance is WHU's advisor. Stage 2 adds expert review of every key, and any correction then follows the key-dispute rules.
- [x] **Advisor rulings during WHU's run.** Ruled 19 October: rulings on audit findings are part of WHU's process. During the study they are made by a ruling model, called by WHU's driver script with a fixed prompt frozen with the protocol, not by the advisor session. The ruling model sees only the finding, its sentence and the quoted source text. It never sees the answer keys, the identity of the review a question came from, or any other system's answer. Every ruling is logged with its time.
- [x] **Define the WHU process that gets frozen.** Ruled 19 October: the full-read audit is part of WHU. It is built as a stage: a written procedure and fixed prompts that Claude Code runs on every sentence of a draft against the held source text, with every finding settled and recorded before publishing. The deskilling audit is the reference: it led to 140 corrected sentences out of about 435, where the automatic checks caught almost none and the one-shot conclusion judge caught 15 of 24 judgement errors, with 12 false alarms among 24 sound sentences. Build it, try it on one practice question, then freeze.
- [x] **WHU outside health.** Claude Code runs the whole process on one practice question in each non-health stratum, taken from reviews published before January 2024 so they cannot be drawn. Practice answers are never scored for the study. Any change goes in before freezing.
- [ ] **Judging cost.** About 480 items (4 systems × 80 claims + 40 conclusions), drawn as about 20 claims and 10 conclusions per system per question. Each judge reads each item once, and a random 20% is read a second time. Projected at $100–170 from pilot-sized sources. Claude Code measures it on the drawn questions' real sources before the full run; if the study would go above $300, Fred decides before the full run.
- [x] **Judge prompts** written, tested on pilot items whose labels are already settled, and frozen.
- [x] **Blinding phrase list** written and tested on WHU's published issues.
- [ ] **Ground truth for the audit itself.** The audit's verdicts were judged by Claude (Claude Code's reading plus advisor review), not by people. Stage 2's human review includes a sample of them.

Once these are settled, the protocol is committed to the repo, and that commit's hash seeds the question draw.
