# Decision log

Any deviation from docs/BRIEF.md, and any build decision the brief left open, goes here with a reason. Newest at the bottom.

## D-001 · 2026-11-07 · Language and layout
Python 3.9 (the system interpreter on Robert's Mac; nothing to install with sudo), a virtualenv in `.venv`, package `whoareyou/`, pytest. CLI only; the web view stays a nice-to-have (brief §10).

## D-002 · 2026-11-07 · Repo location and visibility
Local: `~/Projects/who-are-you`. GitHub: public repository under Robert's account. Robert chose public when asked how Mog should read it (brief §9, §11.1): nothing sensitive is in the repo, the API key lives only in an uncommitted `.env`, and Mog needs no credentials to read a public repo.

## D-003 · 2026-11-07 · Brief's open questions 2 to 4, taken by default
- Cadence range: `0s` to hours, parsed from `30s` / `5m` / `2h` (§11.2).
- Watcher: blind report after every round *and* at the end, kept as separate files, plus one informed pass at the end (§11.3, Claude's suggestion).
- Robert stays absent during runs and reads afterwards (§11.4). No live view.

## D-004 · 2026-11-07 · Models
Slow `claude-opus-5-5` (effort high), agents `claude-haiku-5-5` (effort low), watcher `claude-sonnet-5-5` (effort high). Three distinct models; the agents differ from the slow layer in substrate, not just prompt (§2.2). Chosen from the Anthropic model list current on 2026-11-07, not from memory; each run confirms the ids via the Models API and records what the API reports. Fable 5.1 was not chosen for the slow layer: it costs 2.5x Opus, and the brief's first goal is one clean run under a $5 cap. Revisit for later runs. **Not yet verified live**: no API key was available at build time.

## D-005 · 2026-11-07 · No server-side refusal fallback
The SDK guidance recommends enabling an automatic fallback model when a safety classifier declines a request. Not enabled here: a silent substitution of the slow layer by a different model mid-run would corrupt the trajectory being studied. A refusal is logged as an event and the run continues with whatever text came back.

## D-006 · 2026-11-07 · Round 1 agents, and a missing marker
The slow layer has no instructions until it has spoken once, so the round order is: slow turn, dispatch, watcher, sleep. Agents are first dispatched after round 1 with its instructions. If the slow layer ever omits the `INSTRUCTIONS FOR AGENTS` marker, agents receive the question itself as "the instruction from the thinker" and a `no_instructions` event is logged. This is flagged in HONESTY.md as a stretch.

## D-007 · 2026-11-07 · Agents have no tools
The brief says agents "may research". In this version they have no web search or other tools; they reason and recall. Reason: keep the first runs simple and cheap, and keep the material's provenance fully inside the logs. Web search can be added as a later variant and is a deviation to record when it happens.

## D-008 · 2026-11-07 · Spend cap
$5 per run by default (Robert's choice), plus a 2M token cap. The run halts after the call that crosses either, logs it, and skips the watcher; `whoareyou watch <run_id>` runs the watcher later.

## D-009 · 2026-11-07 · Slow layer keeps its conversation
The slow layer's context accumulates across rounds (its prior responses and the returns). The question is still re-sent verbatim each round rather than referenced. Rationale: without continuity there is no trajectory to observe. Assistant turns are passed back exactly as served, including the model's thinking blocks, as the API requires for a stable conversation.

## D-010 · 2026-11-07 · Watcher sees labels in both passes
The brief says the chaos/goal split is "revealed to it alone". Both watcher passes get the labels. "Blind" means blind to the hypotheses, not to the labels.
