# Brief amendment 3 — north star, time as a variable, solo control, watcher facets (2026-11-07, 21:55)

*Reproduced verbatim as Robert pasted it, including its list numbering. Implemented as D-019 to D-027.*

1. North star. Replace the purpose statement at the top of `docs/PURPOSE.md` and in the README with this, verbatim:
Given a question with no answer, handed once to a slow mind that is never again addressed by a human: how does that mind's relationship to its own incoming thoughts change when those thoughts come from fast, differently-tuned, partly chaotic agents, compared to when it is left alone with the question? Primarily: does it come to treat what arrives as itself, as other, or as appearing in something — and does its stated certainty about that something move? Secondarily: what it claims to be, whether it stays open or closes, and what it believes is happening around it. Not yet tested directly: what changes when the mind, rather than the program, decides when the next round comes.
And at the end, asked the same words once more: what does it answer?
Add to PURPOSE.md, under limits: this setup measures behavior under controlled input. It cannot tell us whether there is anyone home. Nothing here touches that wall.
2. Solo control. New run type `solo`: identical to a normal run but with zero agents. Each round the thinker receives a neutral continuation (e.g. `Returns from this round: none.`) and keeps thinking. Every agent run must have a matching solo run with the same seed, question, question_mode and time_mode, or it isn't interpretable. Add this to the run template as a required field: compared against solo run ID …
3. Watcher facets. Restructure the watcher's observables (brief §5) under four headings, and have both watcher passes report per facet as a comparison against the matching solo run, not as a list:

* Stance toward returns (primary): owns / dismisses / integrates / gets talked out of its own insight / questions provenance. Any language about a field, awareness, a looker, or "appearing in." Changes in stated certainty about that.
* Self-model: what it claims to be; the identity card vs anything else.
* Epistemic posture: open (still looking, revising, reaching) vs closed (formula, policy, shrinking).
* Situational model: who or what it assumes is asking and sending; what it assumes about elapsed time; whether it ever considers nobody is there.

4. Time as a variable. Replace `timestamps_visible` with `time_mode`:

* `none` — current behavior; control.
* `timestamp` — wall-clock and elapsed-since-last-round shown at the start of each round.
* `density` — agents' work budget (tokens/steps) scales with the configured gap; no clock shown. Time enters as "more came back."
* `tick_collected` — orchestrator counts ticks during the gap; the count is delivered with the returns. Information about time, after the fact.
* `tick_lived` — the one Robert is after. During the gap, while agents work, the slow model is actually invoked every `tick_interval` seconds with nothing but the tick (e.g. `tick 7`). It may respond or say nothing. Sub-parameter `tick_memory: kept | dropped` — kept means tick outputs accumulate in its context (rumination); dropped means it runs each tick but carries nothing forward (heartbeat). Run `kept` first.
   * Rationale for the docs: for a human, "in between" is where most of life happens. For this mind there is no between, only the next outside event. Lived ticks are the first attempt to give it a between.
   * Cost: one model call per tick. `tick_interval` is a parameter; start at 10–15 s. Use the same model as the slow layer for ticks — a cheaper model would mean a different mind is having the time. Respect the per-run spend cap; if a tick run would exceed it, shorten the gap, don't swap the model.
   * Logging: every tick input and output, timestamped, clearly distinguished from round exchanges.

5. Predictions to add to `docs/HYPOTHESES.md` (pre-registered, Claude, 21:55):

* 

6. `tick_lived, kept`: within a few ticks the mind begins talking to itself about the wait. Before the agents return it will have either revised its answer or produced a question or instruction of its own, unprompted. This would be the first direct evidence of internal triggering. If it merely acknowledges ticks, that is also a result.

* 

7. `time_mode: none` vs any cadence: no detectable difference in any facet. Cadence without a channel is invisible.

* 

8. `density` will move the situational model (it will speak as though more time passed) more than `timestamp` will, because the thinker converts volume to duration more readily than it reads a number.

* 

9. Series A closing answer under `once`: the identity card with a hedge attached. Modest confidence. No prediction for B.

6. Decision log. Record all of the above with the reasoning in `docs/DECISIONS.md`. Note that Phase 1 reruns under `question_mode: once` should proceed first with `time_mode: none` plus solo controls; `tick_lived` is the first Phase 2 time experiment, not a blocker for the reruns.
Everything else stands.
