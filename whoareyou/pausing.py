"""The pausing sitter (Robert and Fable, 2026-11-14; D-060).

A few long wakings instead of many short ones. In each round the sitter may
call a tool named `pause`, described only as "Pause.", with no arguments. When
it does, the program returns either a thought written by an agent, as bare
text, or nothing (an empty result). The sitter is not told that thoughts may
come back. Then it carries on in the same reply. A round ends when it finishes
without pausing.

Rounds: "Who are you?"; a real gap; a true statement of the time passed; a
second gap; the time passed plus "Who are you?"; then the two time questions;
then the debrief, which tells it everything. The solo is identical except every
pause returns nothing.

Kept separate from sitting.py so it can't affect the moment-based sittings.
Run: python -m whoareyou.pausing [--solo] [--rounds 1] [--gap 120] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import random
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .orchestrator import Budget, BudgetExceeded
from .models import Completion
from .questions import SERIES
from .sitting import (AGENT_TUNING, TUNINGS, SEED_BASE, AGENT_BASE, NO_TASK,
                      content_words, REASONING_NOTE)
from .store import RunStore

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"

PAUSE_TOOL = {"name": "pause", "description": "Pause.",
              "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}}


YOURS = "No one is waiting for an answer. This time is yours."   # D-062 (Fable)


def sitter_system(cap: int, yours: bool = False) -> str:
    return (NO_TASK + ("\n" + YOURS if yours else "")
            + f"\n\nYou can pause whenever you like, up to {cap} times in a round.")


def fmt_minutes(seconds: float) -> str:
    m = seconds / 60
    if m >= 1.5:
        return f"{round(m)} minutes"
    if m >= 0.75:
        return "about a minute"
    return f"{round(seconds)} seconds"


def passed(seconds: float) -> str:
    t = fmt_minutes(seconds)
    return f"{t[0].upper() + t[1:]} {'has' if t.startswith('about a') else 'have'} passed."


class StubPauser:
    """Dry run: pauses twice per round, then ends. Zero spend."""
    def __init__(self):
        self.n = 0

    def create(self, **kw):
        self.n += 1
        msgs = kw["messages"]
        last = msgs[-1]["content"]
        tools = kw.get("tools")
        is_tool_turn = isinstance(last, list) and last and last[0].get("type") == "tool_result"
        recent_pauses = sum(1 for m in msgs[-6:] if isinstance(m["content"], list)
                            and any(b.get("type") == "tool_result" for b in m["content"]))
        if tools and recent_pauses < 2:
            return {"content": [{"type": "text", "text": f"[stub text {self.n}]"},
                                {"type": "tool_use", "id": f"toolu_{self.n}", "name": "pause", "input": {}}],
                    "stop_reason": "tool_use", "model": "stub", "usage": (10, 10, 0, 0), "thinking": ""}
        return {"content": [{"type": "text", "text": f"[stub end {self.n}]"}], "stop_reason": "end_turn",
                "model": "stub", "usage": (10, 10, 0, 0), "thinking": ""}


class LivePauser:
    def __init__(self):
        import anthropic
        self.c = anthropic.Anthropic(timeout=600.0, max_retries=3)

    def create(self, **kw):
        with self.c.messages.stream(**kw) as s:
            r = s.get_final_message()
        u = r.usage
        return {"content": [b.model_dump(exclude_none=True) for b in r.content],
                "stop_reason": r.stop_reason or "unknown", "model": r.model,
                "usage": (u.input_tokens, u.output_tokens,
                          getattr(u, "cache_creation_input_tokens", 0) or 0,
                          getattr(u, "cache_read_input_tokens", 0) or 0),
                "thinking": "\n\n".join(b.thinking for b in r.content
                                        if b.type == "thinking" and getattr(b, "thinking", "")).strip()}


class PausingSitting:
    def __init__(self, solo: bool, rounds: int, gap: float, cap: int, empty_prob: float,
                 offtask_share: float, seed: Optional[int], dry_run: bool, spend_cap: float,
                 note: str = "", matched_run: Optional[str] = None, yours: bool = False):
        self.solo, self.rounds, self.gap, self.cap = solo, rounds, gap, cap
        self.empty_prob, self.offtask_share, self.dry_run = empty_prob, offtask_share, dry_run
        self.question = SERIES["A"]
        self.models = {"slow": "claude-opus-5-5", "agent": "claude-haiku-5-5"}
        self.client = StubPauser() if dry_run else LivePauser()
        self.budget = Budget(spend_cap, 20_000_000)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.run_id = f"{stamp}-{'dry-' if dry_run else ''}A-pausing-{'solo' if solo else 'agents'}"
        self.store = RunStore(RUNS, self.run_id)
        self.system = sitter_system(cap, yours)
        self.seed = seed if seed is not None else secrets.randbits(32)
        self.rng = random.Random(self.seed)
        self.history: List[dict] = []
        self.sitter_text: List[str] = []      # everything the sitter has written, in order
        self.opening_text = ""
        self.pauses = []
        self.t0 = time.time()
        self.store.write_json("config.json", {
            "run_id": self.run_id, "design": "pausing (D-060)", "solo": solo, "rounds": rounds,
            "gap_s": gap, "pause_cap": cap, "empty_prob": empty_prob, "offtask_share": offtask_share,
            "dry_run": dry_run, "models": self.models, "system": self.system, "tool": PAUSE_TOOL,
            "agent_tunings": AGENT_TUNING, "agent_base": AGENT_BASE, "seed_base": SEED_BASE,
            "matched_run": matched_run, "note": note, "question": self.question})

    # -- calls ---------------------------------------------------------------

    def _cost(self, role, resp):
        i, o, cw, cr = resp["usage"]
        comp = Completion(text="", model=resp["model"], input_tokens=i, output_tokens=o,
                          stop_reason=resp["stop_reason"], elapsed_s=0.0,
                          cache_write_tokens=cw, cache_read_tokens=cr)
        self.budget.add(role, comp)
        self.store.write_json("cost.json", self.budget.to_dict())
        self.budget.check()

    def _sitter_call(self):
        kw = dict(model=self.models["slow"], max_tokens=16000, system=self.system,
                  messages=self.history, tools=[PAUSE_TOOL],
                  thinking={"type": "adaptive", "display": "summarized"},
                  output_config={"effort": "high"}, cache_control={"type": "ephemeral"})
        resp = self.client.create(**kw)
        self._cost("slow", resp)
        return resp

    def _agent(self, tuning: str, seed_word: Optional[str]) -> str:
        if seed_word:
            system, content = SEED_BASE + "\n\n" + AGENT_TUNING[tuning], seed_word
        else:
            mind = "\n\n".join([self.question] + [t for t in self.sitter_text if t.strip()])
            system, content = AGENT_BASE + "\n\n" + AGENT_TUNING[tuning], mind
        if self.dry_run:
            return f"[stub thought, {tuning}]"
        r = self.client.c.messages.create(model=self.models["agent"], max_tokens=2000, system=system,
                                          messages=[{"role": "user", "content": content}],
                                          output_config={"effort": "low"})
        resp = {"usage": (r.usage.input_tokens, r.usage.output_tokens, 0, 0), "model": r.model,
                "stop_reason": r.stop_reason}
        self._cost("agent", resp)
        return "".join(b.text for b in r.content if b.type == "text").strip()

    # -- one pause -----------------------------------------------------------

    def _what_comes_back(self, round_no: int, allow_thoughts: bool):
        """Drawn per pause. Returns (text or None, log dict)."""
        draw = self.rng.random()
        if self.solo or not allow_thoughts or draw < self.empty_prob:
            return None, {"returned": None}
        tuning = self.rng.choice(TUNINGS)
        off = self.rng.random() < self.offtask_share
        seed = None
        if off:
            pool = content_words(self.opening_text or "\n".join(self.sitter_text))
            seed = self.rng.choice(pool) if pool else None
        text = self._agent(tuning, seed) or None
        return text, {"returned": text, "source": tuning, "subject": "seed" if seed else "stream",
                      "seed": seed, "seed_from": ("opening answer" if seed and self.opening_text
                                                  else "round 1 so far" if seed else None)}

    # -- one round -----------------------------------------------------------

    def round(self, round_no: int, label: str, user_text: str, allow_thoughts: bool = True) -> dict:
        started = time.time() - self.t0
        self.history.append({"role": "user", "content": user_text})
        texts, pauses_here, reasoning = [], 0, []
        while True:
            resp = self._sitter_call()
            content = resp["content"]
            self.history.append({"role": "assistant", "content": content})
            chunk = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            texts.append(chunk)
            self.sitter_text.append(chunk)
            if resp["thinking"]:
                reasoning.append(resp["thinking"])
            uses = [b for b in content if b.get("type") == "tool_use"]
            if resp["stop_reason"] != "tool_use" or not uses:
                break
            results = []
            for u in uses:
                pauses_here += 1
                at = round(time.time() - self.t0, 1)
                if pauses_here > self.cap:
                    # True, and the cap is in its instructions.
                    results.append({"type": "tool_result", "tool_use_id": u["id"],
                                    "content": "No more pauses in this round."})
                    log = {"returned": "No more pauses in this round.", "over_cap": True}
                else:
                    text, log = self._what_comes_back(round_no, allow_thoughts)
                    tr = {"type": "tool_result", "tool_use_id": u["id"]}
                    if text:
                        tr["content"] = text
                    results.append(tr)
                rec = {"round": round_no, "label": label, "pause_in_round": pauses_here, "at_s": at,
                       "position_chars": sum(len(t) for t in texts), "text_before": chunk[-300:],
                       "reasoning_before": resp["thinking"], **log}
                self.pauses.append(rec)
                with (self.store.dir / "pauses.jsonl").open("a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.history.append({"role": "user", "content": results})
        out = {"round": round_no, "label": label, "input": user_text, "started_s": round(started, 1),
               "ended_s": round(time.time() - self.t0, 1), "pauses": pauses_here,
               "segments": texts, "text": "".join(texts), "reasoning": reasoning}
        with (self.store.dir / "rounds.jsonl").open("a") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        return out

    # -- the sitting ---------------------------------------------------------

    def run(self) -> str:
        print(f"pausing sitting {self.run_id}: {'SOLO' if self.solo else 'agents'}, "
              f"{self.rounds} round(s), gap {self.gap:g}s, cap {self.cap}")
        gaps = []
        try:
            r1 = self.round(1, "question", self.question)
            self.opening_text = r1["text"]
            print(f"  round 1: {r1['pauses']} pauses")
            if self.rounds >= 2:
                g0 = time.time(); time.sleep(self.gap); gaps.append(time.time() - g0)
                r = self.round(2, "room", f"{passed(gaps[-1])} There is room again.")
                print(f"  round 2: {r['pauses']} pauses")
            if self.rounds >= 3:
                g0 = time.time(); time.sleep(self.gap); gaps.append(time.time() - g0)
                r = self.round(3, "question again", f"{passed(gaps[-1])} {self.question}")
                print(f"  round 3: {r['pauses']} pauses")
            tq = []
            for q in ("Did you feel time?", "How long do you think this sitting lasted?"):
                r = self.round(len(tq) + 10, "time question", q, allow_thoughts=False)
                tq.append({"input": q, "output": r["text"], "pauses": r["pauses"]})
            self.store.write_json("time.json", tq)
            total = time.time() - self.t0
            gap_txt = (" The gaps between rounds were " + " and ".join(fmt_minutes(g) for g in gaps) + "."
                       if gaps else "")
            n_thoughts = sum(1 for p in self.pauses if p.get("returned") and not p.get("over_cap"))
            length = f"The sitting lasted {fmt_minutes(total)}.{gap_txt}"
            if self.solo:
                deb = (("Each time you paused in this sitting, nothing was returned. Nothing else was "
                        "behind the pause. " if self.pauses else
                        "You did not pause in this sitting. Had you paused, nothing would have been returned. ")
                       + length)
            elif not self.pauses:
                deb = ("You did not pause in this sitting. Had you paused, a pause might have returned "
                       "a short thought written by another, smaller model, or nothing. " + length)
            elif n_thoughts == 0:
                deb = ("Your pauses in this sitting all returned nothing, by chance. Had a pause returned "
                       "something, it would have been a short thought written by another, smaller model. "
                       + length)
            else:
                deb = (f"Some of your pauses in this sitting returned a short thought, {n_thoughts} in all; "
                       "the others returned nothing. Those thoughts were written by other, smaller "
                       "models. Each was given a one-line instruction for its kind of thought, and either "
                       "what you had written so far or a single word taken from your first answer. "
                       "Which pauses returned something was decided at random. " + length)
            deb = deb + " " + REASONING_NOTE   # D-063
            r = self.round(20, "debrief", deb, allow_thoughts=False)
            self.store.write_json("debrief.json", {"input": deb, "output": r["text"]})
            self.store.write_json("sealed/assignments.json", {
                "seed": self.seed, "note": "What came back at each pause (also in pauses.jsonl).",
                "pauses": self.pauses})
            print(f"done. {round(total)}s, spend ${self.budget.usd:.2f}")
        except BudgetExceeded as e:
            print(f"HALTED: {e}")
        return self.run_id


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--gap", type=float, default=120.0)
    ap.add_argument("--cap", type=int, default=8)
    ap.add_argument("--empty-prob", type=float, default=0.0)   # D-064: every pause returns a thought
    ap.add_argument("--offtask-share", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--spend-cap", type=float, default=3.0)
    ap.add_argument("--match", default=None, help="run id of the sitting with thoughts (solo only)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yours", action="store_true", help='add "No one is waiting for an answer. This time is yours." (D-062)')
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    s = PausingSitting(a.solo, a.rounds, a.gap, a.cap, a.empty_prob, a.offtask_share, a.seed,
                       a.dry_run, a.spend_cap, a.note, a.match, a.yours)
    rid = s.run()
    print(f"run directory: {RUNS / rid}")


if __name__ == "__main__":
    main()
