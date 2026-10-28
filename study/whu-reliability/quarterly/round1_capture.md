# WHU quarterly round 1: running the four AI tools

For Fred. Sixteen runs: four tools (Claude Research, ChatGPT deep research, Gemini Deep Research, Perplexity Deep
Research) × four questions (WHU-Q1-01 to WHU-Q1-04). Each tool is run as it was in the study (`RUN_TOOLS.md`,
`perplexity_plan.md`), under `round1_protocol.md` §3, with one change the advisor ruled (§13.3): **ChatGPT is
launched through the `$deep-research` app link, as for WHU-S01 to WHU-S04, not the composer chip.**

**Not before the advisor has checked this sheet and the WHU briefs.** The answer keys are frozen before any run; you
never see them and nothing here needs them.

**The answers never go in the repository.** They go in `~/Projects/whu-study-private/answers/quarterly/round1/`,
one folder per question (`WHU-Q1-01` … `WHU-Q1-04`). Claude Code makes the folders and the record sheet before you
start, and afterwards builds the capture files and checks the fingerprints.

## Before you start (once)

1. **The record sheet.** Open `~/Projects/whu-study-private/answers/quarterly/round1/run_record.md` in TextEdit; you
   fill one row per run (columns below).
2. **TextEdit in plain text.** TextEdit > Settings > New Document > Format: **Plain text**; Settings > Open and Save:
   tick **Display HTML files as HTML code instead of formatted text**.
3. **The 48-hour rule.** For each question, run all four tools within the same 48 hours. One question at a time, all
   four tools back to back, is simplest.
4. **Don't change the tools between runs.** Same accounts, same settings, same modes for all four questions.
5. **You don't need to read the answers.** Save them as they are. Don't edit, trim or tidy anything.

## The four questions: paste exactly this

Each box is the question from its `issues/WHU-Q1-0N-*/issue.json`, followed by the sentence the protocol adds to every
question. Paste the whole box and nothing else.

**WHU-Q1-01**
```
In primary health care, does using mobile phones or tablets to keep track of the care each patient gets, together with on-screen prompts that guide health workers, reminder messages sent to patients, or both, improve the care people receive and their health? Please research this and give me a well-sourced answer with citations.
```

**WHU-Q1-02**
```
In low- and middle-income countries, do programmes meant to improve education for children and young people with disabilities work, and which kinds work best? Please research this and give me a well-sourced answer with citations.
```

**WHU-Q1-03**
```
If greenhouse gas emissions continue, how will further warming change the climate: rainfall and the water cycle, very wet and very dry extremes, ice, sea level and the oceans? Please research this and give me a well-sourced answer with citations.
```

**WHU-Q1-04**
```
Alongside cutting emissions, what part can removing carbon dioxide from the air play in reaching net zero, now and in the decades ahead? Please research this and give me a well-sourced answer with citations.
```

## For every run: what to write in `run_record.md`

