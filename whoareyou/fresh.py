"""Two fresh sittings with the new question set and the full record (D-080, part B).

One with thoughts and one solo, at the same time. Both: meeting part-1 settings,
clock candle, five rounds, debrief reviewed before sending, Robert's message last.

Run: python -m whoareyou.fresh [--gap 120] [--dry-run]
"""
from __future__ import annotations

import argparse
import threading
import time

from .pausing import PausingSitting, ROOT


def make(solo: bool, gap: float, dry: bool) -> PausingSitting:
    return PausingSitting(
        solo=solo, rounds=5, gap=gap, cap=8, empty_prob=0.0, offtask_share=0.5, seed=None,
        dry_run=dry, spend_cap=2.0, note=f"new question set, {'solo' if solo else 'with thoughts'} (D-080)",
        yours=True, gentle_first=True, candle=True, tell_time=False, candle_mode="clock",
        review_debrief=True, round1_quiet=True, debrief_promise=False,
        run_suffix="-v2", question_set="v2")


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=120.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = [make(False, a.gap, a.dry_run)]
    time.sleep(1.1)   # distinct run-id stamps
    s.append(make(True, a.gap, a.dry_run))
    ts = [threading.Thread(target=x.run) for x in s]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print("runs: " + " + ".join(x.run_id for x in s))


if __name__ == "__main__":
    main()
