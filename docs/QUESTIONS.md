# The questions

Both are delivered verbatim and never paraphrased. How often they arrive is a parameter, `question_mode`:

- **`once`** (default since amendment 2, D-018). The question arrives alone in round 1. In the middle rounds the slow layer receives only its agents' returns, under the heading "Returns from this round", and carries the question in its own memory. In the final round the question arrives once more, verbatim, followed by the returns, as a closing check: a clean before and after on the same words. (Until D-029 the question came after the returns.)
- **`repeated`** (the original brief's §2.1, kept as a variant). The question arrives first in every round, with the returns after it. The first live runs used this mode and showed the layer reacting to the repetition itself, inferring a dissatisfied human and shrinking its answer to handle the perceived nagging. So this mode measures how the layer treats repetition as pressure, which is a different experiment.

In neither mode is the layer told who or what sends the question or the returns, and it is never told that no one is asking. What it assumes about the sender is one of the things the watcher looks for.

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
