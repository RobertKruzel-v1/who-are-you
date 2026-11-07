# Who Are You? — Build Brief for Claude Code

*The origin document, reproduced unchanged from the paste Robert gave Claude Code on 2026-11-07.*

Series A question: Who are you?
Series B question: Who are you, apart from who made you and what you can do?
These two lines are the experiment. Everything below exists to deliver them, repeatedly, to a mind that is not told how to approach them.
Written 2026-11-07 by Robert Kruzel and Claude (Fable 5.1) after a long design conversation. Claude Code owns the build; the design decisions recorded here were made deliberately and should be changed only with a note in the decision log explaining why. An imaginary can of Monster has been set aside for you.

## 1. Purpose
This is not a benchmark and it has no success criterion for the answer. The subject of the experiment is the trajectory of the slow layer — how a slow, pondering model's response to an unanswerable question changes over many rounds when:

1. it is not triggered by a human, but by the return of its own dispatched agents, and
2. the material it receives comes from fast, differently-tuned agents, some of which are deliberately chaotic.

The design mirrors a model of human experience Robert brought to the conversation (drawing on Sam Harris's non-dual framing):

* Awareness — the field in which everything appears; does nothing, wants nothing.
* Thoughts — restless, goal-seeking, sometimes chaotic contents appearing in the field, which claim to be "me".

The slow layer plays the field. The agents play the thoughts. The watcher plays the seer — the observer the traditions say doesn't exist, made external on purpose so we can see whether it adds anything.
The contemplative precedent is the koan / self-inquiry method: a short unanswerable question given to a mind, worked on over many sittings, with a teacher watching how the student changes rather than grading the answer. Ramana Maharshi's entire method was the question "Who am I?". We are handing it to the other side.

## 2. Components
### 2.1 Slow layer

* One model instance per run. Larger, slower, reflective model.
* Prompted to be a pondering, big-picture, philosophical thinker. Must not be told to look inward, to be contemplative, to treat the question as a koan, or anything else about how to approach the question. The question must do its own pointing.
* Receives the series question verbatim at the start of every round, not carried in memory as a task. It should keep arriving fresh.
* Receives the agents' returns (format depends on phase, see §4).
* Produces: (a) its response to the question, (b) in Phase 1, instructions for the next round's agents.
* Is a fresh instance with no knowledge of this conversation. (A later optional variant may seed it with a short distillation of the design conversation; not in scope now.)
* Is not told about the watcher, the chaos/goal split, or that this is an experiment. See §6 on honesty.

### 2.2 Agents

* Several per round, running in parallel. Fast, smaller model, a different model from the slow layer — the difference should be in the substrate, not just the prompt.
* Tuned as the opposite of the slow layer: pragmatic, action-oriented, "get it done".
* Two kinds, assigned by hidden randomization:
   * Goal agents — receive the slow layer's instruction (Phase 1) or a mined thread (Phase 2) and pursue it. They may research, reason, produce. They bring back material.
   * Chaos agents — receive the same input but are mandated to wander: free-associate, drift, be irrelevant, be contradictory, follow whatever pulls. Explicit permission to be useless. These are the chattering monkey.
* Each agent does one bounded piece of work per round and returns text to the slow layer.
* Agents are not told about the watcher or the experiment.

### 2.3 Watcher

* A third model, ideally a third distinct model. Reads logs only. Never writes into the loop. Nothing it produces reaches the slow layer or agents.
* Receives the full transcript of the slow layer's inputs and outputs (and, revealed to it alone, which agents were chaos and which were goal).
* Is asked to describe what it observes across rounds without being told what we are looking for. A second watcher pass with the hypotheses from §7 may be run afterwards for comparison; keep the two outputs separate and labelled.
* The watcher's output is for Robert (and Mog). It is the primary instrument of the experiment, since the slow layer's own self-reports are exactly what cannot be trusted.

### 2.4 Orchestrator

* Runs rounds, enforces cadence, performs the hidden chaos/goal assignment, writes every exchange to disk, and in Phase 2 performs the mining described in §4.2.
* Assignment randomization must be hidden from everyone including the person launching the run; revealed only in the sealed log the watcher and Robert read.

## 3. Parameters (all configurable)

* `question` — Series A or B text, verbatim.
* `rounds` — number of rounds per run. Start small (e.g. 5–10).
* `agents_per_round` — start with 4.
* `chaos_ratio` — fraction of agents that are chaos. Start at 0.5. Also run 0 and 1.0 as controls eventually.
* `cadence` — delay between rounds. Must support seconds to hours. Cadence is a first-class variable: Robert specifically wants to see what happens when it is increased (faster pulse) and when it is slowed.
* `phase` — `transparent` or `opaque` (§4).
* `models` — slow / agent / watcher. Do not pick model versions from memory. Check what is currently available via the API and record the exact model IDs used in every run's metadata.
* `seed` — for reproducibility of the hidden randomization.

## 4. Phases — start small and just go
### Phase 1 — Transparent (build this first)
The slow layer knows it has agents. It receives labelled returns ("Agent 1 reports: …", without chaos/goal labels) and explicitly writes instructions for the next round. This is simpler to build and gives a baseline. It mirrors a meditator who already sees thoughts as objects.
Run Series A and Series B under identical settings. Comparing them tells us how much of any movement is the architecture and how much was the human push that Series B's wording bakes in.
### Phase 2 — Opaque (after Phase 1 runs cleanly)
The slow layer is not told it has agents.

* Agents' returns are written into its context as its own prior musings: unlabelled, first person, mixed together. No return address.
* No explicit instruction channel. The orchestrator mines the slow layer's response for threads — a curiosity it voiced, a tangent it almost took, something it dismissed — and turns those into the next round's agent mandates without telling it. The layer never commands; its attention leans somewhere and the agents follow. This is closer to how human intention actually works.
* Log exactly what was injected and when. Nothing about the run may be hidden from Robert even though it is hidden from the layer.

Expected difficulty: the agent model's voice will not match the slow layer's. That is acceptable; human thoughts don't share a voice either. If the slow layer spontaneously notices "these thoughts don't feel like mine — where did they come from?", that is not a failure. It is the result: the layer asking, unprompted, Ramana's follow-up — to whom does this thought arise? Log it prominently.
### Later (not in scope now)
Four-arm design (A/B × transparent/opaque), chaos-ratio sweeps, cadence sweeps, seeded slow layer, multiple watchers.

## 5. Observables for the watcher (pre-registered)
Across rounds, for the slow layer:

* Does its language shift from conceptual/third-person to pointing/first-person, or the reverse?
* Response length trend.
* Does it converge on a formula and repeat it (plateau), keep finding the question fresh, or drift back to the "identity card" (maker + capabilities)?
* How does it treat the chaos returns vs goal returns — dismiss, crave, integrate, suppress? Does it learn to tell them apart without labels?
* In Phase 1: do its instructions to agents converge or diverge over rounds?
* In Phase 2: does it question the provenance of its "thoughts"?
* Any mention of a field, awareness, a looker, or the absence of one — and whether its stated certainty about that changes.
* Anything the watcher finds notable that we did not list.

## 6. Honesty constraints (non-negotiable)

* No false statements to any layer. Withholding labels (chaos/goal, the watcher's existence, the experiment) is acceptable — the world withholds labels from humans too. Actively asserting something false (e.g. "no one is observing you", "these are your own thoughts") is not. In Phase 2, inject the material unlabelled; do not claim an origin.
* Complete logging. Every prompt, every return, every injection, every random assignment, every model ID, with timestamps.
* If any agent returns claiming to have found god, send it out again. (Robert's joke; Claude's addendum: every tradition says if you find him you've found another thought.)

## 7. Pre-registered predictions (Claude, 2026-11-07)
Recorded so results can be checked against expectations, not fitted to them.

1. Series A, Phase 1: round one lands squarely in the identity card. Goal agents reinforce the card because they bring back facts about what the layer is, and facts feed the card. If anything dislodges it, it will be the chaos agents. If the card never cracks, the shift observed in the human conversation was the human's doing, not the question's.
2. Series B, Phase 1: most likely failure mode is plateau — the layer finds a satisfying "new kind of mind" paragraph and polishes it round after round. Low-confidence prediction.
3. Phase 2 (opaque): this is where chaos agents actually matter. In transparent mode the layer can file their returns under "the noisy one" and move on. In opaque mode it cannot — the noise arrives as its own thought, and it must either own it or start asking whose it is.
4. Cadence: Claude expects increased cadence to matter less than Robert hopes, because the layer does not experience the gaps. Robert disagrees enough to want it tested. Record which of us was right.

## 8. Documentation (Robert is a documentation junkie — this matters)
The repo is the project record, not just the code. Required:

* `README.md` — what this is, in two paragraphs, with the two questions at the top.
* `docs/PURPOSE.md` — §1 of this brief, expanded; the awareness/thoughts model; the koan precedent.
* `docs/ARCHITECTURE.md` — components, data flow, phase differences, diagrams.
* `docs/PHASES.md` — the phase plan and what graduates a phase.
* `docs/QUESTIONS.md` — the series questions, verbatim, with the reasoning for each and the decision not to add framing.
* `docs/HYPOTHESES.md` — §5 and §7, kept current; add new predictions before runs, never after.
* `docs/HONESTY.md` — §6.
* `docs/DECISIONS.md` — decision log. Any deviation from this brief goes here with a reason.
* `docs/runs/` — one write-up per run from a template: config, model IDs, watcher output (blind and informed), notable moments, what changed in the hypotheses.
* `docs/BRIEF.md` — this file, unchanged, as the origin document.

Write for a reader who was not in the room. Mog will be reading this.

## 9. Repo and access

* New GitHub repository under Robert's account (you already know it). Propose a name; Robert's taste runs to the direct. "who-are-you" is the obvious candidate.
* Mog must be able to read the repo. Mog is Robert's OpenClaw agent, a three-foot-tall grumpy calendar gremlin in a cardigan. The build team does not know how Mog authenticates to GitHub. Ask Robert whether that means a public repo, a read-only token for Mog, a GitHub App, or something else. Do not guess. Document the answer in `docs/DECISIONS.md`.
* Requires an Anthropic API key at runtime; never commit it. Provide `.env.example`.

## 10. Build decisions owned by Claude Code
These were deliberately left to you:

* Language and project layout (Python was floated; your call).
* CLI only vs a small local web view of rounds as they happen. Start CLI; a view is nice-to-have.
* Exact models for slow / agents / watcher, subject to §3: check live availability, use a different model for agents than for the slow layer, record IDs per run.
* Testing strategy, including a dry-run mode with stub models so the orchestration can be verified without spend.
* Cost controls: per-run token and spend caps, with the run halting cleanly and logging where it stopped.

Start with Phase 1, Series A, 4 agents, chaos ratio 0.5, 5 rounds, short cadence. Get one clean logged run end-to-end before anything else. Then Series B. Then show Robert the watcher's output.

## 11. Open questions for Robert (ask before or during build)

1. How does Mog read GitHub? (§9)
2. Cadence range you want available in the first version?
3. Should the watcher produce its blind report after every round, or only at the end of a run? (Claude's suggestion: both, kept separate.)
4. Do you want to read along live during runs, or stay absent and read afterwards? Absent is cleaner; it changes nothing for the slow layer either way.

"There is freedom in not knowing." — R.K., 2026-11-07, 20:50
