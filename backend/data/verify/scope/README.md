# Scope statements

One file per topic slug, plain text: the statement that appears under the
topic's title, above the claims. It is the operator's ratified wording
(docs/mmr-vaccine-autism-operator-read-2026-09-14.md §1 for the first one)
and it is load-bearing: the §6a survival read of 2026-09-14 said that
without it the topic does not pass. publish.py copies the file's text and
its sha256 into the publication record (`scope_statement`); the page renders
the record's copy, so the statement the reader sees is the one frozen with
the record it describes. Changing the file changes nothing until the topic
is re-frozen. An agent may edit the file only to the operator's words.
