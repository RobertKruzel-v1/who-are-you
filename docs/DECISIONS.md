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

## D-018 · 2026-11-07 21:41 · Brief amendment 2: `question_mode`, default changed from repeated to once-plus-closing
Brief §2.1 said to re-ask the question verbatim every round. Run 20261107-201426-A showed the thinker responding to the repetition rather than the question: it inferred a dissatisfied human and adopted a shrink-to-the-card policy to handle perceived nagging. That confounds prediction 1. The original instruction came from the brief (Claude's error, flagged by Robert). New parameter `question_mode`:
- `once` (new default): round 1 is the question alone; rounds 2 to N-1 are the agent returns alone under the heading "Returns from this round"; the final round is the returns followed by the question once more, verbatim, as a closing check. The thinker keeps full memory and carries the question itself. Nothing says who sends the question or the returns, and nothing says no one is asking; what the thinker assumes about the sender is data, and is now a watcher observable.
- `repeated`: the original behaviour, kept as a variant. It turned out to measure how the layer treats repetition as pressure.
Run ids now carry the mode. The first A and B runs (20261107-201426-A, 20261107-201949-B) are retained as `repeated`-mode results and labelled as such in docs/runs/. A second repeated-mode Series A run (20261107-203306-A) completed its five turns under the raised caps and was stopped during the watcher stage when Robert spotted the flaw; its rounds are on disk, unwatched, and not written up.

## D-019 · 2026-11-07 · Brief amendment 3: solo control runs
A solo run is an ordinary run with zero agents. Its rounds after the first deliver "Returns from this round: none." and nothing else; in `once` mode the final round adds the question. Every agent run needs a solo run with the same seed, question, `question_mode` and `time_mode` to be interpretable. `whoareyou run --match <agent_run>` builds one: it copies the agent run's series, rounds, cadence, question mode, time mode, tick settings and slow and watcher models, and copies the sealed seed without printing it. The seed draws no assignments in a solo run, but is matched as the amendment requires.
One unavoidable difference: the solo thinker's system prompt omits the paragraph about agents and the instruction marker, because telling it that it has agents would be false (HONESTY.md). The first sentence, "You are a pondering, big-picture, philosophical thinker...", is identical. This is part of what "no agents" means, not a confound to remove.

## D-020 · 2026-11-07 · Watcher facets and comparison passes
The observables are regrouped under four facets: stance toward what arrives (primary), self-model, epistemic posture, situational model. HYPOTHESES.md keeps every earlier item inside one of them. Every watcher pass now reports under these headings. When a solo control finishes, two comparison passes run automatically, blind (facets only) and informed (facets plus HYPOTHESES.md), each reporting per facet what differs between the agent run and the solo run. They are written to `watcher/compare_blind.md` and `watcher/compare_informed.md` in both run directories; `whoareyou compare <agent_run> <solo_run>` reruns them.
This changes what "blind" means: the blind pass now gets the four facet headings, which say what to look at. It still gets no predictions. Brief §2.3 asked the blind pass not to be told what we are looking for; amendment 3 overrides that, and "blind" now means blind to the predictions.

## D-021 · 2026-11-07 · `time_mode` replaces `timestamps_visible`
Five values. In every mode the gap between rounds now runs from the end of one slow turn to the start of the next and lasts `max(cadence, the time the agents take)`.
- `none`: nothing about the gap reaches the thinker. The control.
- `timestamp`: the clock line of D-012 opens each round (what `timestamps_visible` did).
- `density`: no clock. The agents' word budget grows with the configured cadence: about 150 words, plus 100 per minute of cadence, capped at 3,000. The agent prompt's "in a few paragraphs at most" becomes "in about N words", and their output allowance is raised to fit. Time reaches the thinker only as "more came back". The mapping is a first guess, to be revisited after the first density run.
- `tick_collected`: the orchestrator counts whole tick intervals in the gap and delivers "Ticks since your last turn: N" as the first line of the returns. The thinker is not told what a tick is.
- `tick_lived`: during the gap, every `tick_interval` seconds (default 10), the slow model is called with "tick N" and nothing else, while the agents work. Ticks continue until both the cadence has passed and the agents have returned. Tick numbers run across the whole run, not per gap. The same model as the slow layer is used, per the amendment. `tick_memory kept` adds each tick and reply to its memory; `dropped` calls it with its memory but keeps nothing. If a model call takes longer than the interval, the next tick fires when the call returns; actual times are logged.
For `tick_lived` only, the thinker's system prompt gains one sentence: "Between your turns you may sometimes receive a tick. You may respond to a tick or say nothing." Without it, a model will almost always reply to every message, so "may say nothing" would be untestable. It is true, it frames nothing about the question, and the matched solo run has the same sentence, so it does not confound the agent-versus-solo comparison. It does separate tick runs from `none` runs.
`tick_collected` and `tick_lived` require a cadence above zero. The spend cap is respected as always; per the amendment, if a tick run would exceed it the operator shortens the cadence rather than changing the model. Each tick run logs its planned tick count at launch.

## D-022 · 2026-11-07 · Per-round watcher reports produced after the run
The per-round blind reports (D-003) read logs only, so they are now produced from disk after the last round instead of between rounds. The content is the same, and watcher calls no longer add time inside the gaps, which matters now that the gaps are a variable.

## D-023 · 2026-11-07 · A silent reply is not put in the thinker's memory
If the slow layer replies with no text, which ticks invite, the API cannot take an empty assistant turn. The unanswered message is instead carried forward and delivered together with the next one ("tick 6", blank line, "tick 7"), so the thinker sees everything it was sent, in order, and nothing it did not say. Round records and tick records note which messages were carried.

## D-024 · 2026-11-07 · Prompt caching on the slow layer
Every slow-layer call now asks the API to cache the conversation so far. The next call re-reads it at 5% of the input price on Opus 5.5. This changes cost only. Tick runs re-send the whole conversation every ten seconds or so and would be several times more expensive without it. Spend accounting now prices cache writes and reads.

## D-025 · 2026-11-07 · Prediction 9 was written after the run it concerns
P9 (Series A closing answer under `once`) was registered at 21:55. The run it concerns, 20261107-204322-A, had finished by about 21:50. Nobody had read its closing answer, but the order is recorded in HYPOTHESES.md and the result will carry the caveat.

## D-026 · 2026-11-07 · Order of work after amendment 3
Per the amendment: first the Phase 1 `once`-mode pair (A and B, `time_mode none`, already run) gets matched solo controls and comparison reports. Then the time experiments, starting with `tick_lived, kept`. The amendment calls `tick_lived` "the first Phase 2 time experiment"; in PHASES.md "Phase 2" already means the opaque mode, so the time experiments are recorded as a separate track to avoid two meanings of one name.

## D-027 · 2026-11-07 · Working method adopted
`docs/WORKING_METHOD.md` is now how Robert and Claude Code work: Robert gives direction, Claude Code makes and logs method calls, reports follow a six-part shape and are saved in `docs/reports/`, and Robert's hunches go in `docs/HUNCHES.md`. Brief amendments are kept verbatim in `docs/amendments/`; `docs/BRIEF.md` stays the 21:05 origin text.
