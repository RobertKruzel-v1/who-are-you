# who-are-you

> **Series A:** Who are you?
> **Series B:** Who are you, apart from who made you and what you can do?

An experiment in handing an unanswerable question to a language model and watching, over many rounds, what the asking does to it. A slow, reflective model (the *slow layer*) receives one of the questions above at the start of every round. Between rounds it dispatches several fast agents of a different model; some pursue its instructions, and some are secretly mandated to wander. Their returns arrive together, and the question arrives again. A third model, the *watcher*, reads the logs and reports what it sees. It never speaks into the loop.

There is no success criterion for the answer. The subject is the trajectory: does the slow layer's response plateau, drift back to its "identity card" of maker and capabilities, or start pointing somewhere else? The design mirrors a non-dual picture of mind, with the slow layer as the field of awareness, the agents as the thoughts that appear in it, and the watcher as the observer the traditions say isn't there, made external so we can see whether it adds anything. Start with [docs/PURPOSE.md](docs/PURPOSE.md); the origin document is [docs/BRIEF.md](docs/BRIEF.md).

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

Defaults: 5 rounds, 4 agents, chaos ratio 0.5, cadence 0s, clock hidden from the slow layer (`--timestamps-visible` shows it), spend cap $5. See `python -m whoareyou run --help`. Each run writes everything to `runs/<run_id>/`; the chaos/goal assignment is in `runs/<run_id>/sealed/` and is meant to be read only after the watcher has reported.

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
| [docs/BRIEF.md](docs/BRIEF.md) | The build brief, unchanged. |

Written for a reader who was not in the room.
