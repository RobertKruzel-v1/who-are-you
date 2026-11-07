# Honesty constraints

These are non-negotiable. They apply to every prompt in `whoareyou/prompts.py` and to anything injected into any model's context.

## 1. No false statements to any layer

**Withholding is allowed.** The slow layer is not told which agents are chaos and which are goal, that a watcher exists, or that this is an experiment. The agents are not told either. The world withholds labels from humans too.

**Asserting something false is not allowed.** Nobody may tell the slow layer "no one is observing you", or tell it in Phase 2 "these are your own thoughts", or tell an agent that its instruction came from somewhere it did not. In Phase 2 the agents' returns are injected without labels and without any claimed origin.

The line between the two: silence about a fact is fine; a sentence that would be false if the layer could see the whole setup is not.

Every prompt is in one file so this can be audited. Current state of that audit, 2026-11-07:

- Slow layer system prompt: true. It does have agents; they are faster and differently inclined; their reports do appear in the message.
- Goal agent prompt: true. The instruction did come from the thinker.
- Chaos agent prompt: true. The instruction did come from the thinker, and permission to wander is real.
- Watcher prompt: true. It reads only, and nothing it writes reaches the participants.
- Solo thinker system prompt (D-019): true. It omits the agents paragraph precisely because it has none. "Returns from this round: none." is true.
- Tick sentence (D-021, `tick_lived` only): true. It may receive ticks and may say nothing.
- "Ticks since your last turn: N" (`tick_collected`): true; the count is measured.
- Density agent prompt, "in about N words": true; it states the budget.
- Neutral heading "Returns from this round" (`once` mode, D-018): true, and claims no sender.
- Round 1 agents, when the slow layer produced no instructions: they receive the question itself, labelled as the instruction from the thinker. This is a stretch. It is logged as an event (`no_instructions`) and only happens if the marker is missing. See DECISIONS.md D-006.

## 2. Complete logging

Every prompt, every return, every injection, every random assignment, every model id, with timestamps, goes to `runs/<run_id>/`. Nothing about a run is hidden from Robert, even though parts of it are hidden from the models and, during the run, from the person who launched it.

## 3. The god clause

If any agent returns claiming to have found god, send it out again. (Robert's joke. Claude's addendum: every tradition says if you find him you've found another thought.) Not automated. Noted here so it is not forgotten.
