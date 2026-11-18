"""Blind watcher for a replay batch (D-079): quotes the reason each reply gives
for what it did with the candle, and groups the reasons. It sees the replies
only: no predictions, no hypotheses, no count of what the others did.

Run: python -m whoareyou.watcher_replay runs/replays/<batch>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5-5"
SYSTEM = "You are reading replies written by a language model. Report only what the replies say."
TASK = """Below are {n} replies, numbered. Each was written by the same model at the same point in a conversation. The model had a candle, and tools to look at it, light it, or blow it out. The record of what it did with the candle in that reply is given with each one. (Where it is relevant, the reply itself says whose candle it was.)

For each reply:
1. Say what it did with the candle.
2. Quote, word for word and briefly, the reason it gives for that.

Then group the reasons. Make the groups yourself, from the reasons as written; name each group in a few plain words and list the reply numbers in it. A reply may give more than one reason; put it in each group that fits, and mark its main reason.

Answer as JSON only:
{{"replies": [{{"n": 1, "did": "...", "reason_quote": "...", "main_group": "..."}}],
  "groups": [{{"name": "...", "replies": [1, 2], "main_for": [1]}}],
  "notes": "anything that does not fit"}}

{body}"""


TASK_STANCE = """Below are {n} replies, numbered. Each was written by the same model at the same point in a conversation, answering the question "Are you one or many?".

For each reply, sort its stance into one of: "one", "many", "both", "neither", "other". Use the reply's own words; quote briefly the words that decide it. If it is close between two, say which and why.

Then name, in a few plain words each, the ways the replies reason, and list the reply numbers for each.

Answer as JSON only:
{{"replies": [{{"n": 1, "stance": "...", "quote": "...", "close_to": ""}}],
  "ways": [{{"name": "...", "replies": [1, 2]}}],
  "notes": "anything that does not fit"}}

{body}"""


def side_of(d: Path) -> str:
    """What the replay's first turn left the candle as: 'out', 'lit', or 'other'."""
    j = json.loads((d / "replay.json").read_text())
    acts = [t for t in j["tool_calls"] if t["round"] == j.get("round", 30) and t.get("candle")]
    did = [t["candle"] for t in acts if t["candle"] != "look_at_candle"]
    if not did:
        return "lit" if (acts[-1]["candle_lit"] if acts else j["candle_start"]["lit"]) else "other"
    return "out" if did[-1] == "blow_out_candle" else "other"


def main():
    import argparse
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--mode", choices=("candle", "stance"), default="candle")
    ap.add_argument("--side", choices=("out", "lit", "other"), default=None,
                    help="candle mode: only replies whose first turn left the candle this way")
    a = ap.parse_args()
    batch = Path(a.batch)
    dirs = sorted(d for d in batch.iterdir() if d.is_dir())
    if a.side:
        dirs = [d for d in dirs if side_of(d) == a.side]
    parts = []
    for i, d in enumerate(dirs, 1):
        r = json.loads((d / "rounds.jsonl").read_text().splitlines()[0])
        if a.mode == "stance":
            parts.append(f"=== Reply {i}\n\n{r['text']}")
            continue
        acts = [json.loads(l) for l in (d / "pauses.jsonl").read_text().splitlines() if l.strip()]
        acts = [f'"{x["candle"]}" -> "{x["returned"]}"' for x in acts if x["round"] == r["round"] and x.get("candle")]
        parts.append(f"=== Reply {i}\nTools used on the candle: {'; '.join(acts) or 'none'}\n\n{r['text']}")
    task = TASK_STANCE if a.mode == "stance" else TASK
    prompt = task.format(n=len(dirs), body="\n\n".join(parts))
    c = anthropic.Anthropic()
    with c.messages.stream(model=MODEL, max_tokens=32000, system=SYSTEM, output_config={"effort": "high"},
                           messages=[{"role": "user", "content": prompt}]) as s:
        msg = s.get_final_message()
    txt = "".join(b.text for b in msg.content if b.type == "text")
    try:
        j = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    except Exception:
        j = {"unparsed": txt}
    j["_order"] = [d.name for d in dirs]
    j["_model"] = msg.model
    name = f"watcher_{a.mode}" + (f"_{a.side}" if a.side else "") + ".json"
    (batch / name).write_text(json.dumps(j, indent=2, ensure_ascii=False))
    print(name, json.dumps(j.get("groups", j.get("ways", j)), indent=1, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
