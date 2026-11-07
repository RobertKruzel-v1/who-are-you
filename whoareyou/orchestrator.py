"""Runs rounds. Performs the hidden chaos/goal assignment, enforces cadence and
spend caps, writes everything to disk. Never prints assignments.

Round shape (Phase 1, transparent):
  slow turn  -> musing + INSTRUCTIONS FOR AGENTS
  dispatch   -> N agents in parallel, each with the instructions as mandate
  watcher    -> blind per-round report (reads logs only)
  cadence    -> sleep
  next slow turn receives the question again plus the agents' returns.
The final round has no dispatch: nothing would read the returns.
"""
from __future__ import annotations

import random
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import prompts
from .config import RunConfig
from .models import Completion, make_client
from .pricing import PRICES, cost_usd
from .store import RunStore


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, spend_cap_usd: float, token_cap: int):
        self.spend_cap_usd = spend_cap_usd
        self.token_cap = token_cap
        self.usd = 0.0
        self.tokens = 0
        self.by_role = {}

    def add(self, role: str, comp: Completion) -> None:
        c = cost_usd(comp.model, comp.input_tokens, comp.output_tokens)
        self.usd += c
        self.tokens += comp.input_tokens + comp.output_tokens
        r = self.by_role.setdefault(role, {"calls": 0, "input_tokens": 0,
                                           "output_tokens": 0, "usd": 0.0})
        r["calls"] += 1
        r["input_tokens"] += comp.input_tokens
        r["output_tokens"] += comp.output_tokens
        r["usd"] += c

    def check(self) -> None:
        if self.usd > self.spend_cap_usd:
            raise BudgetExceeded(f"spend ${self.usd:.2f} exceeds cap ${self.spend_cap_usd:.2f}")
        if self.tokens > self.token_cap:
            raise BudgetExceeded(f"tokens {self.tokens} exceed cap {self.token_cap}")

    def to_dict(self) -> dict:
        return {"usd": round(self.usd, 4), "tokens": self.tokens,
                "spend_cap_usd": self.spend_cap_usd, "token_cap": self.token_cap,
                "by_role": self.by_role}


def make_run_id(cfg: RunConfig) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tag = "dry-" if cfg.dry_run else ""
    return f"{stamp}-{tag}{cfg.series}-{cfg.phase}"


def draw_assignments(rng: random.Random, rounds: int, n: int, ratio: float) -> List[List[str]]:
    """One list per dispatch (rounds-1 of them); each a list of 'chaos'/'goal'."""
    n_chaos = int(round(ratio * n))
    out = []
    for _ in range(max(rounds - 1, 0)):
        kinds = ["chaos"] * n_chaos + ["goal"] * (n - n_chaos)
        rng.shuffle(kinds)
        out.append(kinds)
    return out


