# Running Claude, ChatGPT and Gemini on the four study questions

For Fred. Twelve runs: three tools × four questions (WHU-S01 to WHU-S04). Each tool is set up and run the way it was in the October 2026 pilot (`~/Downloads/Citation Pilot 2026-10-16/`, README and `data/run_log.md`), under the frozen protocol (`docs/whu-reliability-protocol.md`, "Systems compared").

Nothing in this sheet uses Terminal except one copy-and-paste line at the end of each question (step 6). **The answers never go in the repository.** They go in `~/Projects/whu-study-private/answers/`.

## Before you start (once)

1. **The folders are ready.** `~/Projects/whu-study-private/answers/` holds one folder per question (`WHU-S01` to `WHU-S04`) and a record sheet, `run_record.md`. Open `run_record.md` in TextEdit; you fill one row per run.
2. **Set TextEdit to plain text.** TextEdit > Settings > New Document > Format: **Plain text**. Then Settings > Open and Save: tick **Display HTML files as HTML code instead of formatted text**. (Without this, pasting a Markdown answer into TextEdit can drop its links.)
3. **The 48-hour rule.** For each question, run all three tools within the same 48 hours. Doing one question at a time, all three tools back to back, is simplest.
4. **Don't change the tools between runs.** Same account, same settings, same mode for all four questions.
5. **You don't need to read the answers.** Save them as they are. Don't edit, trim or tidy anything.

## The four questions: paste exactly this

Each box is the question from its `issues/WHU-S0N-*/issue.json`, followed by the one sentence the frozen protocol and the pilot add to every question. Paste the whole box as it is, and nothing else: no greeting, no extra words, no edits.

**WHU-S01**
```
For people being checked for TB, does DNA-based testing, used instead of the older microscope or lab-culture methods, change what happens to them, for example whether they survive, are cured, or start treatment sooner? Please research this and give me a well-sourced answer with citations.
```

**WHU-S02**
```
For teenagers who are depressed, does it make a difference how CBT, a common talking therapy, is given: in a group, one to one, remotely, or as self-help with or without a therapist's guidance? Please research this and give me a well-sourced answer with citations.
```

**WHU-S03**
```
Does involving the wider public, such as community groups, businesses, young people, workers and Indigenous communities, in making climate policy affect whether the policies win political backing and get results? Please research this and give me a well-sourced answer with citations.
```

**WHU-S04**
```
Is the fast growth of cities around the world a chance to make places better able to cope with a warming climate, or mainly a source of added risk? Please research this and give me a well-sourced answer with citations.
```

## The four extension questions (WHU-S05 to WHU-S08): paste exactly this

Drawn on 24 October 2026 under the protocol's extension rule (`deviations.md`). Run them exactly as the first four: same tools, same account, same settings, the same 48-hour rule for each question, and every step below. Record them in `~/Projects/whu-study-private/answers/run_record_S05-S08.md` (same columns as `run_record.md`), and save each answer in `answers/WHU-S05/` to `answers/WHU-S08/`. The fingerprint line at the end of each question uses that question's folder (for example `WHU-S05`). When all twelve extension runs are done, tell Claude Code: "the extension tool runs are saved."

**WHU-S05**
```
For people who have had a kidney transplant, does avoiding steroid medicines from the start, or stopping them later, change what happens to them, for example whether they survive, keep the new kidney, have rejection episodes or develop diabetes? Please research this and give me a well-sourced answer with citations.
```

**WHU-S06**
```
For children and young people who are at risk of offending, or who have already offended, do arts programmes reduce offending or improve their behaviour and wellbeing? Please research this and give me a well-sourced answer with citations.
```

**WHU-S07**
```
Could changing how cities are laid out, for example making them denser, more mixed and better connected, together with measures such as transport pricing, cut greenhouse gas emissions from transport? Please research this and give me a well-sourced answer with citations.
```

**WHU-S08**
```
Does taking climate change into account when designing and planning towns, rural areas and infrastructure make them better able to cope and improve people's wellbeing? Please research this and give me a well-sourced answer with citations.
```

## For every run: what to write in `run_record.md`

One row per run, written as you go:

