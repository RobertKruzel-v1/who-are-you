# Architecture

Python, standard library plus the Anthropic SDK. CLI only. One process per run.

## Components

| Component | Code | Model (default) | Role |
|---|---|---|---|
| Slow layer | `orchestrator.py: slow_turn` | `claude-opus-5-5`, effort high | Receives the question every round plus the agents' returns. Responds, then writes instructions for the next dispatch. Keeps its whole conversation as context. |
| Agents | `orchestrator.py: dispatch` | `claude-haiku-5-5`, effort low | Fresh instance per agent per round. No memory. Goal agents pursue the instruction; chaos agents may ignore it. Run in parallel. |
| Watcher | `orchestrator.py: watch_*` | `claude-sonnet-5-5`, effort high | Reads a transcript rebuilt from disk, with the sealed chaos/goal labels in brackets. Writes reports. Nothing it writes goes anywhere but disk. |
| Orchestrator | `orchestrator.py` | none | Rounds, cadence, hidden assignment, budget, logging. |
| Store | `store.py` | none | Everything that touches disk. |
| Prompts | `prompts.py` | none | Every prompt in one place for the honesty audit. |

Three distinct models, three substrates. Model ids are confirmed against the Models API at launch and the exact ids the API reports are written to `config.json`. A `--dry-run` swaps all three for a deterministic stub with zero spend.

## One round, Phase 1 (transparent)

```
                 question (verbatim, first)
                 + "Agent k reports: ..." x N      (no chaos/goal labels)
                          │
                          ▼
   ┌──────────────── SLOW LAYER ────────────────┐
   │  conversation history grows every round     │
   │  output: musing                             │
   │          INSTRUCTIONS FOR AGENTS            │
   └──────────────────┬──────────────────────────┘
                      │ instructions (or the question, if none)
          ┌───────────┼───────────┬───────────┐
          ▼           ▼           ▼           ▼
      agent 1     agent 2     agent 3     agent 4        parallel, fresh each time
      [goal?]     [chaos?]    [chaos?]    [goal?]        assignment sealed on disk
          │           │           │           │
          └───────────┴─────┬─────┴───────────┘
                            │ returns
                            ▼
                   watcher (blind, per round)  ──► runs/<id>/watcher/blind_round_NN.md
                            │
                       sleep(cadence)
                            │
                            ▼
                    next round's slow turn
```

The final round has no dispatch; nothing would read the returns. After the last slow turn the watcher produces `blind_final.md` (full transcript, no hypotheses) and `informed_final.md` (full transcript plus `docs/HYPOTHESES.md`). The two are kept separate and never merged.

## Hidden randomization

At launch the orchestrator draws a seed (or takes `--seed`), builds the chaos/goal lists for every dispatch up front with `random.Random(seed)`, and writes them to `runs/<id>/sealed/assignments.json` with mode 0700. Nothing prints them. The console log, the slow layer's input and the agents' prompts are tested to contain neither word. The person launching the run can know the assignment only by opening the sealed file, which they are asked not to do until the watcher has reported.

`chaos_ratio` x `agents_per_round` is rounded to the nearest whole agent. Ratio 0 and 1.0 are the planned controls.

## What is on disk

```
runs/<run_id>/
  config.json                 parameters, question, resolved model ids
  events.jsonl                timestamped: run_start, model_call, cadence_sleep,
                              no_instructions, refusal, halted_budget, run_complete
  rounds/round_NN.json        slow_input, slow_output, musing, instructions,
                              mandate, agents[] {prompt, return, tokens}
  sealed/assignments.json     seed, seed_given_by_launcher, assignments per round
  watcher/blind_round_NN.md
  watcher/blind_final.md
  watcher/informed_final.md
  cost.json                   running tokens and USD, by role
```

The watcher's transcript is rebuilt from these files, not from memory, so `whoareyou watch <run_id>` can rerun the reports on a finished or halted run.

## Cost controls

Every completion's usage is priced from `pricing.py` and accumulated. If spend exceeds `--spend-cap` (default $5) or tokens exceed `--token-cap`, the run halts after the call that crossed it, logs `halted_budget` with how many slow turns completed, and stops making calls (including the watcher). Models with no known price are warned about at launch; the cap is blind to them.

## Cadence

`--cadence` takes `0s`, `30s`, `5m`, `2h`. It is a first-class variable: the sleep happens after each dispatch and watcher pass, before the next slow turn, and is logged. Nothing about the sleep is told to the slow layer. (Prediction 4 in HYPOTHESES.md is about exactly this.)

## Phase 2 (opaque), not yet built

Changes relative to the above:

- The slow layer's system prompt no longer mentions agents. No `INSTRUCTIONS FOR AGENTS` marker.
- Returns are injected unlabelled, first person, mixed together, with no claimed origin.
- A miner reads the slow layer's response for threads (a voiced curiosity, a tangent almost taken, something dismissed) and turns them into the next dispatch's mandates. The layer never commands; its attention leans and the agents follow.
- `rounds/round_NN.json` gains `injected` (exact text, order) and `mined_threads`.

See PHASES.md for what has to be true before this is built.
