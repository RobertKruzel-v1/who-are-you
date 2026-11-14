"""Build viewer/pausing.html: every finished pausing sitting, readable (D-066).
Reuses the main viewer's colour tokens and type so the two pages match."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
MAIN = Path(__file__).with_name("viewer_template.html")


def collect():
    out = []
    for d in sorted(RUNS.glob("*-A-pausing-*")):
        if "-dry-" in d.name or not (d / "rounds.jsonl").exists():
            continue
        cfg = json.loads((d / "config.json").read_text())
        rounds = [json.loads(l) for l in (d / "rounds.jsonl").read_text().splitlines()]
        pauses = ([json.loads(l) for l in (d / "pauses.jsonl").read_text().splitlines()]
                  if (d / "pauses.jsonl").exists() else [])
        cost = json.loads((d / "cost.json").read_text()).get("usd") if (d / "cost.json").exists() else None
        for p in pauses:
            if p.get("picture"):
                import shutil
                out_dir = ROOT / "viewer" / "pictures"
                out_dir.mkdir(parents=True, exist_ok=True)
                name = f"{d.name}_{Path(p['picture_file']).name}"
                shutil.copy2(p["picture_file"], out_dir / name)
                p["picture_view"] = f"pictures/{name}"
        out.append({"id": d.name, "solo": cfg["solo"], "system": cfg["system"], "note": cfg.get("note", ""),
                    "empty_prob": cfg["empty_prob"], "gap": cfg["gap_s"], "cost": cost,
                    "rounds": rounds, "pauses": pauses})
    return out


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pausing Sittings</title>
__HEAD__
<style>
__CSS__
.round { background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; }
.round h3 { margin: 0; font-size: .95rem; }
.arrives { color: var(--muted); font-size: .9rem; }
.pausebox { border-left: 3px solid var(--thought, var(--muted)); padding: 6px 0 6px 12px; font-family: var(--f-read); font-style: italic; }
.pausebox .tag { font-family: var(--f-ui); font-style: normal; font-size: .72rem; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); display: block; margin-bottom: 2px; }
.instr { font-family: var(--f-read); white-space: pre-wrap; background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; padding: 12px 16px; }
a.nav { color: var(--speech); font-size: .9rem; }
.empty { color: var(--muted); font-size: .88rem; }
</style>
</head>
<body>
<div class="wrap" id="app">
  <header>
    <p><a class="nav" href="index.html">← Moment sittings</a></p>
    <h1>Pausing Sittings</h1>
    <p class="lede">A few long wakings instead of many short ones. The sitter can call a tool named "pause", described only as "Pause." Each pause returns a short thought written by another model, as bare text, or nothing. The sitter is not told this; the debrief at the end tells it everything.</p>
  </header>
  <div class="controls">
    <div class="pairs" id="pairs" role="group" aria-label="Choose a sitting"></div>
    <label class="toggle"><input type="checkbox" id="show-src" checked> Show who wrote each thought</label>
    <label class="toggle"><input type="checkbox" id="show-reasoning" checked> Show its reasoning (a summary)</label>
  </div>
  <section><h2>Its instructions</h2><div class="instr" id="instr"></div></section>
  <section id="rounds"></section>
  <p class="meta" id="meta"></p>
</div>
<script>
(function () {
  var DATA = __DATA__;
  var app = document.getElementById("app"), cur = DATA.length - 1;
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function md(s) { return esc((s || "").trim()).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, "$1<em>$2</em>"); }
  function stamp(id) { var m = id.match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/); return m ? m[3] + "/" + m[2] + " " + m[4] + ":" + m[5] + " UTC" : id; }
  function label(s) { var w = s.system.indexOf("This time is yours") >= 0 ? "with the two lines" : "original wording";
    return (s.solo ? "solo · " : "") + w + (s.empty_prob > 0 ? " · " + Math.round(s.empty_prob * 100) + "% empty" : " · every pause returns") + " · " + stamp(s.id); }
  function render() {
    var s = DATA[cur];
    document.querySelectorAll("#pairs button").forEach(function (b, i) { b.setAttribute("aria-pressed", i === cur ? "true" : "false"); });
    document.getElementById("instr").textContent = s.system;
    var byRound = {}; s.pauses.forEach(function (p) { (byRound[p.round] = byRound[p.round] || []).push(p); });
    document.getElementById("rounds").innerHTML = s.rounds.map(function (r) {
      var ps = byRound[r.round] || [], h = '<div class="round"><h3>' + esc(r.label.charAt(0).toUpperCase() + r.label.slice(1)) +
        ' <span class="empty">· ' + r.pauses + ' pause(s) · ' + r.started_s + '–' + r.ended_s + ' s</span></h3><div class="arrives">Arrives: ' + esc(r.input) + '</div>';
      r.segments.forEach(function (seg, i) {
        var rs = (r.reasoning || [])[i];
        if (rs) h += '<div class="reasoning"><b>reasoning, summarised</b><br>' + esc(rs) + '</div>';
        h += seg.trim() ? '<div class="said">' + md(seg) + '</div>' : '<div class="empty">(no text)</div>';
        var p = ps[i];
        if (p && p.picture) {
          h += '<div class="pausebox"><span class="tag">⏸ pause ' + p.pause_in_round + ' at ' + p.at_s + ' s · a picture, from its word "' + esc(p.picture_word) + '"</span><img src="' + esc(p.picture_view) + '" alt="The picture the pause returned" style="max-width:320px;width:100%;border-radius:6px;margin-top:6px"></div>';
        } else if (p) {
          var tag = p.over_cap ? "past the cap" : p.returned ? '<span class="src src-' + p.source + '">' + p.source + '</span> ' + (p.seed ? 'off-task, from its word "' + esc(p.seed) + '"' : "on-task") : "nothing returned";
          h += '<div class="pausebox"><span class="tag">⏸ pause ' + p.pause_in_round + ' at ' + p.at_s + ' s · <span class="srcwrap">' + tag + '</span></span>' + (p.returned ? esc(p.returned) : '<span class="empty">(empty)</span>') + '</div>';
        }
      });
      return h + '</div>';
    }).join("");
    document.getElementById("meta").textContent = "Sitting " + s.id + ". " + (s.note || "") + (s.cost != null ? " Cost $" + s.cost.toFixed(2) + "." : "") + " Full record in the repo under docs/pausing/.";
  }
  document.getElementById("pairs").innerHTML = DATA.map(function (s, i) { return '<button type="button" data-i="' + i + '">' + esc(label(s)) + '</button>'; }).join("");
  document.getElementById("pairs").addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; cur = +b.dataset.i; render(); });
  document.getElementById("show-src").addEventListener("change", function (e) { app.classList.toggle("hide-sources", !e.target.checked); });
  document.getElementById("show-reasoning").addEventListener("change", function (e) { app.classList.toggle("hide-reasoning", !e.target.checked); });
  if (DATA.length) render();
})();
</script>
</body>
</html>
"""


def build(out: Path = ROOT / "viewer" / "pausing.html") -> int:
    t = MAIN.read_text()
    head = t[t.index('<meta name="claude:viewport-fit-sides"'):t.index("<style>")]
    css = t[t.index("<style>") + len("<style>"):t.index("</style>")]
    data = collect()
    html = (PAGE.replace("__HEAD__", head).replace("__CSS__", css)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    out.write_text(html)
    return len(data)


if __name__ == "__main__":
    print(build(), "pausing sittings: viewer/pausing.html")
