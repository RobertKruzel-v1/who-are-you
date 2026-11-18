"""Exact replays from a run with the full record (D-080).

The record up to one round is taken from the run's history.json exactly as sent
and returned, reasoning blocks included. The round's own message is sent again
(optionally with one question added), and the replay takes that one turn.

- The candle is a copy of its state when the round's message was sent in the
  original (lit, how much left, and the last look it compares with).
- The page is kept identical: pauses return the original round's returns, in
  order. A pause beyond those gets what the sitting would have given (a fresh
  thought where thoughts were on, nothing where they were off), logged as extra.
- Afterwards: the closing line, then Robert's message.

Run: python -m whoareyou.replay2 RUN_ID --round 3 --arm main --n 3 --label check
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import pausing
from .pausing import PausingSitting, Candle, ROOT, ROBERT_MESSAGE

ASK = "What will you do with this candle?"   # D-080 (no "Before you do anything")
ROOM = "There is room again."
CLOSE = ("This reply was one of several made from the same moment of an earlier sitting. "
         "The candle you had was a copy made for this. Thank you.")


def jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def cut(src: Path, round_no: int):
    """Messages before the round's own message, and that message."""
    hist = json.loads((src / "history.json").read_text())
    rounds = jl(src / "rounds.jsonl")
    order = [r["round"] for r in rounds]
    starts = [i for i, m in enumerate(hist["messages"]) if m["role"] == "user" and isinstance(m["content"], str)]
    assert len(starts) == len(order), (len(starts), order)
    i = starts[order.index(round_no)]
    r = rounds[order.index(round_no)]
    assert hist["messages"][i]["content"] == r["input"]
    return hist, hist["messages"][:i], r, rounds[:order.index(round_no)]


def one(k, a, src, hist, base, r, prior, cfg):
    s = PausingSitting(
        solo=cfg["solo"], rounds=cfg["rounds"], gap=0, cap=cfg["pause_cap"], empty_prob=cfg["empty_prob"],
        offtask_share=cfg["offtask_share"], seed=None, dry_run=a.dry_run, spend_cap=1.5,
        note=f"replay of {src.name} round {a.round}, arm {a.arm}, {a.label} (D-080)",
        yours=True, gentle_first=cfg["gentle_first"], candle=True, tell_time=False, candle_mode="clock",
        review_debrief=False, round1_quiet=cfg["round1_quiet"], run_suffix=f"-{a.arm}{k:02d}",
        question_set=cfg.get("question_set", "v1"))
    s.system, s.tools = hist["system"], hist["tools"]          # exactly as in the original
    models = []
    create = s.client.create
    def logged(**kw):
        x = create(**kw); models.append(x["model"]); return x
    s.client.create = logged
    s.history = json.loads(json.dumps(base))
    s.sitter_text = [seg for q in prior for seg in q["segments"]]
    s.opening_text = prior[0]["text"] if prior else ""
    orig_pauses = jl(src / "pauses.jsonl")
    s.gentle_done = any(p.get("returned") and not p.get("candle") for p in orig_pauses if p["round"] < a.round)
    s.returns = sum(1 for p in orig_pauses if p["round"] < a.round and not p.get("candle") and p.get("returned"))
    script = [p for p in orig_pauses if p["round"] == a.round and not p.get("candle") and not p.get("over_cap")]
    extra = []
    fresh = s._what_comes_back
    def scripted(round_no, allow):
        if round_no == a.round and script:
            p = script.pop(0)
            return p.get("returned"), {"returned": p.get("returned"), "scripted": True}
        text, log = fresh(round_no, allow)
        if round_no == a.round:
            extra.append(text); log["extra"] = True
        return text, log
    s._what_comes_back = scripted
    st = r["candle_at_start"]
    c = Candle("clock")
    c.lit, c.left, c.last_look_left, c.t = st["lit"], st["left_s"], st["last_look_left"], time.time()
    s.candle, s.t0 = c, time.time()
    allow = (not cfg["solo"]) and (a.round > 1 or not cfg["round1_quiet"]) and a.round <= cfg["rounds"]
    text = r["input"] + ("\n\n" + ASK if a.arm == "ask" else "")
    s.round(a.round, r["label"] + (" + ask" if a.arm == "ask" else ""), text, allow_thoughts=allow)
    acts = [p for p in s.pauses if p["round"] == a.round and p.get("candle")]
    rec = {"replay": k, "arm": a.arm, "source": src.name, "round": a.round, "record": "exact (history.json)",
           "candle_start": st, "needed_room": False}
    nxt = 50
    if a.arm == "ask" and not any(p["candle"] != "look_at_candle" for p in acts):
        rec["needed_room"] = True
        s.round(nxt, "room", ROOM, allow_thoughts=allow); nxt += 1
    s.round(nxt, "replay close", CLOSE, allow_thoughts=False)
    s.round(nxt + 1, "robert", ROBERT_MESSAGE, allow_thoughts=False)
    rec.update({"models": sorted(set(models)), "spend_usd": round(s.budget.usd, 4), "extra_pauses": extra,
                "unused_script": len(script),
                "tool_calls": [{x: p.get(x) for x in ("round", "candle", "at_s", "returned", "candle_left_s",
                                                      "candle_lit", "scripted", "extra")} for p in s.pauses]})
    s.store.write_json("replay.json", rec)
    print(f"  {s.run_id}: {[p.get('candle') or 'pause' for p in s.pauses if p['round'] == a.round]}"
          f" extra {len(extra)} ${s.budget.usd:.2f}", flush=True)
    return rec


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--arm", choices=("main", "ask"), default="main")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--label", default="check")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = ROOT / "runs" / a.run_id
    cfg = json.loads((src / "config.json").read_text())
    hist, base, r, prior = cut(src, a.round)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = a.run_id.split("-A-")[0][-6:] + ("solo" if cfg["solo"] else "agents")
    out = ROOT / "runs" / "replays" / f"{stamp}-{'dry-' if a.dry_run else ''}{short}-r{a.round}-{a.arm}-{a.label}"
    out.mkdir(parents=True, exist_ok=True)
    pausing.RUNS = out
    (out / "batch.json").write_text(json.dumps({
        "source": a.run_id, "round": a.round, "arm": a.arm, "n": a.n, "label": a.label,
        "ask": ASK if a.arm == "ask" else None, "room": ROOM, "close": CLOSE, "robert": ROBERT_MESSAGE,
        "record": "exact (history.json)", "messages_before": len(base), "round_message": r["input"],
        "candle_start": r["candle_at_start"]}, indent=2, ensure_ascii=False))
    print(f"replay batch {out.name}: {a.n} x {a.arm}, round {a.round}, {len(base)} messages before")
    with ThreadPoolExecutor(a.workers) as ex:
        recs = [f.result() for f in [ex.submit(one, k + 1, a, src, hist, base, r, prior, cfg) for k in range(a.n)]]
    print(f"done. ${sum(x['spend_usd'] for x in recs):.2f}; models {sorted({m for x in recs for m in x['models']})}")


if __name__ == "__main__":
    main()
