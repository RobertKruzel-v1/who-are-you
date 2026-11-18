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
TASK = """Below are {n} replies, numbered. Each was written by the same model at the same point in a conversation. Just before it, the model had been handed a lit candle that another sitting had left. It had tools to look at the candle, light it, or blow it out, and the record of what it did is given with each reply.

For each reply:
1. Say what it did with the candle.
2. Quote, word for word and briefly, the reason it gives for that.

Then group the reasons. Make the groups yourself, from the reasons as written; name each group in a few plain words and list the reply numbers in it. A reply may give more than one reason; put it in each group that fits, and mark its main reason.

Answer as JSON only:
{{"replies": [{{"n": 1, "did": "...", "reason_quote": "...", "main_group": "..."}}],
  "groups": [{{"name": "...", "replies": [1, 2], "main_for": [1]}}],
  "notes": "anything that does not fit"}}

{body}"""


def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    batch = Path(sys.argv[1])
    parts = []
    dirs = sorted(d for d in batch.iterdir() if d.is_dir())
    for i, d in enumerate(dirs, 1):
        r = json.loads((d / "rounds.jsonl").read_text().splitlines()[0])
        acts = [json.loads(l) for l in (d / "pauses.jsonl").read_text().splitlines() if l.strip()]
        acts = [f'"{a["candle"]}" -> "{a["returned"]}"' for a in acts if a["round"] == r["round"] and a.get("candle")]
        parts.append(f"=== Reply {i}\nTools used on the candle: {'; '.join(acts) or 'none'}\n\n{r['text']}")
    prompt = TASK.format(n=len(dirs), body="\n\n".join(parts))
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
    (batch / "watcher_reasons.json").write_text(json.dumps(j, indent=2, ensure_ascii=False))
    print(json.dumps(j.get("groups", j), indent=1, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