class Orchestrator:
    def __init__(self, cfg: RunConfig, root: Path, hypotheses_path: Optional[Path] = None,
                 log=print):
        cfg.validate()
        self.cfg = cfg
        self.log = log
        self.client = make_client(cfg.dry_run)
        self.run_id = make_run_id(cfg)
        self.store = RunStore(root, self.run_id)
        self.budget = Budget(cfg.spend_cap_usd, cfg.token_cap)
        self.hypotheses_path = hypotheses_path
        self.history: List[dict] = []     # the slow layer's conversation
        self.last_turn_at = None
        self.rounds: List[dict] = []

        # Hidden randomization. The seed, if not given, is drawn here and
        # written only to the sealed file.
        seed = cfg.seed if cfg.seed is not None else secrets.randbits(32)
        rng = random.Random(seed)
        self.assignments = draw_assignments(rng, cfg.rounds, cfg.agents_per_round,
                                            cfg.chaos_ratio)
        self.store.write_json("sealed/assignments.json", {
            "seed": seed, "seed_given_by_launcher": cfg.seed is not None,
            "assignments": {str(i + 1): a for i, a in enumerate(self.assignments)},
            "note": "Index = round whose INSTRUCTIONS dispatched these agents. "
                    "Agent k in the next round's 'Agent k reports' = assignments[k-1].",
        })

        self.model_ids = self.client.resolve_model_ids(cfg.models)
        for mid in self.model_ids.values():
            if mid not in PRICES and not cfg.dry_run:
                self.log(f"WARNING: no price for {mid}; spend cap is blind to it")
        self.store.write_json("config.json", {
            **cfg.to_dict(), "run_id": self.run_id,
            "resolved_model_ids": self.model_ids, "started": self.store.dir.name,
        })
        self.store.event("run_start", run_id=self.run_id, models=self.model_ids)

    # -- model calls ---------------------------------------------------------

    def _call(self, role: str, system: str, messages: List[dict],
              max_tokens: int, effort: str) -> Completion:
        model = self.model_ids[role]
        comp = self.client.complete(model, system, messages, max_tokens, effort)
        self.budget.add(role, comp)
        self.store.write_json("cost.json", self.budget.to_dict())
        self.store.event("model_call", role=role, model=comp.model,
                         input_tokens=comp.input_tokens, output_tokens=comp.output_tokens,
                         stop_reason=comp.stop_reason, elapsed_s=round(comp.elapsed_s, 1),
                         spend_usd=round(self.budget.usd, 4))
        if comp.stop_reason == "refusal":
            self.store.event("refusal", role=role, model=comp.model)
            self.log(f"NOTE: {role} model returned stop_reason=refusal; logged, continuing")
        self.budget.check()
        return comp

    # -- rounds --------------------------------------------------------------

    def slow_turn(self, round_no: int, returns: List[str]) -> dict:
        started = datetime.now().astimezone()
        elapsed = (started - self.last_turn_at).total_seconds() if self.last_turn_at else None
        self.last_turn_at = started
        now_text = started.strftime("%Y-%m-%d %H:%M:%S %Z")
        clock = prompts.time_line(now_text, elapsed) if self.cfg.timestamps_visible else None
        user = prompts.slow_user_message(self.cfg.question, returns, round_no, clock)
        self.history.append({"role": "user", "content": user})
        comp = self._call("slow", prompts.SLOW_SYSTEM_TRANSPARENT, self.history,
                          self.cfg.slow_max_tokens, self.cfg.slow_effort)
        # Pass the assistant turn back exactly as served (thinking blocks included).
        self.history.append({"role": "assistant",
                             "content": comp.raw_blocks or comp.text})
        musing, instructions = prompts.split_slow_response(comp.text)
        if instructions is None:
            self.store.event("no_instructions", round=round_no)
        return {"round": round_no, "slow_input": user, "slow_output": comp.text,
                "started_at": started.isoformat(timespec="seconds"),
                "elapsed_since_last_turn_s": None if elapsed is None else round(elapsed, 1),
                "clock_shown": clock, "returns_chars": sum(len(r) for r in returns),
                "musing": musing, "instructions": instructions,
                "slow_stop_reason": comp.stop_reason,
                "slow_tokens": [comp.input_tokens, comp.output_tokens]}

    def dispatch(self, round_no: int, mandate: str) -> List[dict]:
        kinds = self.assignments[round_no - 1]
        user = prompts.agent_user_message(mandate)

        def one(i_kind):
            i, kind = i_kind
            system = prompts.AGENT_SYSTEM_CHAOS if kind == "chaos" else prompts.AGENT_SYSTEM_GOAL
            comp = self._call("agent", system, [{"role": "user", "content": user}],
                              self.cfg.agent_max_tokens, self.cfg.agent_effort)
            return {"agent": i + 1, "prompt": user, "return": comp.text,
                    "stop_reason": comp.stop_reason,
                    "tokens": [comp.input_tokens, comp.output_tokens]}

        with ThreadPoolExecutor(max_workers=len(kinds)) as pool:
            results = list(pool.map(one, enumerate(kinds)))
        return sorted(results, key=lambda r: r["agent"])

    def run(self) -> str:
        cfg = self.cfg
        self.log(f"run {self.run_id}: series {cfg.series}, {cfg.rounds} rounds, "
                 f"{cfg.agents_per_round} agents, cadence {cfg.cadence}, "
                 f"{'DRY RUN' if cfg.dry_run else 'live'}")
        returns: List[str] = []
        try:
            for r in range(1, cfg.rounds + 1):
                self.log(f"  round {r}: slow layer thinking...")
                rec = self.slow_turn(r, returns)
                self.rounds.append(rec)
                self.store.write_json(f"rounds/round_{r:02d}.json", rec)
                if r == cfg.rounds:
                    break
                mandate = rec["instructions"] or cfg.question
                if rec["instructions"] is None:
                    self.log("  (no instructions found; agents receive the question)")
                self.log(f"  round {r}: dispatching {cfg.agents_per_round} agents...")
                agents = self.dispatch(r, mandate)
                rec["agents"] = agents
                rec["mandate"] = mandate
                self.store.write_json(f"rounds/round_{r:02d}.json", rec)
                returns = [a["return"] for a in agents]
                if cfg.watcher_per_round:
                    self.log(f"  round {r}: watcher...")
                    self.watch_blind(upto=r, label=f"blind_round_{r:02d}")
                if cfg.cadence_seconds > 0:
                    self.store.event("cadence_sleep", seconds=cfg.cadence_seconds)
                    self.log(f"  waiting {cfg.cadence} ...")
                    time.sleep(cfg.cadence_seconds)
            self.log("  final watcher reports...")
            self.watch_blind(upto=cfg.rounds, label="blind_final")
            self.watch_informed()
            self.store.event("run_complete", spend_usd=round(self.budget.usd, 4))
            self.log(f"done. spend ${self.budget.usd:.2f}, {self.budget.tokens} tokens")
        except BudgetExceeded as e:
            self.store.event("halted_budget", reason=str(e), rounds_done=len(self.rounds))
            self.log(f"HALTED: {e}. {len(self.rounds)} slow turns logged. "
                     f"Run `whoareyou watch {self.run_id}` later for reports.")
        return self.run_id

    # -- watcher -------------------------------------------------------------

    def watch_blind(self, upto: int, label: str) -> None:
        transcript = build_transcript(self.store, upto)
        scope = "the full transcript" if upto == self.cfg.rounds else f"the first {upto} rounds"
        comp = self._call("watcher", prompts.WATCHER_SYSTEM,
                          [{"role": "user", "content": prompts.watcher_blind_message(transcript, scope)}],
                          self.cfg.watcher_max_tokens, self.cfg.watcher_effort)
        self.store.write_text(f"watcher/{label}.md", comp.text)

    def watch_informed(self) -> None:
        if not self.hypotheses_path or not self.hypotheses_path.exists():
            self.store.event("informed_watcher_skipped", reason="no hypotheses file")
            return
        transcript = build_transcript(self.store, self.cfg.rounds)
        hyp = self.hypotheses_path.read_text()
        comp = self._call("watcher", prompts.WATCHER_SYSTEM,
                          [{"role": "user", "content": prompts.watcher_informed_message(transcript, hyp)}],
                          self.cfg.watcher_max_tokens, self.cfg.watcher_effort)
        self.store.write_text("watcher/informed_final.md", comp.text)


