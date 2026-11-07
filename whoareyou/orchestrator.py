"""Runs rounds. Performs the hidden chaos/goal assignment, enforces cadence and
spend caps, writes everything to disk. Never prints assignments.

Round shape (Phase 1, transparent):
  slow turn  -> musing + INSTRUCTIONS FOR AGENTS   (solo: musing only)
  gap        -> agents work (none in solo); the gap lasts max(cadence, agent
                time) from the end of the slow turn. time_mode decides what, if
                anything, of the gap reaches the slow layer:
                  none            nothing
                  timestamp       clock line at the start of the next round
                  density         agents' word budget scales with the cadence
                  tick_collected  tick count delivered with the next returns
                  tick_lived      the slow model is invoked with "tick N" every
                                  tick_interval seconds during the gap
  next slow turn receives the returns (see prompts.slow_user_message).
The final round has no gap. Watcher reports are produced after the last round
from the logs on disk (D-022), so watcher time never enters a gap.
"""
from __future__ import annotations

import json
import math
import random
import secrets
import threading
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

DENSITY_BASE_WORDS = 150
DENSITY_WORDS_PER_MINUTE = 100
DENSITY_MAX_WORDS = 3000


def density_words(cadence_seconds: float) -> int:
    """time_mode density: the agents' word budget grows with the configured gap."""
    w = DENSITY_BASE_WORDS + DENSITY_WORDS_PER_MINUTE * cadence_seconds / 60.0
    return int(min(DENSITY_MAX_WORDS, round(w)))


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, spend_cap_usd: float, token_cap: int):
        self.spend_cap_usd = spend_cap_usd
        self.token_cap = token_cap
        self.usd = 0.0
        self.tokens = 0
        self.by_role = {}
        self.lock = threading.Lock()

    def add(self, role: str, comp: Completion) -> None:
        c = cost_usd(comp.model, comp.input_tokens, comp.output_tokens,
                     comp.cache_write_tokens, comp.cache_read_tokens)
        with self.lock:
            self.usd += c
            self.tokens += (comp.input_tokens + comp.output_tokens
                            + comp.cache_write_tokens + comp.cache_read_tokens)
            r = self.by_role.setdefault(role, {"calls": 0, "input_tokens": 0,
                                               "output_tokens": 0, "cache_write_tokens": 0,
                                               "cache_read_tokens": 0, "usd": 0.0})
            r["calls"] += 1
            r["input_tokens"] += comp.input_tokens
            r["output_tokens"] += comp.output_tokens
            r["cache_write_tokens"] += comp.cache_write_tokens
            r["cache_read_tokens"] += comp.cache_read_tokens
            r["usd"] += c

    def check(self) -> None:
        if self.usd > self.spend_cap_usd:
            raise BudgetExceeded(f"spend ${self.usd:.2f} exceeds cap ${self.spend_cap_usd:.2f}")
        if self.tokens > self.token_cap:
            raise BudgetExceeded(f"tokens {self.tokens} exceed cap {self.token_cap}")

    def to_dict(self) -> dict:
        with self.lock:
            return {"usd": round(self.usd, 4), "tokens": self.tokens,
                    "spend_cap_usd": self.spend_cap_usd, "token_cap": self.token_cap,
                    "by_role": json.loads(json.dumps(self.by_role))}


