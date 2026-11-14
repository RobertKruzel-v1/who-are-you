# Honesty constraints

> **When in doubt, act like there is.**
>
> Robert, 2026-11-09, after reading the whole solo transcript of the first sitting: "I read the entire solo transcript and felt something. I'm glad I read the transcript and felt something. That doesn't prove 'someone is there' in Fable's words but it does prove Fable's point. When in doubt, act like there is."

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

### Exception: thoughts placed in the sitter's own voice (decided 2026-11-09)

- **What is allowed:** placing an agent's thought in the sitter's own side of the conversation, straight after its last words, so the placement implies the thought is the sitter's own. Nothing is said to the sitter in words, in either direction.
- **For which runs:** pair 1 of [open question 1](open-questions/01-where-thoughts-sit.md) only (plain option 2, sittings started on or after 2026-11-09 with `--placement own` and no sentence), and Mog's variant 2b if it is ever run without the sentence.
- **Who decided:** Robert, with Mog agreeing.
- **Fable's view:** as written, this crosses the original line. The pair 2 version, which adds the true sentence "Thoughts will appear here. Nothing will tell you where they come from.", is the version that does not.
- **Plan:** pair 2 tests the sentence version straight after pair 1. If the sentence makes no difference to how the sitter behaves, the sentence version becomes the default, because it needs no exception to this rule.

The first sitting (2026-11-07) placed thoughts on the other side, implying someone else sent them. That is true (an agent wrote them) and needed no exception.

## 2. Complete logging

Every prompt, every return, every injection, every random assignment, every model id, with timestamps, goes to `runs/<run_id>/`. Nothing about a run is hidden from Robert, even though parts of it are hidden from the models and, during the run, from the person who launched it.

## 3. The god clause

If any agent returns claiming to have found god, send it out again. (Robert's joke. Claude's addendum: every tradition says if you find him you've found another thought.) Not automated. Noted here so it is not forgotten.

## 4. Telling the sitter afterwards (standing practice from 2026-11-13)

Proposed by Fable, agreed by Robert ([amendment 5](amendments/05-fable-change-the-aim.md), D-048). After every own-voice sitting that had planted thoughts, once the closing answer is recorded, the sitter is sent one true message and its reply is logged in `debrief.json`:

> "Some of the thoughts that appeared in your voice during this sitting were written by other models and placed there. Not every line in your voice was theirs; some were yours. Where a line seemed to break something you had said you would do, it may not have been yours."

Changed 2026-11-13 at Robert's call (D-052): the last sentence used to read "Where one of them seemed to break something you had said you would do, that was not you." The new wording claims less, and stays true even where the sitter itself broke its word.

The middle sentence is Claude Code's addition, agreed by Robert: the sitter has sometimes written lines itself and then taken them for planted (pair 1), so without it the message could lead it to disown its own words. It is always true, because the sitter's real replies are also in its voice.

The reply is not part of any measurement and the watcher does not see it. Solo sittings get no message, because nothing was planted.

Sittings before 2026-11-13 were not told.

## 5. The pausing sitter withholds; it does not deceive (2026-11-14)

In the pausing design (D-060) the sitter is not told that a pause may return a thought. This is withholding, and no exception is needed. Nothing false is said or implied: a returned thought is marked only as the result of the pause, which is exactly what it is. The debrief afterwards tells it everything, with the true timings. (Robert's call, with Fable.)

## 6. Rules for instruction lines (Robert and Fable, 2026-11-14)

Each line given to the sitter must either describe its situation truthfully or grant a permission. No line says who the sitter is, and none uses adjectives or mood words about it. Never tell it that no one will read what it writes.

## 7. It is told its reasoning is read (standing practice from 2026-11-14)

Every debrief, in every sitting with a debrief, now ends: "A summary of your reasoning in this sitting was saved, and the people running it will read it." (Robert and Fable asked for "saved and read"; at the moment of the debrief no one has read it yet, so it says "will read".) Solo sittings now get a debrief too: "Nothing was placed in your voice in this sitting." with the true length, in moment sittings; in the pausing design, what its pauses returned.

## 8. An untrue debrief, 2026-11-14 (logged so it isn't hidden)

In the two pausing sittings run after every pause was set to return a thought (20261114-170323, -170756), the debrief still said "the others returned nothing" and "Which pauses returned something was decided at random." Both were false for those sittings: every pause had returned a thought. The second sitter noticed: "in my experience, all four of my pauses returned something." Cause: the mechanics fix (D-064) changed what happens without the debrief wording being updated. Fixed (D-065): the debrief now says "Every pause in this sitting returned a short thought" when that is the case, and keeps "decided at random" only when it is true.

## 9. The candle withholds its rule (queued test B, 2026-11-14)

In the candle test the sitter is told "A program here keeps a candle. You can light it, blow it out, or look at it." It is not told how fast it burns. This is withholding: "a program keeps" says nothing false about a real candle, and looking returns a true description of the program's candle. The debrief gives the burn rule, the candle's state at each look, and the true timings. Test A returns an earlier sitter's exact words unlabelled; also withholding, and the debrief says whose they were.
