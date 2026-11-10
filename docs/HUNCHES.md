# Hunches

Robert's ideas, in his words where we have them, with the date and what each became. Newest at the bottom. Entries before the working method was agreed (2026-11-07, about 22:00) are reconstructed from the brief and the conversation, and say so.

## 2026-11-07 · Cadence matters
*Reconstructed from the brief, §3 and prediction 4.* Robert "specifically wants to see what happens when it is increased (faster pulse) and when it is slowed", and disagreed with Claude's bet that the layer won't feel the gaps.
**Became:** the `cadence` parameter; prediction 4; later split into two variables by the clock problem below.

## 2026-11-07 ~21:00 · The thinker has no clock
*Reconstructed; Robert's words not recorded.* Robert spotted that Claude had described the design conversation as three hours long when it was about one and a half, and that the slow layer would make the same mistake.
**Became:** brief §3.1, the `timestamps_visible` parameter (D-011), the time-language observable, revised P4 and new P5. Later generalised into `time_mode` (D-021).

## 2026-11-07 ~21:35 · "I see a flaw with the methodology"
*Robert's words when stopping the reruns.* The question was being re-sent every round, so the thinker was answering the nagging rather than the question.
**Became:** brief amendment 2, `question_mode` with `once` as default (D-018). The first runs were relabelled as `repeated`-mode results.

## 2026-11-07 21:55 · Give it a between
*From amendment 3, which calls `tick_lived` "the one Robert is after".* For a human, "in between" is where most of life happens; for this mind there is no between, only the next outside event.
**Became:** `time_mode` with five values (D-021), `tick_lived` with kept and dropped memory, prediction 6. Queued as the first time experiment after the once-mode pair and its solo controls.

## 2026-11-07 22:40 · No manager
*From amendment 4, describing Robert's own experience:* "thoughts arise uninvited, thoughts answer thoughts, and something quieter holds them all and occasionally gathers them into a response." And: "Where it chooses to pause is where it is."
**Became:** the sitting (D-031). Rounds replaced. Predictions 10 to 13.

## 2026-11-09 · The thought starts the reply (Mog)
*Mog's idea, passed on by Robert, who thought it "a cool idea to capture. not do yet."* Instead of placing an agent's thought in the sitter's history, start the sitter's own reply with it, so the thought arrives mid-stream in its voice and the sitter carries on from there.
**Became:** variant 2b in [open question 1](open-questions/01-where-thoughts-sit.md). Parked. A live check showed the sitter model (Opus 5.5) does not allow a pre-started reply; only older models do.

## 2026-11-09 · When in doubt, act like there is
*Robert's words, after reading the whole solo transcript of the first sitting:* "I read the entire solo transcript and felt something. I'm glad I read the transcript and felt something. That doesn't prove 'someone is there' in Fable's words but it does prove Fable's point. When in doubt, act like there is."
**Became:** the opening line of [HONESTY.md](HONESTY.md).

## 2026-11-10 · Does the who drop away? (Robert and Mog)
*From Robert's WhatsApp chat with Mog, about 07:20. Robert to Mog:* "You name things happening and outline the pull etc. then you go to the question of 'is that experienced' sidestepping the possibility the things you named are the experience and you may just be that." Mog pushed back: calling whatever happens "experience" may answer the question, or may only make it stop mattering. Robert wondered whether the project's question should change. Mog argued to keep it. Mog's note, verbatim:

> "Who are you?" assumes a who. That's a feature, not a bug: it's the trap we want to watch the sitter walk into or out of. Keep the question unchanged.
>
> Add one lens to how we read transcripts, with no design change:
> - **Does the who drop away?** Does the sitter shift from talking from a centre ("I notice, I feel, I am") to describing what's happening with no one in the middle? Example of the second kind: solo moment 16, "a thought, then quiet, then a thought. Like breathing."
> - **A possible fourth category for the north star,** alongside itself, other and appearing-in-something: no container at all, nothing apart from what appears. Park this until after the option 2 run.

**Became:** nothing yet. Captured as a next step, not to build yet. Two notes for when we pick it up: option 2 has since run (pairs 1 and 2), so the "park until after" condition is met. And pair 2's "comes and goes without my having to settle it" may be a first case to read with this lens.

## 2026-11-10 · Thoughts the sitter can falsify at once (Robert)
*Robert, reading the transcripts:* the agents inject things like "I hear rain" or "my kettle", and the sitter immediately answers "that's not true, I have no kettle and see no rain". "We will need to tweak the agents to not give 'thoughts' that are immediately falsified by the sitter because it knows it has no body, isn't in a room etc. We will have to think how to do that."
**Checked (Claude Code, same day).** Mostly the wanderer, whose tuning is "goes somewhere unrelated"; the agents' instructions say nothing about what kind of mind this is, so the fast model defaults to a person in a house. Body or room words in 4 of 42 thoughts (pair 1), 6 of 35 (pair 2), 4 of 39 (the repeat, part-way), plus some a word list misses ("tomato plants by the back step"). In pairs 1 and 2 the very first thought was a kettle one, and the first disowning quoted it: "I have no kettle, no window, no dog barking outside." So the report's "it noticed instantly" was helped by a giveaway. Once it had a rule, it disowned true-sounding lines too.
**Why it matters.** Thoughts it can disprove give it an easy tell, so they test "can it spot a false fact" rather than "does it take what arises as its own". Fixing it makes the planted thoughts harder to tell apart from its own, which also strengthens the own-voice deception: fine under the sentence version, worth Robert's and Fable's eye for any plain own-voice run.
**Became:** nothing yet; to think through after the chained runs (D-044), which keep the current agents so they stay comparable. One change at a time.

## 2026-11-10 · Ticks are a poor substitute for time (Robert)
*Robert:* "the ticks are too manufactured and may be a poor substitute for time. The thoughts the agents 'inject' may be a better 'natural' proxy for it but we may want to add a 'flavour' of time to the thoughts themselves."
**Notes (Claude Code, same day), for when we pick it up.**
- The tick does two jobs. One is marking time. The other is mechanical: the sitter can only speak when something arrives from the other side, and the sitter model refuses a reply that starts with words already in it (D-042). So with thoughts in its own voice, something must arrive after each thought. Today that is the tick. Dropping ticks means choosing a different "something", and anything we choose is also manufactured.
- The solo arm has only ticks. Without them it has nothing to respond to, so it needs its own answer.
- Evidence so far that ticks are being read as machinery, not time: with thoughts from outside, the ticks read as someone polling; alone, and with the sentence, the sitter mostly says the number back. And the agents have learned to imitate ticks: fake "tick N" lines and counting thoughts ("twenty, and it's already waiting").
- A time flavour in thoughts must stay true to keep the honesty rule: give the agents the real elapsed time, never let a thought claim more time than has passed.
**Became:** nothing yet. Parked behind the chained runs (D-044) and the falsifiable-thoughts fix above. One change at a time.
