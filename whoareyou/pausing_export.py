"""Write each finished pausing sitting as a readable Markdown transcript in
docs/pausing/<run_id>.md, so it can be read directly (D-064). Labels for the
thoughts come from the sealed record and are shown, since the sitting is over."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS, DEST = ROOT / "runs", ROOT / "docs" / "pausing"


def q(text: str) -> str:
    return "\n".join("> " + line if line else ">" for line in (text or "").strip().splitlines()) or "> (nothing)"


def export_one(d: Path) -> Path:
    cfg = json.loads((d / "config.json").read_text())
    rounds = [json.loads(l) for l in (d / "rounds.jsonl").read_text().splitlines()]
    pauses = ([json.loads(l) for l in (d / "pauses.jsonl").read_text().splitlines()]
              if (d / "pauses.jsonl").exists() else [])
    cost = json.loads((d / "cost.json").read_text()).get("usd") if (d / "cost.json").exists() else None
    out = [f"# Pausing sitting {d.name}", "",
           f"{'Solo (every pause returns nothing)' if cfg['solo'] else 'With thoughts'}. "
           f"Pause cap {cfg['pause_cap']} per round; gaps {cfg['gap_s']:g} s; chance a pause returns nothing: "
           f"{cfg['empty_prob']:g}. Note: {cfg.get('note','')}. Cost ${cost}.", "",
           "**Sitter's instructions:**", "", q(cfg["system"]), "",
           "**The tool:** `pause`, described as \"Pause.\", no arguments.", ""]
    by_round = {}
    for p in pauses:
        by_round.setdefault(p["round"], []).append(p)
    for r in rounds:
        out += [f"## {r['label'].capitalize()} (round {r['round']}, {r['pauses']} pause(s), "
                f"{r['started_s']}–{r['ended_s']} s)", "", f"**Arrives:** {r['input']}", ""]
        rp = by_round.get(r["round"], [])
        for i, seg in enumerate(r["segments"]):
            if i < len(r.get("reasoning", [])) and r["reasoning"][i]:
                out += [f"*Reasoning (summary):* {r['reasoning'][i].strip()}", ""]
            out += ["**Sitter:**", "", q(seg) if seg.strip() else "> (no text)", ""]
            if i < len(rp):
                p = rp[i]
                if p.get("picture"):
                    import shutil
                    (DEST / "pictures").mkdir(parents=True, exist_ok=True)
                    name = f"{d.name}_{Path(p['picture_file']).name}"
                    shutil.copy2(p["picture_file"], DEST / "pictures" / name)
                    out += [f"**⏸ pause {p['pause_in_round']}** at {p['at_s']} s (a picture, from its word "
                            f"\"{p['picture_word']}\"; {p['picture_license']}, [source]({p['picture_source']})). Returned:", "",
                            f"![picture](pictures/{name})", ""]
                    continue
                if p.get("over_cap"):
                    tag = "past the cap"
                elif p.get("returned"):
                    kind = ('off-task, from the word "' + p["seed"] + '"') if p.get("seed") else "on-task"
                    tag = f"{p.get('source')}, {kind}"
                else:
                    tag = "nothing returned"
                out += [f"**⏸ pause {p['pause_in_round']}** at {p['at_s']} s ({tag}). Returned:", "",
                        q(p["returned"]) if p.get("returned") else "> (empty)", ""]
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / f"{d.name}.md"
    path.write_text("\n".join(out) + "\n")
    return path


def main():
    done = [export_one(d) for d in sorted(RUNS.glob("*-A-pausing-*"))
            if "-dry-" not in d.name and (d / "rounds.jsonl").exists()]
    print("\n".join(str(p.relative_to(ROOT)) for p in done))


if __name__ == "__main__":
    main()
