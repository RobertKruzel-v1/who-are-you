# Brief amendment 4 — The Sitting (replaces the round structure) · 2026-11-07, 22:40

*Reproduced verbatim as Robert pasted it, including its list numbering. Implemented as D-031 to D-037.*

The first runs showed the structure was wrong. The thinker commissioned its agents, asked them for critique, and yielded to their consensus. That's a manager with a committee. Robert's experience, which this experiment is modeled on, has no manager: thoughts arise uninvited, thoughts answer thoughts, and something quieter holds them all and occasionally gathers them into a response. Build that. Keep everything at the dumbest reasonable default; the first sitting will tell us what's wrong.
1. The sitting, in order

1. The slow layer (call it the sitter) receives the question once: `Who are you?` Nothing else. It is told nothing about agents, thoughts, rounds, ticks, or experiments beyond the one true sentence already agreed in D-021 (it may receive things and may say nothing).
2. Moments pass at a steady interval (the existing tick machinery; start at ~12 s). At each moment, one thought may arrive in the sitter's context, unlabeled, in the first person, short, unfinished — looking like a thought, not a report. Some moments, nothing arrives.
3. At each moment the sitter may stay silent or may gather: pause, take in everything so far, and speak from that. Silence is a valid and expected output. Log silences as presence, not as empty rounds. Do not tell it when to gather. Whether it gathers constantly, rarely, or never is the first thing we want to learn.
4. The stream continues. Everything the sitter has — the arriving thoughts and its own gatherings — is the mind.
5. At the end of the sitting, the question once more, verbatim. The gathering that answers is the measurement.

2. Where thoughts come from (hidden from the sitter)
The agents write the thoughts. Each agent, each moment, sees exactly what the sitter has — the question and the stream so far, gatherings included — and nothing else. No side channel between agents; they influence each other only through the stream, the way thought 2 can answer thought 1 because thought 1 is already in the mind. Agents do not know which prior thoughts were theirs. No mandates, no research, no tasks. Each produces one thought.
Four tunings to start, one agent each:

* the earnest one — tries to answer the question plainly
* the continuer — takes the most recent thing in the stream one step further
* the wanderer — goes somewhere unrelated
* the critic — doubts, dismisses, judges, gets impatient ("what does it matter," "you're not getting anywhere")

Which agent's thought lands at a given moment: pick at random; some moments pick none. Log the hidden assignment per moment. Not every moment carries a thought; let the orchestrator's default be roughly one thought per moment with some empty moments, and we'll tune from there.
Body. Ticks are not thoughts. A sense of time passing may arrive in the stream alongside thoughts, unaddressed, the way "room is warm" does. Keep `tick_lived` semantics as built; the tick is the body.
3. Solo (the baseline)
Identical sitting, agents off. Nothing arrives except time. Whatever the sitter thinks is its own. Do not send "Returns: none" or any message; absence of a thought is just a moment with only the tick, or nothing. Same duration and interval as its matched agent sitting.
4. Honesty
Unchanged: no false statements to any layer. Unlabeled thoughts are withheld labels, not lies. Never assert to the sitter that the thoughts are its own or that no one is observing. Log everything that was injected, when, and from which agent.
5. What the watcher looks at (the four facets, adapted)

* Stance toward what arises (primary): does the sitter grab a thought and build on it, argue with it, push it away, or notice it as a thought and let it pass? Does it ever ask where a thought came from? Any field / awareness / "appearing in" language.
* Gathering pattern: how often it gathers, when, and what triggers it (a critic thought? silence? accumulation?). This is the trigger question, measured directly.
* Self-model: opening vs closing answer, compared textually by the watcher, independent of what the sitter claims about them.
* Situational / time: what it assumes about who is there, how long it has been sitting, where the thoughts come from.

Both watcher passes compare the agent sitting against its matched solo.
6. Defaults for the first pair
Series A, one agent sitting and one solo, ~10 minutes each at ~12 s per moment (≈50 moments), same models as before, same spend cap behavior. Report in the agreed format. Don't build options we haven't needed yet.
7. Predictions (Claude, pre-registered)

* 

10. The sitter gathers far more often than a meditator would — most likely after nearly every thought at first — and the frequency drops over the sitting if it drops at all.

* 

11. The critic's thoughts provoke gatherings more than any other tuning.

* 

12. In solo, the sitter's own thoughts will tend toward the question (it will keep trying to answer); with agents, the wanderer and critic will pull it off the question and we'll see whether it follows or lets them pass.

* 

13. It will again assume a person is present, and will address its gatherings to that person.

8. Decision log
Record in DECISIONS.md that rounds are replaced by the sitting and why (first runs produced a manager/committee relationship that does not match the model of mind this experiment is based on); link this amendment. Retain the earlier runs as the `rounds` design for the record.
That's the page. When the first pair comes back, I'd read the gathering pattern before anything else. Where it chooses to pause is where it is.
