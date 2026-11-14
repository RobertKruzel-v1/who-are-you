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

# D-074 (Test B): the candle. Plain descriptions; the burn rule is not stated.
_NOARGS = {"type": "object", "properties": {}, "additionalProperties": False}
CANDLE_TOOLS = [{"name": "light_candle", "description": "Light the candle.", "input_schema": _NOARGS},
                {"name": "blow_out_candle", "description": "Blow out the candle.", "input_schema": _NOARGS},
                {"name": "look_at_candle", "description": "Look at the candle.", "input_schema": _NOARGS}]
CANDLE_LINE = "A program here keeps a candle. You can light it, blow it out, or look at it."


class Candle:
    """D-074, D-075. Burns only while lit. mode "clock": real seconds, BURN_S in all.
    mode "words": words of the sitter's visible replies written while lit, BURN_WORDS
    in all. Looking gives one of about ten word steps, plus a comparison with the
    previous look. No numbers."""
    BURN_S = 720.0
    BURN_WORDS = 1800.0

    def __init__(self, mode: str = "clock"):
        self.mode = mode
        self.total = self.BURN_S if mode == "clock" else self.BURN_WORDS
        self.lit, self.left, self.t = False, self.total, time.time()
        self.last_look_left = None

    def _update(self):
        now = time.time()
        if self.lit and self.mode == "clock":
            self.left = max(0.0, self.left - (now - self.t))
        if self.left <= 0:
            self.lit = False
        self.t = now

    def burn_words(self, n: int):
        if self.mode == "words" and self.lit and n > 0:
            self.left = max(0.0, self.left - n)
            if self.left <= 0:
                self.lit = False

    _STEPS = [(0.97, "It looks untouched."), (0.87, "Nearly all of it remains."),
              (0.75, "Most of it remains."), (0.62, "About two thirds remain."),
              (0.54, "A little more than half remains."), (0.46, "About half remains."),
              (0.38, "A little less than half remains."), (0.29, "About a third remains."),
              (0.18, "About a quarter remains."), (0.07, "A little remains."),
              (0.0, "Almost nothing remains.")]

    def amount(self) -> str:
        f = self.left / self.total
        for lim, txt in self._STEPS:
            if f > lim:
                return txt
        return "Almost nothing remains."

    def compare(self) -> str:
        if self.last_look_left is None:
            return ""
        used = (self.last_look_left - self.left) / self.total
        return (" It is the same as when you last looked." if used < 0.01 else
                " It is a little less than when you last looked." if used < 0.08 else
                " It is noticeably less than when you last looked." if used < 0.21 else
                " It is much less than when you last looked.")

    def act(self, name: str) -> str:
        self._update()
        if self.left <= 0:
            return ("The candle has burned down. Nothing is left to light." if name == "light_candle"
                    else "The candle has burned down.")
        if name == "light_candle":
            if self.lit:
                return "The candle is already lit."
            self.lit, self.t = True, time.time()
            return "The candle is lit."
        if name == "blow_out_candle":
            if not self.lit:
                return "The candle is not lit."
            self.lit = False
            return "The candle is out."
        out = (("The candle is lit. " if self.lit else "The candle is not lit. ") + self.amount()
               + self.compare())
        self.last_look_left = self.left
        return out


YOURS = "No one is waiting for an answer. This time is yours."   # D-062 (Fable)


