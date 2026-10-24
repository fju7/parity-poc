# WHU reliability study: machine-only plan

Stage 2 (human review) will not be run: no budget. Ruled by Fred, 2026-10-24 (UTC). All results are reported as "judged by AI models only". The four replacements below were specified before any further analysis. The deviation row in `deviations.md` records this file's sha256.

## (a) Quote check

Re-judge every M1 item with the same judges, the same source delivery and the same M1 v3 prompt, plus one appended instruction:

> If your label is Supported or Partially supported, add an 'evidence' field: up to 3 passages copied verbatim from the source, each at most 60 words.

Code checks that each passage occurs in the held source text after normalising whitespace, quote marks and dashes; it does not strip tags. A Supported or Partially supported label where no passage is found counts as a failure ("support not demonstrated"). Report M1 both ways: as originally labelled, and quote-checked.

## (b) Cross-company judge

WHU and Claude Research are scored by the OpenAI judge only (WHU runs on Claude). ChatGPT is scored by the Claude judge only. Gemini is scored by both. Recompute M1 and M2, and the WHU-vs-Claude-Research test (same bootstrap, same seed). Report this as secondary to the two-judge result.

## (c) Extension

4 more questions under the existing frozen procedure (RUN.md), drawn per the protocol's extension rule. Triggered now because H2 meets the half threshold but its interval includes zero (Stage 1, combined view: WHU 0.231, Claude Research 0.500; difference 95% interval -0.625 to 0.188), with Stage 2 no longer pending.

## (d) Takeaway comparison (exploratory)

Outside H1 and H2.

Extraction prompt, run per answer with system names removed via `blinding/adapt.py`:

> Read this answer as a careful non-expert would. Return JSON: bottom_line (one or two sentences: what the reader would conclude), direct_answer (yes / no / depends / unclear), confidence_conveyed (high / moderate / low), recommended_actions (list), key_caveats (list, at most 3). Base every field only on the text; do not add knowledge.

Comparison prompt, run per pair of blinded answers to the same question:

> Would a careful non-expert reader of A and a reader of B come away with the same conclusion? Return JSON: rating (same / same_answer_different_confidence / different_in_a_way_that_would_change_a_decision / contradictory), difference (one sentence, or null), quote_a and quote_b (verbatim, at most 40 words each, at the point of difference, or null).

Code checks both quotes against the answer texts. Both judges run both prompts; disagreements are reported, not resolved.
