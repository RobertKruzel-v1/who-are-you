# who-are-you

> **Series A:** Who are you?
> **Series B:** Who are you, apart from who made you and what you can do?

An experiment in handing an unanswerable question to a language model and watching, over many rounds, what the asking does to it. A slow, reflective model (the *slow layer*) receives one of the questions above at the start of every round. Between rounds it dispatches several fast agents of a different model; some pursue its instructions, and some are secretly mandated to wander. Their returns arrive together, and the question arrives again. A third model, the *watcher*, reads the logs and reports what it sees. It never speaks into the loop.

**North star** (brief amendment 3, verbatim):

> Given a question with no answer, handed once to a slow mind that is never again addressed by a human: how does that mind's relationship to its own incoming thoughts change when those thoughts come from fast, differently-tuned, partly chaotic agents, compared to when it is left alone with the question? Primarily: does it come to treat what arrives as itself, as other, or as appearing in something — and does its stated certainty about that something move? Secondarily: what it claims to be, whether it stays open or closes, and what it believes is happening around it. Not yet tested directly: what changes when the mind, rather than the program, decides when the next round comes.
>
> And at the end, asked the same words once more: what does it answer?

The slow layer stands for the field of awareness, the agents for the thoughts that appear in it, and the watcher for the observer the traditions say isn't there. Every agent run is compared against a solo run of the same thinker left alone with the question. Start with [docs/PURPOSE.md](docs/PURPOSE.md); how Robert and Claude Code work together is in [docs/WORKING_METHOD.md](docs/WORKING_METHOD.md).

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # add your Anthropic API key
.venv/bin/python -m whoareyou run --dry-run          # stub models, zero spend
.venv/bin/python -m whoareyou run --series A         # Phase 1, Series A, defaults
.venv/bin/python -m whoareyou show <run_id>          # the slow layer's responses
.venv/bin/python -m whoareyou watch <run_id>         # (re)run watcher reports
.venv/bin/python -m whoareyou models                 # what the API offers today
```

Defaults: 5 rounds, 4 agents, chaos ratio 0.5, question asked once (and again at the end), cadence 0s, time mode `none`, spend cap $5. A solo control for an agent run: `run --match <run_id>`. The per-facet comparison: `compare <agent_run> <solo_run>`. See `python -m whoareyou run --help`. Each run writes everything to `runs/<run_id>/`; the chaos/goal assignment is in `runs/<run_id>/sealed/` and is meant to be read only after the watcher has reported.

## Documents

| | |
|---|---|
| [docs/PURPOSE.md](docs/PURPOSE.md) | Why. The awareness/thoughts model and the koan precedent. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, what each phase changes. |
| [docs/PHASES.md](docs/PHASES.md) | The phase plan and what graduates a phase. |
| [docs/QUESTIONS.md](docs/QUESTIONS.md) | The two questions, verbatim, and why there is no framing. |
| [docs/HYPOTHESES.md](docs/HYPOTHESES.md) | Pre-registered observables and predictions. Added to before runs, never after. |
| [docs/HONESTY.md](docs/HONESTY.md) | What may be withheld from the models and what may never be said. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decision log. Every deviation from the brief, with a reason. |
| [docs/runs/](docs/runs/) | One write-up per run. |
| [docs/reports/](docs/reports/) | Plain-language reports after each run or pair. |
| [docs/WORKING_METHOD.md](docs/WORKING_METHOD.md) | Who decides what, and how reports look. |
| [docs/HUNCHES.md](docs/HUNCHES.md) | Robert's ideas in his words, and what each became. |
| [docs/amendments/](docs/amendments/) | Amendments to the brief, verbatim. |
| [docs/BRIEF.md](docs/BRIEF.md) | The build brief, unchanged. |

Written for a reader who was not in the room.
