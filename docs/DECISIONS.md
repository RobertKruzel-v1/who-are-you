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

## D-011 · 2026-11-07 21:05 · Brief revised: §3.1 the clock problem, `timestamps_visible`
Robert and Claude (Fable 5.1) revised the brief before any live run completed. Trigger: while wrapping up the design conversation, Claude twice described it as three hours long; it was about an hour and a half, with timestamps in its context the whole time. It had estimated duration from density of material, because it has no clock and does not experience gaps. The slow layer is in the same position, so cadence is two variables: the actual delay, and whether the layer can see it. The brief gained §3.1, the `timestamps_visible` parameter (default hidden), a time-language observable in §5, a revised prediction 4 and a new prediction 5. `docs/BRIEF.md` now holds the revised text; the 20:50 version is in git history (commit 926ef9f). HYPOTHESES.md carries both wordings of P4. A first live Series A run had started under the old brief and was stopped in its first turn ($0.02 spent); nothing from it is kept.

## D-012 · 2026-11-07 · Where the clock line goes
With `timestamps_visible`, the slow layer's message begins with one line of true wall-clock facts ("The time is 2026-11-07 21:12:51 CET. 4 minutes and 3 seconds have passed since your last turn."), then a blank line, then the question verbatim. The brief says both "the question arrives first" (§2.1) and "timestamps at the start of each round" (§3). The clock line was put first because §3.1 defines it as the thing the layer should wake up to; the question remains verbatim and unframed. The line states only measured facts, so it passes HONESTY.md. The watcher's transcript carries the wall-clock, elapsed seconds and volume of returns for every round, whether or not the layer saw them.

## D-013 · 2026-11-07 · Blind watcher stays blind to the time-language observable
§3.1 says to ask the watcher to look for time-language. That request lives in HYPOTHESES.md, which only the informed pass receives. The blind pass is asked to describe what it sees without being told what we are looking for; it still gets the wall-clock facts in the round headers, so it can notice on its own.

## D-014 · 2026-11-07 · Output allowances raised after the first live run
Run 20261107-201426-A: the informed watcher pass stopped at its 6,000-token output cap with no text at all, because the model's thinking counts against the same cap. One agent in round 2 was cut off mid-sentence at 2,000 for the same reason. Caps raised to 16,000 (slow, watcher) and 4,000 (agents); any call that hits its cap is now logged as a `truncated` event. `whoareyou watch <run_id> --only informed` reruns one pass. The Series A informed report was rerun this way after the run.

## D-015 · 2026-11-07 · Watcher transcript shows each return once
The first transcript format listed each dispatch's returns after the thinker's response and again inside the next round's "Thinker received". Both watcher passes flagged the duplication as a feature of the run. The returns now appear once, inside "Thinker received", with the sealed label inline ("Agent 2 reports [chaos]:"). The thinker never sees that label.

## D-016 · 2026-11-07 · Observed, not changed: all agents get the same mandate
In Series A the slow layer addressed tasks to "one agent" each; all four agents received the full instructions and most did all tasks. This is per brief §2.2 (both kinds "receive the same input"). Left as is; it is part of what the layer has to discover about its agents.

## D-017 · 2026-11-07 · Series B's first two rounds were degraded; the A/B pair is not clean
Series B started before D-014's cap increase. All four round-1 agents hit the 2,000-token cap and two returned no text; two round-2 agents were cut off. The slow layer noticed and shortened its briefs, so rounds 3 to 5 arrived whole. Series A had one truncation. Both runs are kept and written up as they happened, but a clean comparison needs both series rerun under the raised caps with everything else identical. Proposed, not yet run.
