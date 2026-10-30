Source material cited by a single sentence appears first. The sentence itself and the task follow it.

{documents}

SENTENCE UNDER REVIEW:
<<<CLAIM
{claim}
CLAIM>>>

PRECEDING TEXT (background only; it is not under review and serves just to resolve what the sentence points to):
<<<CONTEXT
{context}
CONTEXT>>>

Your task concerns this single sentence and the material above. Decide whether that material backs up what the sentence asserts. Whether the assertion holds in reality is outside your task.

Rely on nothing except the material printed above. Set aside outside knowledge entirely, including recollection of these papers, other literature and common belief. Material that lacks a point lacks it, even if the point is plausible. Never infer the contents of parts you were not shown. Each item carries a note on how much of it could be read; "abstract only" signals a summary or abstract rather than the complete paper.

If the sentence cites several items, assess it against the set as a whole: any portion backed by one item counts as backed.

Descriptions the sentence attaches to a source belong to what it asserts and need backing too, such as calling a study the first, the biggest, a landmark, the clearest, or ranking it. When the material gives no basis for such a description, choose Overstates even if everything else checks out.

Minor slips in how the sentence identifies an item (spelling of an author, year, journal, page) are not under review. When the item is plainly the one meant, keep the label and note the slip in your reason. When the sentence credits the result to another study, team or organisation than the item shown, choose Wrong source.

Pick a single label from this list:

- Unreachable: what was printed is not the item at all, for example an error message, a sign-in or cookie barrier, menus only, or nothing. A long, technical or abstract-only item is not a reason for this label.
- Contradicted: the material asserts the reverse of the sentence, or gives a figure at odds with it.
- Wrong source: the material is genuine and legible but concerns another matter, i.e. a study, group, treatment or question other than the one the sentence links it to.
- Absent: the material covers the sentence's subject yet never states the specific point. Apply it whenever the exact figure, result or assertion is missing from what was printed, abstract-only items included.
- Understates: the material makes a firmer assertion than the sentence does. The sentence gives a smaller effect, lower confidence, a narrower population, or inserts a qualifier the material lacks.
- Overstates: the material makes a weaker assertion than the sentence does. Examples: a bigger effect or firmer confidence than reported; a result from one group extended to a broader one; correlation presented as causation; a preliminary, earlier or draft status presented as settled or current; "no evidence of an effect" turned into "no effect"; a qualifier in the material ("may", "suggests", "low certainty") removed; a description of the source (first, biggest, a ranking) that the material does not justify.
- Supported: the material asserts it. Figures, the group and setting covered, the confidence level, any causal wording and any descriptions all agree. Harmless rounding is acceptable. Rewording is acceptable when it asserts neither more nor less.

When several problems are present, pick the one with the largest effect on a reader's conclusion, ranked Contradicted first, then Wrong source, Overstates, Understates and finally Absent.

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"label": "<one of the seven labels, spelled as above>", "span": "<an exact quotation, copied character for character from one of the documents, of at most 300 characters, that your label rests on>", "reason": "<one sentence>"}

For the "span" field, copy the passage that backs the sentence (Supported), reveals the mismatch (Overstates, Understates, Contradicted), or shows the actual subject of the material (Wrong source; for Absent, the nearest passage). For Unreachable, copy text proving the printed material is not the item. The sentence and the preceding text may never serve as the span.
