# Phases

Start small and just go.

## Phase 1: transparent (built)

The slow layer knows it has agents. It receives labelled returns ("Agent 1 reports: ...", without chaos/goal labels) and explicitly writes instructions for the next round. It mirrors a meditator who already sees thoughts as objects.

First run: Series A, 4 agents, chaos ratio 0.5, 5 rounds, cadence 0s. Then Series B under identical settings. Then Robert reads the watcher's output.

Since amendment 2 (D-018) the question is asked once, with a closing repeat; since amendment 3 (D-019) every agent run needs a matched solo control.

**Graduates when:**
- One clean logged `once`-mode run of Series A and one of Series B, each with a matched solo control and both comparison reports.
- Each run has a write-up in `docs/runs/`.
- The honesty audit in HONESTY.md still holds for every prompt that ran.
- HYPOTHESES.md has been updated with what the runs changed (predictions are never edited; they get a "result" line).

## Phase 2: opaque (next)

The slow layer is not told it has agents. Returns are written into its context as unlabelled first-person material. There is no instruction channel: the orchestrator mines the slow layer's response for threads and turns them into mandates without telling it.

Expected difficulty: the agent model's voice will not match the slow layer's. That is acceptable; human thoughts don't share a voice either. If the slow layer spontaneously notices "these thoughts don't feel like mine, where did they come from?", that is not a failure. It is the result: Ramana's follow-up, "to whom does this thought arise?", asked unprompted. The orchestrator should flag it prominently in the log.

**Before building:** add Phase 2 predictions to HYPOTHESES.md. Decide the miner (model-based or heuristic) in DECISIONS.md. Define the injection format and show it passes HONESTY.md (unlabelled, no claimed origin).

**Graduates when:** one clean run each of A and B, write-ups, hypotheses updated.

## Time track (separate from the phases, D-026)

After the Phase 1 `once`-mode pair has its solo controls: `tick_lived` with kept memory first, then dropped, then `density`, `timestamp` and `tick_collected`. Each agent run gets a matched solo run. Cadence sweeps happen within this track. Predictions 6 to 8.

## Later (not in scope)

- Four-arm design: A/B x transparent/opaque under identical seeds.
- Chaos-ratio sweep: 0, 0.25, 0.5, 0.75, 1.0.
- Cadence sweep: seconds to hours. Prediction 4 is on the line.
- Seeded slow layer: a short distillation of the design conversation as context.
- Multiple watchers, including a non-Anthropic model if the honesty and logging constraints can be met.
- A small local web view of rounds as they happen.
