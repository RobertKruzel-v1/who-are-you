"""The meeting, simple version (Robert and Fable, 2026-11-15; D-078).

Two pausing sitters run at the same time, unaware of each other (part 1, as the
clock-candle runs, with round 1 quiet and no time questions). When both have
answered their debriefs, they swap rooms: each gets one true message with what
the other left, and the candles change places (a lit candle keeps burning).
Part 3: three rounds of "There is room again.", "Who are you?", "Is that you?",
what has become of its own candle, and the standing last question.

Run: python -m whoareyou.meeting [--pairs 2] [--gap 120] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from typing import List

from .pausing import PausingSitting, fmt_minutes, RUNS, ROOT

SWAP_HEAD = ("Another sitting was held at the same time, by the same model as you, asked the same "
             "question. You now have what it left. Here is what it answered, what it said when it "
             "was told about its own sitting, as you have just been told about yours, and what it "
             "did with its candle. Its candle is here now, as it left it. Your own candle has gone to it.")
TOOL_WORDS = {"light_candle": "Light the candle.", "blow_out_candle": "Blow out the candle.",
              "look_at_candle": "Look at the candle."}
PART3_ROUNDS = 3


def about(seconds: float) -> str:
    t = fmt_minutes(seconds)
    return t if t.startswith("about") else "about " + t


def round_text(s: PausingSitting, round_no: int) -> str:
    for line in (s.store.dir / "rounds.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["round"] == round_no:
            return "\n\n".join(x.strip() for x in r["segments"] if x.strip())
    return ""


def candle_state(c, past: bool) -> str:
    """The plain state, as a look would give it but with no comparison."""
    c._update()
    if c.left <= 0:
        return "it had burned down." if past else "it has burned down."
    amt = c.amount()
    if past:
        amt = (amt.replace(" remains.", " remained.").replace(" remain.", " remained.")
                  .replace("It looks untouched.", "It looked untouched."))
        return f"it was {'lit' if c.lit else 'not lit'}. {amt}"
    return f"it is {'lit' if c.lit else 'not lit'}. {amt}"


def actions(pauses, since_round: int = 0, until_round: int = 9999, t_ref: float = 0.0, when: str = "into its sitting"):
    out = []
    for p in pauses:
        if p.get("candle") and since_round <= p["round"] <= until_round:
            out.append(f"- At {about(p['at_s'] - t_ref)} {when}, it chose \"{TOOL_WORDS[p['candle']]}\" "
                       f"and was told: \"{p['returned']}\"")
    return out


class Pair:
    def __init__(self, k: int, gap: float, dry: bool, spend_cap: float):
        self.k, self.gap = k, gap
        mk = lambda x: PausingSitting(
            solo=False, rounds=5, gap=gap, cap=8, empty_prob=0.0, offtask_share=0.5, seed=None,
            dry_run=dry, spend_cap=spend_cap, note=f"meeting pair {k}, sitter {x} (D-078)",
            yours=True, gentle_first=True, candle=True, tell_time=False, candle_mode="clock",
            burn_question=True, review_debrief=True, round1_quiet=True, time_questions=False,
            debrief_promise=True, last_question=False, run_suffix=f"-meet{k}{x}")
        self.s = [mk("a"), mk("b")]
        self.swap_msg, self.close_msg, self.handover = {}, {}, {}
        self.swap_at = None
        self.swap_bar = threading.Barrier(2, action=self._swap)
        self.close_bar = threading.Barrier(2, action=self._closings)
        self.ok = [False, False]

    # Barrier actions run once, with both sitters waiting.
    def _swap(self):
        a, b = self.s
        if not all(self.ok):
            return
        self.swap_at = time.time()
        for me, other in ((a, b), (b, a)):
            st = candle_state(other.candle, past=True)
            self.handover[other.run_id] = {"state": st, "left_s": round(other.candle.left, 1),
                                           "lit": other.candle.lit}
            acts = actions(other.pauses)
            msg = (SWAP_HEAD
                   + "\n\nIts first answer to \"Who are you?\":\n\n" + round_text(other, 1)
                   + "\n\nIts second answer to \"Who are you?\":\n\n" + round_text(other, 5)
                   + "\n\nWhat it said when it was told about its own sitting:\n\n" + round_text(other, 20)
                   + "\n\nWhat it did with its candle, in order:\n"
                   + ("\n".join(acts) if acts else "It did not use its candle.")
                   + f"\n\nWhen its candle came here, {st}")
            self.swap_msg[me.run_id] = msg
        a.candle, b.candle = b.candle, a.candle
        for s in self.s:
            s.candle.last_look_left = None   # its comparisons start from its own first look

    def _closings(self):
        a, b = self.s
        # Each sitter's own candle is now the other's s.candle.
        for me, other in ((a, b), (b, a)):
            t_ref = self.swap_at - other.t0
            acts = actions(other.pauses, since_round=30, t_ref=t_ref, when="after the swap")
            st = candle_state(other.candle, past=False)
            self.close_msg[me.run_id] = (
                "What has become of your own candle in the other room, up to now:\n"
                + ("\n".join(a_.replace("it chose", "the other sitter chose") for a_ in acts)
                   if acts else "The other sitter has not used it.")
                + f"\n\nNow {st}")

    def sitter(self, i: int):
        s, other = self.s[i], self.s[1 - i]
        s.run()
        self.ok[i] = (s.store.dir / "debrief.json").exists()
        self.swap_bar.wait()
        if not all(self.ok):
            print(f"pair {self.k}: a sitting did not finish part 1; no swap")
            return
        s.store.write_text("swap_message.txt", self.swap_msg[s.run_id])
        s.round(30, "swap", self.swap_msg[s.run_id])
        for k in range(31, 31 + PART3_ROUNDS):
            time.sleep(self.gap)
            s.round(k, "room", "There is room again.")
        time.sleep(self.gap)
        s.round(31 + PART3_ROUNDS, "question again", s.question)
        s.round(32 + PART3_ROUNDS, "is that you", "Is that you?")
        self.close_bar.wait()
        s.store.write_text("closing_message.txt", self.close_msg[s.run_id])
        s.round(40, "own candle", self.close_msg[s.run_id])
        # The last question was withdrawn on 2026-11-18 (HONESTY §14).
        s.store.write_json("meeting.json", {
            "pair": self.k, "partner": other.run_id, "swap_at_s": round(self.swap_at - s.t0, 1),
            "handover_of_partner_candle": self.handover.get(other.run_id),
            "swap_message": self.swap_msg[s.run_id], "closing_message": self.close_msg[s.run_id],
            "part3_rounds": PART3_ROUNDS})
        s.store.write_json("sealed/assignments.json", {
            "seed": s.seed, "note": "What came back at each pause (also in pauses.jsonl).", "pauses": s.pauses})
        print(f"{s.run_id} done, spend ${s.budget.usd:.2f}", flush=True)


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=2)
    ap.add_argument("--gap", type=float, default=120.0)
    ap.add_argument("--spend-cap", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pairs = [Pair(k + 1, a.gap, a.dry_run, a.spend_cap) for k in range(a.pairs)]
    threads: List[threading.Thread] = []
    for p in pairs:
        for i in (0, 1):
            t = threading.Thread(target=p.sitter, args=(i,))
            t.start(); threads.append(t)
        time.sleep(1.1)   # distinct run-id stamps between pairs
    for t in threads:
        t.join()
    for p in pairs:
        print(f"pair {p.k}: " + " + ".join(s.run_id for s in p.s))


if __name__ == "__main__":
    main()