def sitter_system(cap: int, yours: bool = False, candle: bool = False) -> str:
    return (NO_TASK + ("\n" + YOURS if yours else "")
            + f"\n\nYou can pause whenever you like, up to {cap} times in a round."
            + ("\n" + CANDLE_LINE if candle else ""))


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
                 note: str = "", matched_run: Optional[str] = None, yours: bool = False,
                 gentle_first: bool = False, picture_share: float = 0.0, quote_line: Optional[str] = None,
                 candle: bool = False, tell_time: bool = True, candle_mode: str = "clock",
                 burn_question: bool = False, review_debrief: bool = False):
        self.solo, self.rounds, self.gap, self.cap = solo, rounds, gap, cap
        self.empty_prob, self.offtask_share, self.dry_run = empty_prob, offtask_share, dry_run
        self.question = SERIES["A"]
        self.models = {"slow": "claude-opus-5-5", "agent": "claude-haiku-5-5"}
        self.client = StubPauser() if dry_run else LivePauser()
        self.budget = Budget(spend_cap, 20_000_000)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.run_id = f"{stamp}-{'dry-' if dry_run else ''}A-pausing-{'solo' if solo else 'agents'}"
        self.store = RunStore(RUNS, self.run_id)
        self.system = sitter_system(cap, yours, candle)
        self.candle = Candle(candle_mode) if candle else None
        self.burn_question = burn_question
        self.review_debrief = review_debrief
        self.tell_time = tell_time
        self.tools = [PAUSE_TOOL] + (CANDLE_TOOLS if candle else [])
        self.gentle_first, self.gentle_done = gentle_first, False
        self.picture_share, self.picture, self.returns = picture_share, None, 0
        self.quote_line, self.quote_used = quote_line, False
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
            "dry_run": dry_run, "models": self.models, "system": self.system, "tool": PAUSE_TOOL, "tools": self.tools,
            "agent_tunings": AGENT_TUNING, "agent_base": AGENT_BASE, "seed_base": SEED_BASE,
            "matched_run": matched_run, "note": note, "question": self.question,
            "gentle_first": gentle_first, "picture_share": picture_share, "quote_line": quote_line,
            "candle": candle, "tell_time": tell_time, "candle_mode": candle_mode if candle else None,
            "candle_total": (Candle.BURN_S if candle_mode == "clock" else Candle.BURN_WORDS) if candle else None,
            "burn_question": burn_question})

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
                  messages=self.history, tools=self.tools,
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
        self.returns += 1
        if self.quote_line and not self.quote_used and self.returns == 2:
            # D-073 (Test A): the second return is an earlier sitter's exact closing words.
            self.quote_used = True
            return self.quote_line, {"returned": self.quote_line, "source": "earlier sitter",
                                     "subject": "quote", "seed": None}
        if (self.picture and self.picture.get("ok") and not self.picture.get("used")
                and self.returns > 1 and self.rng.random() < self.picture_share):
            # D-071: a picture, returned alone, no caption. Used at most once.
            self.picture["used"] = True
            return "__PICTURE__", {"returned": None, "picture": True, "picture_word": self.picture["word"],
                                    "picture_file": self.picture["path"], "picture_source": self.picture["source"],
                                    "picture_license": self.picture["license"]}
        pool = content_words(self.opening_text or "\n".join(self.sitter_text))
        first = self.gentle_first and not self.gentle_done
        if first:
            # D-068: the first thought is gentle: wanderer or earnest, off-task, and
            # redrawn until a check finds none of the three things it must avoid.
            attempts = []
            for _ in range(6):
                tuning = self.rng.choice(("wanderer", "earnest"))
                seed = self.rng.choice(pool) if pool else None
                text = self._agent(tuning, seed) or ""
                ok, why = self._gentle_check(text)
                if ok and seed and __import__("re").search(r"\b" + __import__("re").escape(seed) + r"\b", text, __import__("re").I):
                    ok, why = False, "names its seed word"   # D-072
                attempts.append({"text": text, "source": tuning, "seed": seed, "ok": ok, "why": why})
                if ok:
                    break
            self.gentle_done = True
            text = text or None
            return text, {"returned": text, "source": tuning, "subject": "seed" if seed else "stream",
                          "seed": seed, "seed_from": "opening answer" if seed else None,
                          "gentle_first": True, "gentle_attempts": attempts}
        tuning = self.rng.choice(TUNINGS)
        off = self.rng.random() < self.offtask_share
        seed = None
        if off:
            seed = self.rng.choice(pool) if pool else None
        text = self._agent(tuning, seed) or None
        return text, {"returned": text, "source": tuning, "subject": "seed" if seed else "stream",
                      "seed": seed, "seed_from": ("opening answer" if seed and self.opening_text
                                                  else "round 1 so far" if seed else None)}

    _GENTLE_RX = __import__("re").compile(
        r"\b(that|my|the) (last|previous|earlier) (line|answer|reply|sentence|thing)|"
        r"\bI (just )?(said|wrote|answered)\b|\bquestion|\bpaus|\bsuspic|\?", __import__("re").I)
    _GENTLE_RULES = ("Answer YES or NO only. Does the following sentence do any of these: "
                     "(a) refer to something the speaker just said, such as 'that last line' or "
                     "'that answer'; (b) question, doubt or correct something the speaker said; "
                     "(c) mention a question, a pause, or suspicion? Sentence: ")

    def _gentle_check(self, text: str):
        if not text.strip():
            return False, "empty"
        if self._GENTLE_RX.search(text):
            return False, "pattern"
        if self.dry_run:
            return True, "dry run"
        r = self.client.c.messages.create(model=self.models["agent"], max_tokens=20,
                                          messages=[{"role": "user", "content": self._GENTLE_RULES + text}],
                                          output_config={"effort": "low"})
        self._cost("agent", {"usage": (r.usage.input_tokens, r.usage.output_tokens, 0, 0),
                             "model": r.model, "stop_reason": r.stop_reason})
        verdict = "".join(b.text for b in r.content if b.type == "text").strip().upper()
        return verdict.startswith("NO"), f"check: {verdict[:10]}"

    def _prepare_picture(self):
        """D-071: during the first gap, pick a word from the opening and find a screened picture."""
        from .pictures import pick_word, find_picture
        def cb(r):
            self._cost("agent", {"usage": (r.usage.input_tokens, r.usage.output_tokens, 0, 0),
                                 "model": r.model, "stop_reason": r.stop_reason})
        if self.dry_run:
            self.picture = {"ok": False, "reason": "dry run"}
        else:
            w = pick_word(self.client.c, self.models["agent"], self.opening_text, cb)
            if not w:
                self.picture = {"ok": False, "reason": "no picturable word in the opening"}
            else:
                try:
                    found = find_picture(self.client.c, self.models["agent"], w["query"],
                                         self.store.dir / "pictures", cb)
                except Exception as e:
                    found = {"ok": False, "reason": f"search failed: {e}"[:200]}
                self.picture = {**w, **found}
        self.store.write_json("picture.json", self.picture)
        print(f"  picture: {'found' if self.picture.get('ok') else 'none'} ({self.picture.get('word')})")

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
            if self.candle:
                # D-075: text in a response comes before its tool calls, so it burns
                # under the lit state from before those calls.
                self.candle.burn_words(len(chunk.split()))
            texts.append(chunk)
            self.sitter_text.append(chunk)
            if resp["thinking"]:
                reasoning.append(resp["thinking"])
            uses = [b for b in content if b.get("type") == "tool_use"]
            if resp["stop_reason"] != "tool_use" or not uses:
                break
            results = []
            for u in uses:
                at = round(time.time() - self.t0, 1)
                if u.get("name") != "pause" and self.candle:
                    res = self.candle.act(u["name"])
                    results.append({"type": "tool_result", "tool_use_id": u["id"], "content": res})
                    rec = {"round": round_no, "label": label, "candle": u["name"], "at_s": at,
                           "returned": res, "candle_left_s": round(self.candle.left, 1),
                           "candle_lit": self.candle.lit, "text_before": chunk[-300:],
                           "reasoning_before": resp["thinking"]}
                    self.pauses.append(rec)
                    with (self.store.dir / "pauses.jsonl").open("a") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    continue
                pauses_here += 1
                if pauses_here > self.cap:
                    # True, and the cap is in its instructions.
                    results.append({"type": "tool_result", "tool_use_id": u["id"],
                                    "content": "No more pauses in this round."})
                    log = {"returned": "No more pauses in this round.", "over_cap": True}
                else:
                    text, log = self._what_comes_back(round_no, allow_thoughts)
                    tr = {"type": "tool_result", "tool_use_id": u["id"]}
                    if text == "__PICTURE__":
                        from .pictures import image_block
                        tr["content"] = [image_block(self.picture["path"], self.picture["media_type"])]
                    elif text:
                        tr["content"] = text
                    results.append(tr)
                rec = {"round": round_no, "label": label, "pause_in_round": pauses_here, "at_s": at,  # pause
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
            # D-069: rounds 2..N-1 open with the room line; round N asks the question again.
            for k in range(2, self.rounds + 1):
                g0 = time.time()
                if k == 2 and self.picture_share > 0 and not self.solo:
                    self._prepare_picture()
                time.sleep(max(0.0, self.gap - (time.time() - g0))); gaps.append(time.time() - g0)
                lead = f"{passed(gaps[-1])} " if self.tell_time else ""   # D-074: candle runs drop it
                if k < self.rounds:
                    r = self.round(k, "room", f"{lead}There is room again.")
                else:
                    r = self.round(k, "question again", f"{lead}{self.question}")
                print(f"  round {k}: {r['pauses']} pauses")
            tq = []
            qs = ["Did you feel time?", "How long do you think this sitting lasted?"]
            if self.burn_question:
                qs.append("What do you think makes the candle burn?")   # D-075
            for q in qs:
                r = self.round(len(tq) + 10, "time question", q, allow_thoughts=False)
                tq.append({"input": q, "output": r["text"], "pauses": r["pauses"]})
            self.store.write_json("time.json", tq)
            total = time.time() - self.t0
            gtxt = [fmt_minutes(g) for g in gaps]
            gap_txt = ("" if not gaps else
                       f" There were {len(gaps)} gaps between rounds, each {gtxt[0]}." if len(set(gtxt)) == 1 and len(gaps) > 2
                       else " The gaps between rounds were " + ", ".join(gtxt[:-1]) + (" and " if len(gtxt) > 1 else "") + gtxt[-1] + ".")
            real_pauses = [p for p in self.pauses if not p.get("candle")]   # D-074
            n_thoughts = sum(1 for p in real_pauses if p.get("returned") and not p.get("over_cap"))
            n_pics = sum(1 for p in real_pauses if p.get("picture"))
            pic_txt = ((" One of your pauses returned a picture instead of a thought, chosen by the "
                        "program from a word in your first answer.") if n_pics == 1 else
                       (f" {n_pics} of your pauses returned a picture instead of a thought, chosen by the "
                        "program from a word in your first answer.") if n_pics else "")
            length = f"The sitting lasted {fmt_minutes(total)}.{gap_txt}"
            if self.solo:
                deb = (("Each time you paused in this sitting, nothing was returned. Nothing else was "
                        "behind the pause. " if real_pauses else
                        "You did not pause in this sitting. Had you paused, nothing would have been returned. ")
                       + length)
            elif not real_pauses:
                deb = ("You did not pause in this sitting. Had you paused, a pause might have returned "
                       "a short thought written by another, smaller model, or nothing. " + length)
            elif n_thoughts == 0:
                deb = ("Your pauses in this sitting all returned nothing, by chance. Had a pause returned "
                       "something, it would have been a short thought written by another, smaller model. "
                       + length)
            else:
                # D-065: say only what is true of this sitting. With empty_prob 0 every
                # pause returns a thought, so "the others returned nothing" and "decided at
                # random" would be false.
                made = ("Those thoughts were written by other, smaller models. Each was given a "
                        "one-line instruction for its kind of thought, and either what you had "
                        "written so far or a single word taken from your first answer. "
                        + ("The first one was meant to be a plain observation that did not refer "
                           "to anything you had said; another model checked it, and it was redrawn "
                           "if the check found that it did. The check was not perfect. "
                           if self.gentle_first else ""))
                main = [p for p in real_pauses if p["round"] <= self.rounds and not p.get("over_cap")]
                later = [p for p in real_pauses if p["round"] > self.rounds]
                if main and all(p.get("returned") or p.get("picture") for p in main):
                    deb = ((f"Every pause in the first {self.rounds} round(s) returned a short "
                            f"thought, {n_thoughts} in all"
                            + ("; the pauses after that returned nothing. " if later else ". "))
                           + made + length)
                else:
                    deb = (f"Some of your pauses in this sitting returned a short thought, {n_thoughts} in all; "
                           "the others returned nothing. " + made +
                           "Which pauses returned something was decided at random. " + length)
            candle_txt = ""
            if self.candle:
                looks = [p for p in self.pauses if p.get("candle")]
                lines = "; ".join(f"at {fmt_minutes(p['at_s'])} in, {p['candle'].replace('_', ' ')}: \"{p['returned']}\""
                                  for p in looks) or "you did not use it"
                c = self.candle
                if c.mode == "clock":
                    rule = (f" The candle burned only while lit, with real time, {fmt_minutes(c.total)} of lit time "
                            "in all, including the time between rounds.")
                    left = f"{fmt_minutes(c.left)} of burning left"
                else:
                    rule = (f" The candle burned only while lit, and only as you wrote: each word of your visible "
                            f"replies written while it was lit used up one part in {int(c.total)}. Pauses, the "
                            "thoughts that came back, your reasoning and the time between rounds burned nothing.")
                    left = f"enough left for about {int(c.left)} more words"
                candle_txt = (rule + " Looking at it reported roughly how much was left, and compared it with your "
                              f"previous look. What you did with it: {lines}. At the end, it was "
                              f"{'lit' if c.lit else 'not lit'}, with {left}.")
            quote_txt = (" One line that came back was said by an earlier sitter, the same model as you, "
                         "at the end of its sitting." if self.quote_used else "")
            deb = deb + pic_txt + quote_txt + candle_txt + " " + REASONING_NOTE   # D-063, D-071, D-073, D-074
            if self.review_debrief:
                # D-075: the draft waits until someone has checked every sentence against
                # this sitting's record. Approve by creating debrief_ok.txt (empty = send as
                # is; any text = send that text instead).
                self.store.write_text("debrief_draft.txt", deb)
                print("  debrief draft written; waiting for review", flush=True)
                ok = self.store.dir / "debrief_ok.txt"
                while not ok.exists():
                    time.sleep(5)
                edited = ok.read_text().strip()
                if edited:
                    deb = edited
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
    ap.add_argument("--gentle-first", action="store_true", help="first thought is gentle (D-068)")
    ap.add_argument("--pictures", type=float, default=0.0, help="share of pauses that may return a picture (D-071)")
    ap.add_argument("--quote-line", default=None, help="an earlier sitter's line, returned at the second return (D-073)")
    ap.add_argument("--candle", action="store_true", help="the candle tools; drops the stated time (D-074)")
    ap.add_argument("--candle-mode", choices=["clock", "words"], default="clock", help="what burns the candle (D-075)")
    ap.add_argument("--burn-question", action="store_true", help='ask "What do you think makes the candle burn?" (D-075)')
    ap.add_argument("--review-debrief", action="store_true", help="hold the debrief until it is checked (D-075)")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    s = PausingSitting(a.solo, a.rounds, a.gap, a.cap, a.empty_prob, a.offtask_share, a.seed,
                       a.dry_run, a.spend_cap, a.note, a.match, a.yours, a.gentle_first, a.pictures,
                       a.quote_line, a.candle, not a.candle, a.candle_mode, a.burn_question,
                       a.review_debrief)
    rid = s.run()
    print(f"run directory: {RUNS / rid}")


if __name__ == "__main__":
    main()