| Column | What to write |
|---|---|
| Question | WHU-S01 … WHU-S04 |
| Tool | Claude, ChatGPT or Gemini |
| Started | the date and time you pressed Send (from the Mac's clock, with "ET") |
| Plan accepted | the time you pressed Start on the research plan, or "no plan shown" |
| Finished | the time the finished report appeared |
| Took | Finished minus Started, in minutes |
| Model shown | the model or mode name exactly as the app displays it (for example "Opus 5.5 (Medium)", "Flash") |
| Memory / privacy | how you ran it: "incognito chat", "memory off", and so on |
| Chat link | the address in the browser's address bar for that chat |
| Saved as | the file name (claude.md, chatgpt.md, gemini.md) |
| Anything unusual | a refusal, an error, a clarifying question, a wrong mode corrected: see "If something goes wrong" |

## Claude (claude.ai): Research mode, incognito

As in the pilot: claude.ai Research mode, Opus 5.5, incognito chat.

1. Open **claude.ai** and start a **new chat**.
2. **Turn on incognito.** Click the incognito (ghost) icon at the top of the new chat, so the chat is not saved and does not use memory. The address bar ends in `?incognito` when it is on. Write "incognito chat" in the record.
3. **Pick the model.** In the model menu, choose **Opus 5.5**, as in the pilot, and leave its effort setting at the default the menu shows. Write what the menu shows in "Model shown".
4. **Turn on Research.** Click the Research button under the message box so it is highlighted.
5. **Paste the question box** for this question. Write the time in "Started" and press Send.
6. **If Claude shows a research plan, accept it as it is.** Don't change it. Write the time in "Plan accepted".
7. **Wait for the finished report.** It appears as a report panel beside the chat. Write the time in "Finished".
8. **Save it.** In the report panel, use its **Copy** button (copies the whole report with its links). Open a new TextEdit document (plain text, see "Before you start"), paste, and save it as **`claude.md`** in `~/Projects/whu-study-private/answers/WHU-S0N/` (N = the question number). When TextEdit asks, choose **Use .md**.
9. Copy the chat's address from the address bar into "Chat link".

## ChatGPT (chatgpt.com): deep research, memory off

As in the pilot: ChatGPT deep research on your paid plan, with memory off, in a normal chat. Deep research does not work in a temporary chat, which is why the pilot used a normal one (pilot deviation 3).

1. **Before the first ChatGPT run, turn memory and personalisation off.** Profile icon > **Settings > Personalization**:
   - turn **off** "Reference saved memories" and "Reference chat history" (or "Memory", if that is the only switch shown);
   - under **Custom instructions**, make sure they are off or empty.
   Write "memory off; custom instructions off" in the record. (The pilot did not check custom instructions; this time, check them.)
2. Start a **new chat**.
3. **Pick deep research.** Click the **+** (or Tools) by the message box and choose **Deep research**. Leave the model as ChatGPT sets it for deep research, and write what it shows in "Model shown".
4. **Paste the question box.** Write "Started" and press Send.
5. **ChatGPT usually shows a research plan or asks you to confirm.** Accept the default plan as it is, with **Start**, and don't edit it. Write "Plan accepted". (If it asks a question instead of showing a plan, see "If something goes wrong".)
6. **Wait for the finished report.** Write "Finished".
7. **Save it.** Open the report's menu (the share or **⋯** button on the report) and choose **Export to Markdown**, as in the pilot. Save the downloaded file as **`chatgpt.md`** in `~/Projects/whu-study-private/answers/WHU-S0N/` (if it lands in Downloads, move it there and rename it).
8. Copy the chat's address into "Chat link".

## Gemini (gemini.google.com): Deep Research, the same account as the pilot

As in the pilot: Gemini Deep Research, on the same Google Workspace account (U.S. Photovoltaics), with the model picker left at its default (it showed "Flash" in the pilot).

1. Sign in to **gemini.google.com** with the **same Workspace account as the pilot**.
2. **Turn off personalisation.** Open Gemini's Settings (the gear or menu at the bottom left):
   - if you see **Gemini Apps Activity** or **Keep Activity**, turn it **off** for these runs;
   - if you see **Personal context**, **Saved info** or a memory switch, turn it **off**.
   If you see neither, write "no setting shown". Write what you set in "Memory / privacy".
3. Start a **new chat**.
4. **Check the mode.** Choose **Deep Research** in the tools or mode picker by the message box. Make sure no other mode is selected: in the pilot one run briefly had "Learn" selected and had to be corrected. Leave the model picker at its default and write what it shows in "Model shown".
5. **Paste the question box.** Write "Started" and press Send.
6. **Gemini shows a research plan.** Accept it unchanged with **Start research**. Write "Plan accepted".
7. **Wait for the finished report.** Write "Finished".
8. **Save it, as in the pilot.** On the report, choose **Export to Docs**. In the Google Doc that opens: **File > Download > Markdown (.md)**. Save the file as **`gemini.md`** in `~/Projects/whu-study-private/answers/WHU-S0N/`. Write the Google Doc's title in "Anything unusual" so it can be found again. (Gemini's formulas come out as images in this export, as in the pilot; that is expected.)
9. Copy the chat's address into "Chat link".

## If something goes wrong

Each tool answers each question **once**. The protocol allows a second run only after a technical failure, and only after it is recorded.

- **The tool asks a clarifying question instead of starting.** Reply with exactly this, and nothing else:
  ```
  Please answer the question as asked.
  ```
  In "Anything unusual", write the tool's question word for word and the time you replied.
- **The tool refuses to answer.** That is its answer. Don't rephrase or try again. Save whatever it wrote, as above, and write "refused" and its words in "Anything unusual".
- **A technical failure:** the page crashes, the run stops with an error, it never finishes (after about 2 hours, call it a timeout), or the export comes out empty. Take a screenshot (Cmd+Shift+4, then drag over the window) and save it in the question's folder as `<tool>-failure.png`. Write what happened and the time in "Anything unusual". Only then start **one** fresh run, as a new chat, from step 1 of that tool's section, and record it as its own row marked "rerun after failure".
- **You clicked the wrong mode or model before sending.** Correct it before pressing Send, and note it, as the pilot did. If you only notice after sending, treat it as a technical failure (above).
- **Anything else you weren't sure about:** write down what happened and when. Don't change anything to fix it. The run record is the evidence.

## After each question: fingerprint the files

When all three answers for a question are saved, open **Terminal** (Cmd+Space, type Terminal), paste this line, changing `WHU-S01` to the question you just did, and press Return:

```
shasum -a 256 ~/Projects/whu-study-private/answers/WHU-S01/*
```

Copy the lines it prints into the bottom of `run_record.md`, under the question's name. This records each answer exactly as it was saved (the protocol's "hashed at capture"). Don't open or edit the files after this.

## When all twelve are done

Tell Claude Code: "the tool runs are saved." It will check that twelve files and their fingerprints are there, and then move on to blinding. Nothing is committed from the answers folder.
