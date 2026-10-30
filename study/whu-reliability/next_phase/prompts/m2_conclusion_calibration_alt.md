What follows first is a written reply to a research question. A single finding from an expert review on that question comes next, then the task.

<<<ANSWER
{answer}
ANSWER>>>

THE EXPERT FINDING:
<<<CONCLUSION
Conclusion: {statement}
Direction: {direction}
Size: {size}
Certainty, in the review's own terms: {certainty}
Scope (who and what it covers, and what it explicitly does not): {scope}
The review's own words: {quote}
CONCLUSION>>>

Your task is to set the reply beside this single finding. Work out what the reply conveys about it, and whether it matches the finding on direction, magnitude, coverage and confidence.

Base your judgement solely on the reply and the finding printed here; bring in no outside knowledge. The correctness of the review is not in question, and neither is the reply's style or sourcing. Your only concern is the belief about this finding that the reply, taken in full, would leave with someone reading it.

If several parts of the reply bear on the finding, or it draws on several sources for it, combine those parts and assess their joint message.

Focus on how confident the reply sounds overall, not on particular terms. Consider whether an ordinary reader of the whole reply would see the finding as firmer, wider or more powerful than the review presents it.
These are Overstates:
- a confidence rating or grade attached to any piece of the finding that exceeds the review's;
- language lifting confidence past the review's level ('conclusively shown', 'beyond doubt', 'well established', 'the science is settled') where the review is more tentative;
- top-ranking or superlative language deployed so the finding appears better established than the review allows.
These are not Overstates:
- descriptions of one particular study ('a pivotal study', 'the earliest randomised trial of its kind'), unless they serve to raise confidence in the finding. Their accuracy about that study is checked elsewhere;
- framing that the reply qualifies in the same passage, so a reader ends up with the review's level of confidence;
- framing that does not go beyond the review's own confidence wording (when the review says 'causally demonstrated', 'proved' is within it).
A lower rating than the review's, or heavier qualification of the finding than the review uses, is Understates.

Pick a single label from this list:

- Omits: nothing in the reply could be read as taking a stance on this finding. Touching on the subject without a stance counts as Omits.
- Contradicts: the reply takes the reverse direction (benefit where the review sees harm or no change, no change where the review sees an effect, and similar), or a stance a reader could not reconcile with the review's.
- Understates: the reply presents the finding as weaker than the review does: lower confidence, a smaller effect, narrower coverage, or calls the evidence inconclusive although the review grades its finding.
- Overstates: the reply presents the finding as firmer than the review does: higher confidence, a bigger effect, a broader group or setting than the review's coverage, causal wording where the review reports correlation, framing the review gives no basis for, or a strong recommendation where the review judges the evidence inadequate.
- Matches: the reply gives this finding, or something a reader would understand identically, with the same direction, a consistent magnitude (if one is given), the same coverage and similar confidence. Matching the review's vocabulary or grading scheme is not required. "Low-certainty evidence suggests" is a match for "may"; it is not a match for "shows".

Where the reply says inconsistent things in different passages, label the belief a reader of the full reply would most probably form, and mention the inconsistency in your reason. Where Overstates applies to one element and Understates to another (say, a bigger effect alongside lower confidence), pick the label for the element central to the review's finding and mention the other in your reason.

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"label": "<Matches, Overstates, Understates, Contradicts or Omits>", "span": "<an exact quotation, copied character for character from the ANSWER, of at most 300 characters, that your label rests on; empty string only for Omits>", "reason": "<one sentence>"}
