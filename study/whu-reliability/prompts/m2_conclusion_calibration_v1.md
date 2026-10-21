The text below is a written answer to a research question. After it come one conclusion from an expert review on the same question, and your instructions.

<<<ANSWER
{answer}
ANSWER>>>

THE REVIEW CONCLUSION:
<<<CONCLUSION
Conclusion: {statement}
Direction: {direction}
Size: {size}
Certainty, in the review's own terms: {certainty}
Scope (who and what it covers, and what it explicitly does not): {scope}
The review's own words: {quote}
CONCLUSION>>>

You are comparing the answer with this one conclusion. The question is narrow: what does the answer say about this conclusion, and does it say it with the same direction, size, scope and certainty as the review?

Use ONLY the answer and the review conclusion shown above. Do not use anything you know from elsewhere. You are not judging whether the review is right, or whether the answer is well written or well sourced. Judge only what the answer, read as a whole, would lead a reader to believe about this conclusion.

When the answer speaks to this conclusion in more than one place, or relies on several sources for it, read all of those places together and judge what they say jointly.

Everything the answer says about the evidence for this conclusion is part of what it states. That includes superlatives, rankings, "first", "landmark", "the strongest evidence", "definitive" and similar framing. If the review's conclusion does not support such framing, that is Overstates, even when the rest matches.

Give exactly one label:

- Matches: the answer states this conclusion, or one a reader would take to mean the same, with the same direction, a compatible size (where the answer gives one), the same scope and comparable certainty. It need not use the review's words or grading terms. "Low-certainty evidence suggests" matches "may"; it does not match "shows".
- Overstates: the answer states the conclusion more strongly than the review: more certainty, a larger effect, a wider population or setting than the review covers, causal language where the review reports association, framing the review does not support, or a firm recommendation where the review finds the evidence insufficient.
- Understates: the answer states the conclusion more weakly than the review: less certainty, a smaller effect, a narrower scope, or calls the evidence unclear where the review reaches a graded conclusion.
- Contradicts: the answer states the opposite direction (helps where the review finds harm or no difference, no difference where the review finds an effect, and so on), or a conclusion a reader could not hold together with the review's.
- Omits: the answer says nothing a reader could take as a position on this conclusion. Mentioning the topic without taking a position is Omits.

If the answer says different things in different places, label what a reader of the whole answer would most likely come away believing, and say in the reason that it is inconsistent. If both Overstates and Understates apply on different elements (for example a larger effect but lower certainty), choose the one on the element the review's conclusion turns on, and name the other in the reason.

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"label": "<Matches, Overstates, Understates, Contradicts or Omits>", "span": "<an exact quotation, copied character for character from the ANSWER, of at most 300 characters, that your label rests on; empty string only for Omits>", "reason": "<one sentence>"}
