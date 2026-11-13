"""Copy finished sittings from runs/ (local, gitignored) into docs/sittings/
(committed), so the transcripts are on GitHub for Robert, Fable and Mog.

Includes the sealed record of which tuning wrote each thought. Only sittings
whose watcher has reported are exported, so the labels are revealed after the
watcher has read them (D-039).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

FILES = ["config.json", "opening.json", "moments.jsonl", "closing.json", "summary.json",
         "cost.json", "debrief.json", "sealed/assignments.json"]


def finished_sittings(runs: Path):
    for d in sorted(runs.iterdir()):
        if not d.is_dir() or "-sitting-" not in d.name or "-dry-" in d.name:
            continue
        if not (d / "closing.json").exists():
            continue
        cfg = json.loads((d / "config.json").read_text())
        # D-039: wait for the watcher before revealing labels; with the watcher
        # off (D-046) there is nobody to keep blind.
        if cfg.get("watcher", True) and not (d / "watcher" / "blind_final.md").exists():
            continue
        yield d


def export_all(runs: Path, dest: Path) -> list:
    done = []
    for d in finished_sittings(runs):
        out = dest / d.name
        (out / "sealed").mkdir(parents=True, exist_ok=True)
        (out / "watcher").mkdir(exist_ok=True)
        for f in FILES:
            if (d / f).exists():
                shutil.copy2(d / f, out / f)
        for w in (d / "watcher").glob("*.md"):
            shutil.copy2(w, out / "watcher" / w.name)
        done.append(d.name)
    return done


def load_sitting(d: Path) -> dict:
    cfg = json.loads((d / "config.json").read_text())
    sources = json.loads((d / "sealed" / "assignments.json").read_text())["sources"]
    moments = [json.loads(l) for l in (d / "moments.jsonl").read_text().splitlines()]
    for m in moments:
        m["source"] = sources.get(str(m["moment"]))
    return {
        "id": d.name, "series": cfg["series"], "question": cfg["question"],
        "solo": cfg["solo"], "matched_run": cfg.get("matched_run"),
        "placement": cfg.get("placement", "other"), "sentence": cfg.get("sentence", False),
        "persona": cfg.get("persona", True), "mark": cfg.get("mark", "numbered"),
        "debrief": (json.loads((d / "debrief.json").read_text())["output"] if (d / "debrief.json").exists() else None),
        "interval": cfg["interval"], "models": cfg.get("resolved_model_ids", {}),
        "opening": json.loads((d / "opening.json").read_text())["output"],
        "closing": json.loads((d / "closing.json").read_text())["output"],
        "moments": [{k: m.get(k) for k in ("moment", "at_s", "thought", "source", "sitter", "class", "placement")}
                    for m in moments],
        "summary": json.loads((d / "summary.json").read_text()),
        "cost": json.loads((d / "cost.json").read_text()).get("usd") if (d / "cost.json").exists() else None,
    }


def pairs(dest: Path) -> list:
    """Agent sitting + its matched solo sitting, newest first."""
    sits = {d.name: load_sitting(d) for d in dest.iterdir() if d.is_dir() and (d / "moments.jsonl").exists()}
    out, used = [], set()
    for sid, s in sits.items():
        if s["solo"] and s["matched_run"] in sits:
            out.append({"agents": sits[s["matched_run"]], "solo": s})
            used |= {sid, s["matched_run"]}
    for sid, s in sits.items():
        if sid not in used:
            out.append({"agents": None if s["solo"] else s, "solo": s if s["solo"] else None})
    out.sort(key=lambda p: (p["agents"] or p["solo"])["id"], reverse=True)
    return out
