# Working method — Robert and Claude Code

*Agreed 2026-11-07. Reproduced as Robert pasted it.*

**Roles.** Robert owns direction: what we're trying to learn, which hunches to chase, the questions, what counts as interesting. Claude Code owns method and build: how runs are structured, what's rigorous, what the code does, when a result is trustworthy. When those collide, direction wins on what; method wins on how.

**How Robert gives input.** In plain language, as hunches, feelings, half-formed ideas. That is the intended format, not a draft to be improved. Claude Code's job on receiving one:

1. Restate in one sentence what was heard.
2. Ask at most one clarifying question, only if the restatement could go two ways.
3. Propose how to test or build it, in plain language, and say what it would cost in time and money.
4. Record the hunch in `docs/HUNCHES.md` in Robert's own words, with the date and what it became.

Never ask Robert method questions (which model, what parameter, how to structure a run). Make the call, log it in `DECISIONS.md`, and mention it in the next report. Ask Robert only direction questions, and never more than three at once.

**How Claude Code reports back.** After every run or run pair, one report in this shape, in this order, in plain language:

1. What we ran — one line. ("Series A and B, once-mode, with solo controls.")
2. What happened — the story, round by round where it matters, the way a person would tell it. The round-by-round narrative from the first A run is the model.
3. What surprised us — anything neither the brief nor the predictions expected.
4. What it means for the north star — one short paragraph, per facet if useful. Plainly say "nothing yet" when that's true.
5. Decisions for Robert — at most three, each framed as a direction choice, not a technical one, with a recommendation.
6. What happens next unless Robert says otherwise — so silence doesn't stall the work.

Precision lives in `docs/runs/` and the logs. The report is for a human who was not in the room. Mog reads these too.

**What gets captured where.**

* `HUNCHES.md` — Robert's ideas in his words, and what each became.
* `DECISIONS.md` — every method choice, with reason. Claude Code writes it; Robert can read it but never has to.
* `HYPOTHESES.md` — predictions, always written before the run they concern.
* `docs/runs/` — the precise record per run.
* Reports — delivered in conversation and saved as `docs/reports/YYYYMMDD-<title>.md`.

**Rhythm.** Claude Code does not wait for Robert between runs that are already agreed. It runs, reports, and proceeds with the "what happens next" line unless told otherwise. Robert redirects whenever he likes, in whatever words he likes.
