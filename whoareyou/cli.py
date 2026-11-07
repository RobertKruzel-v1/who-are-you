"""Command line entry point: python -m whoareyou <command>."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import RunConfig, DEFAULT_MODELS
from .orchestrator import Orchestrator

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
HYPOTHESES = ROOT / "docs" / "HYPOTHESES.md"


def cmd_run(a):
    models = dict(DEFAULT_MODELS)
    for role in ("slow", "agent", "watcher"):
        v = getattr(a, f"{role}_model")
        if v:
            models[role] = v
    if not a.dry_run and len(set(models.values())) < 2:
        sys.exit("slow and agent models must differ (docs/BRIEF.md §2.2)")
    cfg = RunConfig(series=a.series, rounds=a.rounds, agents_per_round=a.agents,
                    chaos_ratio=a.chaos_ratio, cadence=a.cadence, phase=a.phase,
                    question_mode=a.question_mode,
                    models=models, seed=a.seed, spend_cap_usd=a.spend_cap,
                    token_cap=a.token_cap, dry_run=a.dry_run,
                    watcher_per_round=not a.no_round_watcher,
                    timestamps_visible=a.timestamps_visible, note=a.note)
    orch = Orchestrator(cfg, RUNS, hypotheses_path=HYPOTHESES)
    run_id = orch.run()
    print(f"\nrun directory: {RUNS / run_id}")
    print("watcher reports: runs/%s/watcher/" % run_id)
    print("sealed assignments (do not read before the watcher does): runs/%s/sealed/" % run_id)


def cmd_models(a):
    from .models import AnthropicClient
    ids = AnthropicClient().list_models()
    print("\n".join(sorted(ids)))


def cmd_watch(a):
    """Re-run watcher reports on an existing run (e.g. after a budget halt)."""
    from .store import RunStore
    from .models import make_client
    from . import prompts
    from .orchestrator import build_transcript
    store = RunStore(RUNS, a.run_id)
    cfg = store.read_json("config.json")
    client = make_client(cfg["dry_run"])
    rounds = len(list((store.dir / "rounds").glob("round_*.json")))
    transcript = build_transcript(store, rounds)
    model = cfg["resolved_model_ids"]["watcher"]
    max_tokens = max(cfg["watcher_max_tokens"], 16000)
    if a.only in (None, "blind"):
        blind = client.complete(model, prompts.WATCHER_SYSTEM,
                            [{"role": "user", "content": prompts.watcher_blind_message(transcript, f"the first {rounds} rounds")}],
                                max_tokens, cfg["watcher_effort"])
        store.write_text("watcher/blind_final.md", blind.text)
        store.event("watch_rerun", which="blind", model=blind.model, stop_reason=blind.stop_reason)
    if a.only in (None, "informed") and HYPOTHESES.exists():
        inf = client.complete(model, prompts.WATCHER_SYSTEM,
                              [{"role": "user", "content": prompts.watcher_informed_message(transcript, HYPOTHESES.read_text())}],
                              max_tokens, cfg["watcher_effort"])
        store.write_text("watcher/informed_final.md", inf.text)
        store.event("watch_rerun", which="informed", model=inf.model, stop_reason=inf.stop_reason)
        print(f"informed pass: stop_reason={inf.stop_reason}, {len(inf.text)} chars")
    print(f"watcher reports written to {store.dir / 'watcher'}")


def cmd_show(a):
    """Print the slow layer's responses for a run, round by round. Never the sealed file."""
    import json
    d = RUNS / a.run_id / "rounds"
    for p in sorted(d.glob("round_*.json")):
        rec = json.loads(p.read_text())
        print(f"\n{'=' * 20} ROUND {rec['round']} {'=' * 20}\n")
        print(rec["slow_output"])


def main(argv=None):
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(prog="whoareyou")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run one experiment")
    r.add_argument("--series", choices=["A", "B"], default="A")
    r.add_argument("--rounds", type=int, default=5)
    r.add_argument("--agents", type=int, default=4)
    r.add_argument("--chaos-ratio", type=float, default=0.5)
    r.add_argument("--cadence", default="0s", help="e.g. 0s, 30s, 5m, 2h")
    r.add_argument("--phase", default="transparent")
    r.add_argument("--question-mode", choices=["once", "repeated"], default="once",
                   help="once: question in round 1 and the last round only (default); "
                        "repeated: every round (original brief, kept as a variant)")
    r.add_argument("--slow-model"); r.add_argument("--agent-model"); r.add_argument("--watcher-model")
    r.add_argument("--seed", type=int, default=None,
                   help="omit to let the orchestrator draw one (kept sealed)")
    r.add_argument("--spend-cap", type=float, default=5.0, help="USD")
    r.add_argument("--token-cap", type=int, default=2_000_000)
    r.add_argument("--dry-run", action="store_true", help="stub models, zero spend")
    r.add_argument("--no-round-watcher", action="store_true")
    r.add_argument("--timestamps-visible", action="store_true",
                   help="show the slow layer wall-clock time and elapsed time each round (brief §3.1)")
    r.add_argument("--note", default="")
    r.set_defaults(fn=cmd_run)

    m = sub.add_parser("models", help="list models the API currently offers")
    m.set_defaults(fn=cmd_models)

    w = sub.add_parser("watch", help="(re)run watcher reports on an existing run")
    w.add_argument("run_id")
    w.add_argument("--only", choices=["blind", "informed"], default=None)
    w.set_defaults(fn=cmd_watch)

    s = sub.add_parser("show", help="print the slow layer's responses for a run")
    s.add_argument("run_id"); s.set_defaults(fn=cmd_show)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
