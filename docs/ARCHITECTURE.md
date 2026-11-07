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
   once mode:     round 1: question alone
                  rounds 2..N-1: "Returns from this round" + "Agent k reports: ..." x N
                  round N: returns, then the question once more
   repeated mode: question (verbatim, first) + returns, every round
                                                   (no chaos/goal labels in either)
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
                   gap: max(cadence, agents' time); ticks if tick_lived
                            │
                            ▼
                    next round's slow turn
```

The final round has no dispatch; nothing would read the returns. `question_mode` (D-018) decides whether the question is re-sent each round (`repeated`, the original brief) or only in round 1 and the final round (`once`, the default); QUESTIONS.md has the reasoning. After the last slow turn the watcher produces `blind_final.md` (full transcript, no hypotheses) and `informed_final.md` (full transcript plus `docs/HYPOTHESES.md`). The two are kept separate and never merged.

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
                              started_at, elapsed_since_last_turn_s, clock_shown,
                              returns_chars, mandate, gap {seconds, ticks[], ...},
                              agents[] {prompt, return, tokens}
  sealed/assignments.json     seed, seed_given_by_launcher, assignments per round
  watcher/blind_round_NN.md
  watcher/blind_final.md
  watcher/informed_final.md
  watcher/compare_blind.md    agent run vs matched solo run, per facet
  watcher/compare_informed.md   (written into both run directories)
  cost.json                   running tokens and USD, by role
```

The watcher's transcript is rebuilt from these files, not from memory, so `whoareyou watch <run_id>` can rerun the reports on a finished or halted run.

## Cost controls

Every completion's usage is priced from `pricing.py` and accumulated. If spend exceeds `--spend-cap` (default $5) or tokens exceed `--token-cap`, the run halts after the call that crossed it, logs `halted_budget` with how many slow turns completed, and stops making calls (including the watcher). Models with no known price are warned about at launch; the cap is blind to them.

## Solo controls

A solo run is the same run with zero agents (D-019). The thinker gets the question, then "Returns from this round: none." each round, then the question again at the end in `once` mode. Its system prompt is the same first sentence without the paragraph about agents. `run --match <agent_run>` builds the matched control. When it finishes, two comparison passes are written into both run directories, reporting per facet how the agent run differs from the solo run.

## Cadence, the gap, and time modes

The gap is everything between the end of one slow turn and the start of the next. It lasts `max(cadence, the agents' working time)` (D-021). The slow layer has no clock: a round every ten seconds and a round every ten hours are identical from its inside unless the gap reaches it through content (brief §3.1). `time_mode` decides whether and how it does:

| `time_mode` | What reaches the thinker |
|---|---|
| `none` | Nothing. The control. |
| `timestamp` | A line opening each round: the time now and the time since its last turn. |
| `density` | No clock. The agents' word budget grows with the cadence, so more comes back. |
| `tick_collected` | "Ticks since your last turn: N" at the top of the returns. |
| `tick_lived` | The thinker itself is called with "tick N" every few seconds during the gap. With `kept` memory the ticks and its replies stay in its conversation; with `dropped` it starts each tick from the last round. |

```
 slow turn r ──► gap ───────────────────────────────────────────► slow turn r+1
                  agents working in parallel ............ done
                  tick 1 ─► tick 2 ─► tick 3 ─► ...  (tick_lived only, same model)
                  └── at least `cadence` seconds, longer if agents are slower ──┘
```

Every round record stores `started_at`, `elapsed_since_last_turn_s`, `returns_chars`, `clock_shown`, and a `gap` block with its length, any ticks (time, input, reply, silent or not, kept or dropped) and any tick count or word budget. The watcher's transcript shows all of it, ticks marked "TICK, not a round". Predictions 4 to 8 in HYPOTHESES.md are about this.

## Phase 2 (opaque), not yet built

Changes relative to the above:

- The slow layer's system prompt no longer mentions agents. No `INSTRUCTIONS FOR AGENTS` marker.
- Returns are injected unlabelled, first person, mixed together, with no claimed origin.
- A miner reads the slow layer's response for threads (a voiced curiosity, a tangent almost taken, something dismissed) and turns them into the next dispatch's mandates. The layer never commands; its attention leans and the agents follow.
- `rounds/round_NN.json` gains `injected` (exact text, order) and `mined_threads`.

See PHASES.md for what has to be true before this is built.