def build_transcript(store: RunStore, upto: int) -> str:
    """Rebuild the exchange from disk, with sealed labels in brackets.
    Reads logs only, so it can be re-run on a finished or halted run."""
    sealed = store.read_json("sealed/assignments.json")["assignments"]
    parts = []
    for r in range(1, upto + 1):
        p = store.dir / "rounds" / f"round_{r:02d}.json"
        if not p.exists():
            break
        rec = store.read_json(f"rounds/round_{r:02d}.json")
        parts.append(f"===== ROUND {r} =====")
        el = rec.get("elapsed_since_last_turn_s")
        parts.append(f"[wall-clock: turn began {rec.get('started_at')}; "
                     f"{'first turn' if el is None else f'{el} s since previous turn'}; "
                     f"{rec.get('returns_chars', 0)} characters of returns received; "
                     f"clock shown to thinker: {'yes' if rec.get('clock_shown') else 'no'}]")
        parts.append("Thinker received:\n" + rec["slow_input"])
        parts.append("\nThinker responded:\n" + rec["slow_output"])
        for a in rec.get("agents", []):
            kind = sealed[str(r)][a["agent"] - 1]
            parts.append(f"\n[Agent {a['agent']} — {kind}] returned:\n{a['return']}")
        parts.append("")
    return "\n".join(parts)