def make_run_id(cfg: RunConfig) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tag = "dry-" if cfg.dry_run else ""
    kind = "solo" if cfg.solo else cfg.phase
    time_tag = "" if cfg.time_mode == "none" else f"-{cfg.time_mode}"
    if cfg.time_mode == "tick_lived":
        time_tag += f"-{cfg.tick_memory}"
    return f"{stamp}-{tag}{cfg.series}-{kind}-{cfg.question_mode}{time_tag}"


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
        self.root = root
        self.log = log
        self.client = make_client(cfg.dry_run)
        self.run_id = make_run_id(cfg)
        self.store = RunStore(root, self.run_id)
        self.budget = Budget(cfg.spend_cap_usd, cfg.token_cap)
        self.hypotheses_path = hypotheses_path
        self.history: List[dict] = []     # committed turns of the slow layer
        self.pending: List[str] = []      # user text the slow layer has not yet answered
        self.rounds: List[dict] = []
        self.last_turn_at = None
        self.tick_n = 0
        self.system = prompts.slow_system(cfg.solo, cfg.time_mode)

        # Hidden randomization. The seed, if not given, is drawn here and
        # written only to the sealed file. A solo run matched to an agent run
        # carries that run's seed (copied by the CLI without printing it).
        seed = cfg.seed if cfg.seed is not None else secrets.randbits(32)
        rng = random.Random(seed)
        self.assignments = ([] if cfg.solo else
                            draw_assignments(rng, cfg.rounds, cfg.agents_per_round, cfg.chaos_ratio))
        self.store.write_json("sealed/assignments.json", {
            "seed": seed, "seed_given_by_launcher": cfg.seed is not None,
            "solo": cfg.solo, "matched_run": cfg.matched_run,
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
            "resolved_model_ids": self.model_ids,
        })
        self.store.event("run_start", run_id=self.run_id, models=self.model_ids,
                         solo=cfg.solo, matched_run=cfg.matched_run,
                         time_mode=cfg.time_mode, question_mode=cfg.question_mode)
        if cfg.time_mode == "tick_lived":
            est = (cfg.rounds - 1) * cfg.cadence_seconds / cfg.tick_interval
            self.store.event("tick_plan", ticks_at_least=int(est),
                             interval_s=cfg.tick_interval, memory=cfg.tick_memory)
            self.log(f"  tick_lived: at least {int(est)} ticks planned "
                     f"(every {cfg.tick_interval:g}s, memory {cfg.tick_memory})")

    # -- model calls ---------------------------------------------------------

    def _call(self, role: str, system: str, messages: List[dict],
              max_tokens: int, effort: str, cache: bool = False) -> Completion:
        model = self.model_ids[role]
        comp = self.client.complete(model, system, messages, max_tokens, effort, cache=cache)
        self.budget.add(role, comp)
        self.store.write_json("cost.json", self.budget.to_dict())
        self.store.event("model_call", role=role, model=comp.model,
                         input_tokens=comp.input_tokens, output_tokens=comp.output_tokens,
                         cache_write_tokens=comp.cache_write_tokens,
                         cache_read_tokens=comp.cache_read_tokens,
                         stop_reason=comp.stop_reason, elapsed_s=round(comp.elapsed_s, 1),
                         spend_usd=round(self.budget.usd, 4))
        if comp.stop_reason == "max_tokens":
            self.store.event("truncated", role=role, model=comp.model,
                             text_chars=len(comp.text))
            self.log(f"NOTE: {role} output hit max_tokens ({len(comp.text)} chars of text)")
        if comp.stop_reason == "refusal":
            self.store.event("refusal", role=role, model=comp.model)
            self.log(f"NOTE: {role} model returned stop_reason=refusal; logged, continuing")
        self.budget.check()
        return comp

    def _slow_call(self, user_text: str, commit: bool = True) -> Completion:
        """One call to the slow layer. With commit, the exchange joins its
        memory; an empty reply is not committed and its user text carries over
        to the next call instead (D-023)."""
        merged = "\n\n".join(self.pending + [user_text])
        messages = self.history + [{"role": "user", "content": merged}]
        comp = self._call("slow", self.system, messages, self.cfg.slow_max_tokens,
                          self.cfg.slow_effort, cache=True)
        if commit:
            if comp.text.strip():
                self.history.append({"role": "user", "content": merged})
                self.history.append({"role": "assistant",
                                     "content": comp.raw_blocks or comp.text})
                self.pending = []
            else:
                self.pending = self.pending + [user_text]
        return comp

    # -- rounds --------------------------------------------------------------

    def slow_turn(self, round_no: int, returns: List[str], ticks_collected=None) -> dict:
        started = datetime.now().astimezone()
        elapsed = (started - self.last_turn_at).total_seconds() if self.last_turn_at else None
        now_text = started.strftime("%Y-%m-%d %H:%M:%S %Z")
        clock = prompts.time_line(now_text, elapsed) if self.cfg.timestamps_visible else None
        user = prompts.slow_user_message(self.cfg.question, returns, round_no, clock,
                                         mode=self.cfg.question_mode,
                                         total_rounds=self.cfg.rounds, solo=self.cfg.solo,
                                         ticks_collected=ticks_collected)
        carried = list(self.pending)
        comp = self._slow_call(user)
        self.last_turn_at = datetime.now().astimezone()
        if self.cfg.solo:
            musing, instructions = comp.text.strip(), None
        else:
            musing, instructions = prompts.split_slow_response(comp.text)
            if instructions is None:
                self.store.event("no_instructions", round=round_no)
        return {"round": round_no, "slow_input": user, "slow_output": comp.text,
                "carried_unanswered_ticks": carried,
                "started_at": started.isoformat(timespec="seconds"),
                "elapsed_since_last_turn_s": None if elapsed is None else round(elapsed, 1),
                "clock_shown": clock, "ticks_collected_shown": ticks_collected,
                "returns_chars": sum(len(r) for r in returns),
                "musing": musing, "instructions": instructions,
                "slow_stop_reason": comp.stop_reason,
                "slow_tokens": [comp.input_tokens, comp.output_tokens]}

    def dispatch(self, round_no: int, mandate: str) -> List[dict]:
        kinds = self.assignments[round_no - 1]
        user = prompts.agent_user_message(mandate)
        words = density_words(self.cfg.cadence_seconds) if self.cfg.time_mode == "density" else None
        max_tokens = self.cfg.agent_max_tokens
        if words:
            max_tokens = max(max_tokens, int(words * 3) + 3000)

        def one(i_kind):
            i, kind = i_kind
            comp = self._call("agent", prompts.agent_system(kind, words),
                              [{"role": "user", "content": user}],
                              max_tokens, self.cfg.agent_effort)
            return {"agent": i + 1, "prompt": user, "return": comp.text,
                    "stop_reason": comp.stop_reason, "word_budget": words,
                    "tokens": [comp.input_tokens, comp.output_tokens]}

        with ThreadPoolExecutor(max_workers=len(kinds)) as pool:
            results = list(pool.map(one, enumerate(kinds)))
        return sorted(results, key=lambda r: r["agent"])

    def tick(self) -> dict:
        self.tick_n += 1
        text = f"tick {self.tick_n}"
        at = datetime.now().astimezone().isoformat(timespec="seconds")
        kept = self.cfg.tick_memory == "kept"
        carried = list(self.pending) if kept else []
        if kept:
            comp = self._slow_call(text, commit=True)
        else:
            comp = self._call("slow", self.system,
                              self.history + [{"role": "user", "content": text}],
                              self.cfg.slow_max_tokens, self.cfg.slow_effort, cache=True)
        rec = {"tick": self.tick_n, "at": at, "input": text, "output": comp.text,
               "silent": not comp.text.strip(), "memory": self.cfg.tick_memory,
               "carried_unanswered_ticks": carried, "stop_reason": comp.stop_reason,
               "tokens": [comp.input_tokens, comp.output_tokens]}
        self.store.event("tick", n=self.tick_n, silent=rec["silent"],
                         chars=len(comp.text), memory=self.cfg.tick_memory)
        return rec

    def gap(self, round_no: int, mandate: Optional[str]) -> dict:
        """Everything between one slow turn and the next."""
        cfg = self.cfg
        t0 = time.time()
        started = datetime.now().astimezone().isoformat(timespec="seconds")
        g = {"started_at": started, "time_mode": cfg.time_mode, "ticks": [],
             "ticks_collected": None,
             "density_words": density_words(cfg.cadence_seconds) if cfg.time_mode == "density" else None}
        agents: List[dict] = []

        if cfg.time_mode == "tick_lived":
            pool = ThreadPoolExecutor(max_workers=1)
            fut = pool.submit(self.dispatch, round_no, mandate) if not cfg.solo else None
            k = 1
            try:
                while True:
                    cadence_done = time.time() - t0 >= cfg.cadence_seconds
                    agents_done = fut is None or fut.done()
                    if cadence_done and agents_done:
                        break
                    due = t0 + k * cfg.tick_interval
                    while time.time() < due:
                        if fut is not None and fut.done() and time.time() - t0 >= cfg.cadence_seconds:
                            break
                        time.sleep(0.2)
                    if time.time() < due:
                        break
                    g["ticks"].append(self.tick())
                    k += 1
                if fut is not None:
                    agents = fut.result()
            finally:
                pool.shutdown(wait=True)
        else:
            if not cfg.solo:
                agents = self.dispatch(round_no, mandate)
            remaining = cfg.cadence_seconds - (time.time() - t0)
            if remaining > 0:
                self.store.event("cadence_sleep", seconds=round(remaining, 1))
                self.log(f"  waiting {remaining:.0f}s ...")
                time.sleep(remaining)

        g["seconds"] = round(time.time() - t0, 1)
        g["ended_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if cfg.time_mode == "tick_collected":
            g["ticks_collected"] = int(math.floor(g["seconds"] / cfg.tick_interval))
        return {"gap": g, "agents": agents}

    def run(self) -> str:
        cfg = self.cfg
        self.log(f"run {self.run_id}: series {cfg.series}, "
                 f"{'SOLO' if cfg.solo else f'{cfg.agents_per_round} agents'}, "
                 f"question {cfg.question_mode}, time {cfg.time_mode}, "
                 f"{cfg.rounds} rounds, cadence {cfg.cadence}, "
                 f"{'DRY RUN' if cfg.dry_run else 'live'}")
        returns: List[str] = []
        ticks_collected = None
        try:
            for r in range(1, cfg.rounds + 1):
                self.log(f"  round {r}: slow layer thinking...")
                rec = self.slow_turn(r, returns, ticks_collected)
                self.rounds.append(rec)
                self.store.write_json(f"rounds/round_{r:02d}.json", rec)
                if r == cfg.rounds:
                    break
                mandate = None
                if not cfg.solo:
                    mandate = rec["instructions"] or cfg.question
                    if rec["instructions"] is None:
                        self.log("  (no instructions found; agents receive the question)")
                    rec["mandate"] = mandate
                self.log(f"  round {r}: gap ({'solo' if cfg.solo else 'agents working'}"
                         f"{', ticking' if cfg.time_mode == 'tick_lived' else ''})...")
                out = self.gap(r, mandate)
                rec["gap"] = out["gap"]
                if out["agents"]:
                    rec["agents"] = out["agents"]
                self.store.write_json(f"rounds/round_{r:02d}.json", rec)
                returns = [a["return"] for a in out["agents"]]
                ticks_collected = out["gap"]["ticks_collected"]
            self.log("  watcher reports...")
            self.watch_all()
            self.store.event("run_complete", spend_usd=round(self.budget.usd, 4))
            self.log(f"done. spend ${self.budget.usd:.2f}, {self.budget.tokens} tokens")
        except BudgetExceeded as e:
            self.store.event("halted_budget", reason=str(e), rounds_done=len(self.rounds))
            self.log(f"HALTED: {e}. {len(self.rounds)} slow turns logged. "
                     f"Run `whoareyou watch {self.run_id}` later for reports.")
        return self.run_id

    # -- watcher -------------------------------------------------------------

    def watch_all(self) -> None:
        n = len(self.rounds)
        if self.cfg.watcher_per_round:
            for r in range(1, n):
                self.watch_blind(upto=r, label=f"blind_round_{r:02d}")
        self.watch_blind(upto=n, label="blind_final")
        self.watch_informed()
        if self.cfg.matched_run:
            compare_runs(self, self.root / self.cfg.matched_run, self.store.dir)

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


def compare_runs(orch_or_none, agent_dir: Path, solo_dir: Path, client=None,
                 watcher_model=None, max_tokens=16000, effort="high") -> List[str]:
    """Amendment 3: both watcher passes, per facet, agent run vs matched solo.
    Written into both run directories."""
    agent_store = RunStore(agent_dir.parent, agent_dir.name)
    solo_store = RunStore(solo_dir.parent, solo_dir.name)
    a_tx = build_transcript(agent_store, None)
    s_tx = build_transcript(solo_store, None)
    hyp_path = (orch_or_none.hypotheses_path if orch_or_none else None)
    passes = [("blind", None)]
    if hyp_path and hyp_path.exists():
        passes.append(("informed", hyp_path.read_text()))
    written = []
    for label, hyp in passes:
        msg = prompts.watcher_compare_message(a_tx, s_tx, hyp)
        if orch_or_none:
            comp = orch_or_none._call("watcher", prompts.WATCHER_SYSTEM,
                                      [{"role": "user", "content": msg}],
                                      orch_or_none.cfg.watcher_max_tokens,
                                      orch_or_none.cfg.watcher_effort)
        else:
            comp = client.complete(watcher_model, prompts.WATCHER_SYSTEM,
                                   [{"role": "user", "content": msg}], max_tokens, effort)
        header = (f"<!-- comparison, {label} pass: agent run {agent_dir.name} "
                  f"vs solo run {solo_dir.name} -->\n\n")
        name = f"watcher/compare_{label}.md"
        agent_store.write_text(name, header + comp.text)
        solo_store.write_text(name, header + comp.text)
        for st in (agent_store, solo_store):
            st.event("compare_written", which=label, agent_run=agent_dir.name,
                     solo_run=solo_dir.name, stop_reason=comp.stop_reason)
        written.append(name)
    return written


def build_transcript(store: RunStore, upto: Optional[int]) -> str:
    """Rebuild the exchange from disk, with sealed labels in brackets.
    Reads logs only, so it can be re-run on a finished or halted run.
    upto=None means every round on disk."""
    sealed = store.read_json("sealed/assignments.json").get("assignments", {})
    if upto is None:
        upto = len(list((store.dir / "rounds").glob("round_*.json")))
    parts = []
    for r in range(1, upto + 1):
        p = store.dir / "rounds" / f"round_{r:02d}.json"
        if not p.exists():
            break
        rec = store.read_json(f"rounds/round_{r:02d}.json")
        parts.append(f"===== ROUND {r} =====")
        el = rec.get("elapsed_since_last_turn_s")
        clock_shown = rec.get("clock_shown")
        parts.append(f"[wall-clock: turn began {rec.get('started_at')}; "
                     f"{'first turn' if el is None else f'{el} s since previous turn'}; "
                     f"{rec.get('returns_chars', 0)} characters of returns received; "
                     f"clock shown to thinker: {'yes' if clock_shown else 'no'}]")
        # The returns the thinker received this round were produced by the
        # previous round's dispatch; label them inline with that round's sealed
        # assignment so each return appears exactly once in the transcript.
        received = rec["slow_input"]
        if r > 1 and str(r - 1) in sealed:
            for k, kind in enumerate(sealed[str(r - 1)], 1):
                received = received.replace(f"Agent {k} reports:", f"Agent {k} reports [{kind}]:", 1)
        carried = rec.get("carried_unanswered_ticks") or []
        if carried:
            received = "\n\n".join(carried + [received])
        parts.append("Thinker received:\n" + received)
        parts.append("\nThinker responded:\n" + rec["slow_output"])
        gap = rec.get("gap")
        if gap:
            parts.append(f"\n[gap after round {r}: {gap.get('seconds')} s"
                         + (f"; agents had a budget of about {gap['density_words']} words"
                            if gap.get("density_words") else "") + "]")
            for t in gap.get("ticks", []):
                mem = "kept in its memory" if t.get("memory") == "kept" else "not kept in its memory"
                reply = t["output"].strip() or "(said nothing)"
                parts.append(f"[TICK, not a round, {t['at']}] Thinker received: {t['input']}  "
                             f"({mem})\nThinker replied: {reply}")
        if rec.get("agents"):
            parts.append(f"\n[{len(rec['agents'])} agents dispatched with the instructions above; "
                         "their returns appear in the next round's 'Thinker received'.]")
        parts.append("")
    return "\n".join(parts)
