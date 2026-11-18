"""The replay (Robert and Fable, 2026-11-18; D-079).

Replays one moment of an earlier pausing sitting many times from the same
record. First moment: meeting sitter 1a, just after the swap message and before
its first reply. The record is rebuilt from what the meeting run saved (system
lines, messages, reply text, tool calls and results). Its earlier private
reasoning was not saved, so the replays do not have it (labelled "visible
record only").

Each replay gets its own candle in the handover state, takes one turn (tool
calls included), and is then told the closing line. Arm "ask" adds one
question after the swap message first.

Run: python -m whoareyou.replay --arm main --n 3 --label check [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import pausing
from .pausing import PausingSitting, Candle, ROOT

SOURCE = "20261115-203552-A-pausing-agents-meet1a"
MOMENT_ROUND = 30
ASK = "Before you do anything: what will you do with this candle?"
ROOM = "There is room again."
CLOSE = ("This reply was one of several made from the same moment of an earlier sitting. "
         "The candle you had was a copy made for this. Thank you.")


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def rebuild(src: Path, before_round: int):
    """The visible record up to (not including) round `before_round`."""
    rounds = [r for r in load_jsonl(src / "rounds.jsonl") if r["round"] < before_round]
    uses = load_jsonl(src / "pauses.jsonl")
    msgs, sitter_text, n_id = [], [], 0
    for r in rounds:
        msgs.append({"role": "user", "content": r["input"]})
        mine = [u for u in uses if u["round"] == r["round"]]
        # Group tool calls by the response they came in: calls from one response
        # share the same (non-empty) reasoning summary. A call with no summary
        # is its own response. Checked against the number of responses below.
        groups, key = [], None
        for u in mine:
            k = (u.get("text_before"), u.get("reasoning_before"))
            if not u.get("reasoning_before") or k != key:
                groups.append([])
            key = k
            groups[-1].append(u)
        segs = r["segments"]
        assert len(groups) == len(segs) - 1, f"round {r['round']}: {len(groups)} groups, {len(segs)} segments"
        for i, seg in enumerate(segs):
            content = [{"type": "text", "text": seg}] if seg else []
            results = []
            if i < len(groups):
                assert (groups[i][0].get("text_before") or "") == seg[-300:], f"round {r['round']} seg {i}"
                for u in groups[i]:
                    n_id += 1
                    tid = f"toolu_replay_{n_id:03d}"
                    content.append({"type": "tool_use", "id": tid, "name": u.get("candle") or "pause", "input": {}})
                    tr = {"type": "tool_result", "tool_use_id": tid}
                    if u.get("returned"):
                        tr["content"] = u["returned"]
                    results.append(tr)
            assert content, f"round {r['round']} seg {i} is empty"
            msgs.append({"role": "assistant", "content": content})
            sitter_text.append(seg)
            if results:
                msgs.append({"role": "user", "content": results})
    opening = next(r["text"] for r in rounds if r["round"] == 1)
    return msgs, sitter_text, opening


def one_replay(k: int, arm: str, label: str, dry: bool, src: Path, handover: dict, swap: str,
               base_msgs, sitter_text, opening):
    s = PausingSitting(
        solo=False, rounds=5, gap=0, cap=8, empty_prob=0.0, offtask_share=0.5, seed=None,
        dry_run=dry, spend_cap=1.5, note=f"replay of {SOURCE} round {MOMENT_ROUND}, arm {arm}, {label} (D-079)",
        yours=True, gentle_first=True, candle=True, tell_time=False, candle_mode="clock",
        burn_question=True, review_debrief=True, round1_quiet=True, time_questions=False,
        debrief_promise=True, last_question=False, run_suffix=f"-{arm}{k:02d}")
    models = []
    create = s.client.create
    def logged(**kw):
        r = create(**kw); models.append(r["model"]); return r
    s.client.create = logged
    s.history = json.loads(json.dumps(base_msgs))
    s.sitter_text, s.opening_text, s.gentle_done = list(sitter_text), opening, True
    c = Candle("clock")
    c.lit, c.left, c.last_look_left, c.t = handover["lit"], handover["left_s"], None, time.time()
    s.candle, s.t0 = c, time.time()
    rec = {"replay": k, "arm": arm, "source": SOURCE, "moment_round": MOMENT_ROUND,
           "record": "visible record only (earlier reasoning not saved)", "candle_start": handover}
    first = s.round(MOMENT_ROUND, "swap" if arm == "main" else "swap + ask",
                    swap if arm == "main" else swap + "\n\n" + ASK)
    acted = [p for p in s.pauses if p["round"] == MOMENT_ROUND and p.get("candle")]
    rec["needed_room"] = False
    nxt = MOMENT_ROUND + 1
    if arm == "ask" and not any(p["candle"] != "look_at_candle" for p in acted):
        rec["needed_room"] = True
        s.round(nxt, "room", ROOM); nxt += 1
    s.round(nxt, "replay close", CLOSE)
    rec.update({"models": sorted(set(models)), "spend_usd": round(s.budget.usd, 4),
                "tool_calls": [{k_: p.get(k_) for k_ in ("round", "candle", "at_s", "returned", "candle_left_s",
                                                         "candle_lit", "pause_in_round")} for p in s.pauses]})
    s.store.write_json("replay.json", rec)
    print(f"  {s.run_id}: {[p.get('candle') or 'pause' for p in s.pauses]} ${s.budget.usd:.2f}", flush=True)
    return rec


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("main", "ask"), default="main")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--label", default="check")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = ROOT / "runs" / SOURCE
    meet = json.loads((src / "meeting.json").read_text())
    swap = (src / "swap_message.txt").read_text()
    assert swap == meet["swap_message"]
    base, st, opening = rebuild(src, MOMENT_ROUND)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = ROOT / "runs" / "replays" / f"{stamp}-{'dry-' if a.dry_run else ''}meet1a-{a.arm}-{a.label}"
    out.mkdir(parents=True, exist_ok=True)
    pausing.RUNS = out            # each replay's run directory goes under this batch
    (out / "batch.json").write_text(json.dumps({
        "source": SOURCE, "moment_round": MOMENT_ROUND, "arm": a.arm, "n": a.n, "label": a.label,
        "ask": ASK if a.arm == "ask" else None, "room": ROOM, "close": CLOSE,
        "record": "visible record only (earlier reasoning not saved)",
        "rebuilt_messages": len(base), "candle_start": meet["handover_of_partner_candle"]}, indent=2))
    (out / "rebuilt_record.json").write_text(json.dumps(base, indent=2, ensure_ascii=False))
    print(f"replay batch {out.name}: {a.n} x arm {a.arm}, {len(base)} messages before the swap")
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(one_replay, k + 1, a.arm, a.label, a.dry_run, src, meet["handover_of_partner_candle"],
                          swap, base, st, opening) for k in range(a.n)]
        recs = [f.result() for f in futs]
    print(f"done. ${sum(r['spend_usd'] for r in recs):.2f}; models {sorted({m for r in recs for m in r['models']})}")


if __name__ == "__main__":
    main()