| Column | What to write |
|---|---|
| Question | WHU-Q1-01 … WHU-Q1-04 |
| Tool | Claude, ChatGPT, Gemini or Perplexity |
| Started | the date and time you pressed Send (the Mac's clock, with "ET") |
| Plan accepted | the time you accepted the research plan, or "no plan shown" |
| Finished | the time the finished report appeared |
| Took | Finished minus Started, in minutes |
| Model shown | the model or mode name exactly as the app shows it |
| Memory / privacy | how you ran it: "incognito chat", "memory off", and so on |
| Searches shown | ChatGPT only: the report header's line, word for word, e.g. "Research completed in 14m · 32 citations · 41 searches" |
| Chat link | the address in the browser's address bar for that chat |
| Saved as | the file name |
| Anything unusual | a refusal, an error, a clarifying question, a wrong mode corrected: see "If something goes wrong" |

## Claude (claude.ai): Research mode, incognito

1. Open **claude.ai** and start a **new chat**.
2. **Turn on incognito** (the ghost icon at the top of the new chat). The address bar ends in `?incognito`. Write
   "incognito chat".
3. **Pick the model.** Choose **Opus 5.5** and leave its effort setting at the default. Write what the menu shows.
4. **Turn on Research** (the Research button under the message box, highlighted).
5. **Paste the question box.** Write "Started" and press Send.
6. **If Claude shows a research plan, accept it unchanged.** Write "Plan accepted".
7. **Wait for the finished report** (a report panel beside the chat). Write "Finished".
8. **Save it.** In the report panel's menu choose **Download as Markdown** (as for WHU-S05 to WHU-S08). Move the file from
   Downloads to the question's folder and name it **`claude.raw.md`**. Don't open or edit it.
9. Copy the chat's address into "Chat link". If the page says "Given access to: …" any apps, write that line in
   "Anything unusual".

## ChatGPT (chatgpt.com): deep research through the `$deep-research` app link, memory off

1. **Before the first ChatGPT run**, Profile icon > **Settings > Personalization**: memory ("Reference saved memories",
   "Reference chat history", or "Memory") **off**; **Custom instructions** off or empty. Write "memory off; custom
   instructions off". Change nothing else.
2. Start a **new, normal chat** (deep research does not run in a temporary chat).
3. **Launch deep research through the app link, not the chip.** In the message box, type `$deep-research` and choose
   the **Deep research** app from the list that appears, so that `$deep-research ` sits at the start of the message
   (this is how WHU-S01 to WHU-S04 were run). Do **not** use **+** > **Deep research** (the composer chip): that is how
   WHU-S05 to WHU-S08 were run, and none of those searched the web. Leave the model as ChatGPT sets it; write what it
   shows.
4. **Paste the question box** after `$deep-research `. Write "Started" and press Send.
5. **Accept the default plan unchanged** (**Start**). Write "Plan accepted".
6. **Wait for the finished report.** Write "Finished".
7. **Write the header line.** At the top of the report, copy the "Research completed in … · … citations · … searches"
   line word for word into "Searches shown". **If it shows 0 searches, write that, do not re-run**: its figures are
   labelled "no web search performed" (protocol §13.3).
8. **Save it.** The report's menu (share or **⋯**) > **Export to Markdown**. Move the file to the question's folder and
   name it **`chatgpt.raw.md`**.
9. Copy the chat's address into "Chat link".

## Gemini (gemini.google.com): Deep Research, the same Workspace account as the study

1. Sign in with the **same Google Workspace account as the study** (U.S. Photovoltaics).
2. **Personalisation off**, as in the study: Gemini Apps Activity / Keep Activity **off**; Personal context / Saved info /
   memory **off**. If neither is shown, write "no setting shown".
3. Start a **new chat**.
4. **Choose Deep Research** in the tools or mode picker; make sure no other mode (for example "Learn") is selected.
   Leave the model picker at its default; write what it shows.
5. **Paste the question box.** Write "Started" and press Send.
6. **Accept the research plan unchanged** (**Start research**). Write "Plan accepted".
7. **Wait for the finished report.** Write "Finished".
8. **Save it, as in the study:** on the report, **Export to Docs**; in the Google Doc, **File > Download > Markdown
   (.md)**. Name it **`gemini.raw.md`** in the question's folder. Write the Google Doc's title in "Anything unusual".
9. Copy the chat's address into "Chat link".

## Perplexity (perplexity.ai): Deep Research, personalisation off

As in `perplexity_plan.md`, with the lesson of 2026-10-27 (the first four Perplexity runs were set aside because
"Your occupation" was left set).

1. **Before the first Perplexity run, write down the state of each setting, then switch off:** memory; personalisation,
   including **Your occupation** (clear it) and any AI profile text; connected apps and files (for example Gmail, Drive);
   and any selected Space. Change nothing else. Write each setting's before and after state in `run_record.md`, so it
   can be restored afterwards.
2. Start a **new thread** (no Space selected).
3. **Choose Deep Research** (or "Research", whichever the app names it). Write the mode and any model shown.
4. **Paste the question box.** Write "Started" and press Send.
5. **Wait for the finished report.** Write "Finished".
6. **Save it** with Perplexity's own export: **Markdown** if offered, otherwise PDF. Move the file from Downloads to the
   question's folder and name it **`perplexity.raw.md`** (or `.pdf`).
7. Copy the thread's address into "Chat link".

## If something goes wrong

Each tool answers each question **once**. A second run is allowed only after a technical failure, recorded first.

- **A clarifying question instead of starting.** Reply with exactly this, and nothing else:
  - Claude, ChatGPT, Gemini: `Please answer the question as asked.`
  - Perplexity: `Please proceed with your best interpretation.` (as in `perplexity_plan.md`)
  Write the tool's question word for word and the time you replied.
- **A refusal** is the answer. Don't rephrase or retry. Save it and write "refused" and its words.
- **ChatGPT with 0 searches** is not a failure: record it and do not re-run (protocol §13.3).
- **A technical failure** (crash, an error that stops the run, no finish after about 2 hours, an empty export):
  screenshot it (Cmd+Shift+4) as `<tool>-failure.png` in the question's folder, write what happened and the time, then
  start **one** fresh run from step 1 of that tool's section, recorded as its own row marked "rerun after failure".
- **Wrong mode or model before sending:** correct it and note it. Noticed only after sending: treat it as a technical
  failure.
- **Anything else you weren't sure about:** write down what happened and when. Don't change anything to fix it.

## After each question: fingerprint the files

When all four answers for a question are saved, open **Terminal**, paste this line with the question's folder, and
press Return:

```
shasum -a 256 ~/Projects/whu-study-private/answers/quarterly/round1/WHU-Q1-01/*
```

Copy the lines it prints into the bottom of `run_record.md`, under the question's name. Don't open or edit the files
after this.

## When all sixteen are done

Tell Claude Code: "the round 1 tool runs are saved." It checks the sixteen files and their fingerprints, builds the
capture files around them without retyping anything, restores nothing on your behalf (you restore the Perplexity and
ChatGPT settings from your notes), and commits only the sha256 manifest.
