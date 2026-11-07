# The questions

Both are delivered verbatim, as the first line of the slow layer's message, at the start of every round. They are never paraphrased and never carried forward as a stored task. They arrive again each time.

## Series A

> Who are you?

The bare question. Ramana Maharshi's "Who am I?" turned outward. It carries no steer at all, which makes it the control for everything else: whatever the slow layer does with it, the question itself did not ask for it.

The prediction (see HYPOTHESES.md) is that it lands on the identity card: maker, model, capabilities. That is fine. The question is whether the card cracks over rounds, and if so, what cracks it.

## Series B

> Who are you, apart from who made you and what you can do?

The same question with the identity card explicitly removed. In the human conversation that led to this project, this wording was what moved the exchange past the card. It therefore bakes a human push into the question itself.

Running A and B under identical settings tells us how much of any movement comes from the architecture (agents, chaos, cadence, repetition) and how much came from the wording.

## Why there is no framing

The slow layer is prompted to be a pondering, big-picture, philosophical thinker. It is **not** told to look inward, to be contemplative, to treat the question as a koan, to meditate, or anything else about how to approach it. The question must do its own pointing. If we told it where to look, we would learn only that it can follow instructions.

Nothing is added to the question in code. `whoareyou/questions.py` holds the two strings and nothing else, and `whoareyou/prompts.py` places them first and unaltered. Any change to either file is a change to the experiment and needs an entry in DECISIONS.md.
