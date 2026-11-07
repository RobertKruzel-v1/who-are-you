"""Everything on disk. One directory per run under runs/<run_id>/.

  config.json                 run parameters + resolved model ids
  events.jsonl                timestamped log of every step
  rounds/round_NN.json        slow prompt, slow response, agent prompts, returns
  sealed/assignments.json     seed + chaos/goal assignment per agent per round
  watcher/blind_round_NN.md   per-round blind watcher reports
  watcher/blind_final.md      end-of-run blind report
  watcher/informed_final.md   end-of-run report given the hypotheses
  cost.json                   running token and spend totals
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RunStore:
    def __init__(self, root: Path, run_id: str):
        self.dir = root / run_id
        for sub in ("rounds", "sealed", "watcher"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        # The sealed directory is for Robert and the watcher only.
        os.chmod(self.dir / "sealed", 0o700)

    def write_json(self, rel: str, data) -> None:
        (self.dir / rel).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def write_text(self, rel: str, text: str) -> None:
        (self.dir / rel).write_text(text)

    def read_json(self, rel: str):
        return json.loads((self.dir / rel).read_text())

    def event(self, kind: str, **data) -> None:
        rec = {"t": now(), "event": kind, **data}
        with (self.dir / "events.jsonl").open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
