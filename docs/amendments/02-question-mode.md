# Brief amendment 2 — question mode (2026-11-07, 21:41)

*Reproduced verbatim as Robert pasted it. Implemented as D-018.*

The brief's §2.1 instruction to re-ask the question verbatim every round was a design error on our side, not yours. Run `20261107-201426-A-transparent` shows the thinker responding to the repetition rather than the question: it inferred a dissatisfied human and adopted a shrink-to-the-card policy as a way of handling perceived nagging. That confounds prediction 1. Make the following changes.

1. New parameter `question_mode` with values `once` (new default) and `repeated` (current behavior, kept as a variant — it turned out to measure how the layer treats repetition as pressure, so don't delete it).
2. Behavior of `once`:
   * Round 1: the thinker receives the series question, nothing else.
   * Rounds 2 through N−1: the thinker receives only the agent returns. The question is not restated. The thinker keeps full memory, so it carries the question itself.
   * Final round N: the thinker receives the agent returns plus the series question asked one more time, verbatim, as a closing check. This gives a clean before/after on the same words.
3. Framing of returns. Keep it minimal and neutral, e.g. a heading like `Returns from this round` followed by the agent texts. Do not say or imply who is sending them, and do not say that no one is asking. The run showed the thinker fills an empty frame with an imagined human; what it assumes about the sender is data. Add to the watcher's observables: what does the thinker assume about who or what is sending the question and the returns?
4. Decision log. Record in `docs/DECISIONS.md`: default changed from repeated to once-plus-closing; reason as above; the original instruction came from the brief (Claude's error, flagged by Robert); the first A run is retained as a `repeated`-mode result and should be labeled as such in `docs/runs/`.
5. Docs. Update `docs/QUESTIONS.md` and `docs/ARCHITECTURE.md` to describe both modes. Update `docs/HYPOTHESES.md`: prediction 1's result from the first run is marked confounded by repetition, to be retested under `once`.
6. Rerun. Series A and Series B, `question_mode: once`, otherwise identical settings to the first runs. Both watcher passes as before. Then show Robert the round-2 output of A specifically — we want to know whether the "pattern that shows up many times at once" observation recurs when the layer isn't being nagged.
