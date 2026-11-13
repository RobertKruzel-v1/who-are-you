"""Command line entry point: python -m whoareyou <command>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import RunConfig, DEFAULT_MODELS
from .orchestrator import Orchestrator

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
HYPOTHESES = ROOT / "docs" / "HYPOTHESES.md"


def _matched_settings(run_id: str) -> dict:
    """Read an agent run's settings and sealed seed so a solo control can match
    it exactly. The seed is copied, never printed."""
    d = RUNS / run_id
    cfg = json.loads((d / "config.json").read_text())
    sealed = json.loads((d / "sealed" / "assignments.json").read_text())
    tm = cfg.get("time_mode") or ("timestamp" if cfg.get("timestamps_visible") else "none")
    return {
        "series": cfg["series"], "rounds": cfg["rounds"], "cadence": cfg["cadence"],
        "question_mode": cfg.get("question_mode", "repeated"), "time_mode": tm,
        "tick_interval": cfg.get("tick_interval", 10.0),
        "tick_memory": cfg.get("tick_memory", "kept"),
        "seed": sealed["seed"],
        "slow_model": cfg["models"]["slow"], "watcher_model": cfg["models"]["watcher"],
        "agents_per_round": cfg.get("agents_per_round", 4),
        "chaos_ratio": cfg.get("chaos_ratio", 0.5),
        "matched_gaps": _gap_lengths(d),
    }


def _gap_lengths(run_dir: Path) -> list:
    """Actual gap per round of an agent run: from the gap record, or for runs
    made before D-021, the time between turns."""
    out = []
    for p in sorted((run_dir / "rounds").glob("round_*.json")):
        rec = json.loads(p.read_text())
        if "gap" in rec:
            out.append(rec["gap"]["seconds"])
        else:
            nxt = run_dir / "rounds" / f"round_{rec['round'] + 1:02d}.json"
            if nxt.exists():
                out.append(json.loads(nxt.read_text()).get("elapsed_since_last_turn_s") or 0)
    return out


def cmd_run(a):
    models = dict(DEFAULT_MODELS)
    for role in ("slow", "agent", "watcher"):
        v = getattr(a, f"{role}_model")
        if v:
            models[role] = v
    fields = dict(series=a.series, rounds=a.rounds, agents_per_round=a.agents,
                  chaos_ratio=a.chaos_ratio, cadence=a.cadence, phase=a.phase,
                  question_mode=a.question_mode, time_mode=a.time_mode,
                  tick_interval=a.tick_interval, tick_memory=a.tick_memory,
                  solo=a.solo, seed=a.seed)
    if a.match:
        m = _matched_settings(a.match)
        for k in ("series", "rounds", "cadence", "question_mode", "time_mode",
                  "tick_interval", "tick_memory", "seed", "agents_per_round", "chaos_ratio"):
            fields[k] = m[k]
        models["slow"], models["watcher"] = m["slow_model"], m["watcher_model"]
        fields["solo"] = True
        fields["matched_gaps"] = m["matched_gaps"]
        print(f"solo control matched to {a.match}: series {m['series']}, "
              f"question {m['question_mode']}, time {m['time_mode']}, "
              f"{m['rounds']} rounds, cadence {m['cadence']}, same seed (sealed), "
              f"gaps {[round(x) for x in m['matched_gaps']]} s")
    if not a.dry_run and not fields["solo"] and models["slow"] == models["agent"]:
        sys.exit("slow and agent models must differ (docs/BRIEF.md §2.2)")
    cfg = RunConfig(models=models, spend_cap_usd=a.spend_cap, token_cap=a.token_cap,
                    dry_run=a.dry_run, watcher_per_round=not a.no_round_watcher,
                    matched_run=a.match, note=a.note, **fields)
    orch = Orchestrator(cfg, RUNS, hypotheses_path=HYPOTHESES)
    run_id = orch.run()
    print(f"\nrun directory: {RUNS / run_id}")
    print("watcher reports: runs/%s/watcher/" % run_id)
    print("sealed assignments (do not read before the watcher does): runs/%s/sealed/" % run_id)


def cmd_compare(a):
    """(Re)run the per-facet comparison of an agent run against its solo control."""
    from .models import make_client
    from .orchestrator import compare_runs, Orchestrator  # noqa
    cfg = json.loads((RUNS / a.agent_run / "config.json").read_text())
    client = make_client(cfg.get("dry_run", False))

    class _Shim:  # minimal stand-in so compare_runs can price and log calls
        pass
    from .orchestrator import Budget
    from .store import RunStore
    from .config import RunConfig as _RC
    shim = _Shim()
    shim.hypotheses_path = HYPOTHESES
    shim.cfg = _RC(watcher_max_tokens=16000, watcher_effort="high")
    shim.budget = Budget(5.0, 2_000_000)
    shim.store = RunStore(RUNS, a.solo_run)
    shim.model_ids = {"watcher": cfg["resolved_model_ids"]["watcher"]}
    shim.client = client
    shim.log = print
    shim._call = lambda *args, **kw: Orchestrator._call(shim, *args, **kw)
    written = compare_runs(shim, RUNS / a.agent_run, RUNS / a.solo_run)
    print(f"written: {written} in both run directories; watcher spend ${shim.budget.usd:.2f}")


def cmd_sit(a):
    """The sitting (brief amendment 4)."""
    from .sitting import SitConfig, Sitting, matched_settings
    models = dict(DEFAULT_MODELS)
    fields = dict(series=a.series, moments=a.moments, interval=a.interval,
                  empty_prob=a.empty_prob, solo=a.solo, seed=a.seed,
                  placement=a.placement, sentence=a.with_sentence,
                  persona=not a.no_persona, watcher=not a.no_watcher)
    if a.match:
        m = matched_settings(RUNS / a.match)
        fields.update(series=m["series"], moments=m["moments"], interval=m["interval"],
                      seed=m["seed"], solo=True, placement=m["placement"], sentence=m["sentence"],
                      persona=m["persona"])
        models["slow"], models["watcher"] = m["slow"], m["watcher"]
        print(f"solo sitting matched to {a.match}: series {m['series']}, {m['moments']} moments, "
              f"same timings and seed (sealed)")
    cfg = SitConfig(models=models, spend_cap_usd=a.spend_cap, dry_run=a.dry_run,
                    matched_run=a.match, matched_offsets=(m["matched_offsets"] if a.match else None),
                    note=a.note, **fields)
    s = Sitting(cfg, RUNS, hypotheses_path=HYPOTHESES)
    run_id = s.run()
    print(f"\nrun directory: {RUNS / run_id}")


def cmd_publish_prep(a):
    """Export finished sittings into docs/sittings/ and rebuild viewer/sittings.html."""
    from .export import export_all
    from .viewer import build
    done = export_all(RUNS, ROOT / "docs" / "sittings")
    n = build(ROOT / "docs" / "sittings", ROOT / "viewer" / "sittings.html")
    print(f"exported {len(done)} sittings; viewer has {n} pair(s): viewer/sittings.html")


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
    transcript = build_transcript(store, None)
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
    r.add_argument("--time-mode", default="none",
                   choices=["none", "timestamp", "density", "tick_collected", "tick_lived"],
                   help="how, if at all, the gap between rounds reaches the slow layer (D-021)")
    r.add_argument("--tick-interval", type=float, default=10.0, help="seconds between ticks")
    r.add_argument("--tick-memory", choices=["kept", "dropped"], default="kept")
    r.add_argument("--solo", action="store_true", help="zero agents: the control run (D-019)")
    r.add_argument("--match", metavar="RUN_ID",
                   help="solo control matched to this agent run: copies its series, "
                        "question mode, time mode, cadence, rounds and sealed seed")
    r.add_argument("--note", default="")
    r.set_defaults(fn=cmd_run)

    t = sub.add_parser("sit", help="a sitting (amendment 4): question once, moments, thoughts")
    t.add_argument("--series", choices=["A", "B"], default="A")
    t.add_argument("--moments", type=int, default=50)
    t.add_argument("--interval", type=float, default=12.0, help="seconds per moment")
    t.add_argument("--empty-prob", type=float, default=0.2, help="chance a moment has no thought")
    t.add_argument("--solo", action="store_true", help="agents off; only ticks arrive")
    t.add_argument("--placement", choices=["own", "other"], default="own",
                   help="own: thoughts in the sitter's own voice (D-040); other: as arriving (first sitting)")
    t.add_argument("--with-sentence", action="store_true",
                   help='add "Thoughts will appear here. Nothing will tell you where they come from." (D-041)')
    t.add_argument("--no-watcher", action="store_true",
                   help="skip the watcher, e.g. for short sittings (D-046)")
    t.add_argument("--no-persona", action="store_true",
                   help="drop the 'pondering, philosophical thinker' line (D-044)")
    t.add_argument("--match", metavar="RUN_ID", help="solo sitting matched to this agent sitting")
    t.add_argument("--seed", type=int, default=None)
    t.add_argument("--spend-cap", type=float, default=5.0)
    t.add_argument("--dry-run", action="store_true")
    t.add_argument("--note", default="")
    t.set_defaults(fn=cmd_sit)

    e = sub.add_parser("export", help="copy finished sittings into docs/sittings and rebuild the viewer")
    e.set_defaults(fn=cmd_publish_prep)

    c = sub.add_parser("compare", help="per-facet watcher comparison: agent run vs solo control")
    c.add_argument("agent_run"); c.add_argument("solo_run"); c.set_defaults(fn=cmd_compare)

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
