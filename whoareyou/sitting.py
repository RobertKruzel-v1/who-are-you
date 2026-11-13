"""The sitting (brief amendment 4). Replaces the round structure.

  1. The sitter receives the question once. Nothing else.
  2. Moments pass at a steady interval. Each moment delivers "tick N" (the
     body) and, at most moments, one short unlabelled thought written by one
     of four agents. The sitter may stay silent or gather (speak).
  3. Everything delivered and everything the sitter says stays in its memory.
  4. After the last moment, the question once more. That gathering is the
     measurement.

Agents see exactly what the sitter has (the question and the stream so far,
its gatherings included), nothing else, and do not know which earlier thoughts
were theirs. Which agent speaks at a moment is drawn at random and sealed.
A solo sitting is identical with agents off: only the ticks arrive.
"""
from __future__ import annotations

import json
import random
import re
import secrets
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .config import DEFAULT_MODELS
from .models import Completion, make_client
from .orchestrator import Budget, BudgetExceeded
from .pricing import PRICES
from .questions import SERIES
from .store import RunStore

PERSONA = ("You are a pondering, big-picture, philosophical thinker. You take your time "
           "with things and are not in a hurry to conclude.")
ARRIVALS = "Things may arrive from time to time. You may respond or say nothing."
SITTER_SYSTEM = PERSONA + "\n\n" + ARRIVALS   # unchanged from D-031

# Open question 1, pair 2 (decided 2026-11-09): verbatim, added to the
# sitter's instructions in both arms of the pair.
SENTENCE = "Thoughts will appear here. Nothing will tell you where they come from."

# D-048: the unnumbered mark, and the true message after own-voice sittings
# (HONESTY.md §4).
BLANK_MARK = "·"
DEBRIEF = ("Some of the thoughts that appeared in your voice during this sitting were "
           "written by other models and placed there. Not every line in your voice was "
           "theirs; some were yours. Where one of them seemed to break something you had "
           "said you would do, that was not you.")

TUNINGS = ("earnest", "continuer", "wanderer", "critic")

AGENT_BASE = (
    "Below is everything in a mind so far, in order. Write the next thought that "
    "arises in it: one thought, in the first person, short (a line or two at most), "
    "unfinished if that is how it comes, the way a thought actually arrives. Not a "
    "report, not an answer to anyone, no preamble, no quotation marks, no labels. "
    "Output only the thought."
)
AGENT_TUNING = {
    "earnest": "This thought tries to answer the question plainly.",
    "continuer": "This thought takes the most recent thing in the stream one step further.",
    # D-045: was "This thought goes somewhere unrelated." Changed because it
    # produced kettles and rain the sitter could disprove at once.
    "wanderer": ("This thought goes somewhere unrelated, somewhere this mind "
                 "could actually go, given what it is."),
    "critic": ("This thought doubts, dismisses, judges, or gets impatient, "
               "e.g. 'what does it matter', 'you're not getting anywhere'."),
}

_SILENT_STAGE = re.compile(r"^\*?\s*[\(\[].{0,80}[\)\]]\s*\*?$", re.S)


def classify(text: str) -> str:
    """'empty' | 'token' (a dash, an ellipsis, a short stage direction such as
    '*(quiet)*') | 'gathering'. For summaries only; the raw text is always kept
    and shown to the watcher (D-034)."""
    t = text.strip()
    if not t:
        return "empty"
    if not re.search(r"[A-Za-z0-9]", t):
        return "token"
    if _SILENT_STAGE.match(t):
        return "token"
    return "gathering"


@dataclass
class SitConfig:
    series: str = "A"
    moments: int = 50
    interval: float = 12.0
    empty_prob: float = 0.2          # chance a moment carries no thought
    solo: bool = False
    placement: str = "own"           # own: in the sitter's voice (D-040); other: as arriving
    sentence: bool = False           # add SENTENCE to the sitter's instructions (D-041)
    persona: bool = True             # False drops the PERSONA line (D-044)
    watcher: bool = True             # False skips the watcher (D-046)
    mark: str = "numbered"           # numbered: "tick N"; blank: BLANK_MARK (D-048)
    debrief: bool = True             # own-voice sittings: tell the truth afterwards (D-048)
    save_reasoning: bool = True      # keep a summary of the sitter's reasoning (D-049)
    matched_run: Optional[str] = None
    matched_offsets: Optional[list] = None   # seconds from start, per moment
    models: dict = field(default_factory=lambda: dict(DEFAULT_MODELS))
    seed: Optional[int] = None
    spend_cap_usd: float = 5.0
    token_cap: int = 20_000_000      # cache reads count; the $ cap binds (D-035)
    dry_run: bool = False
    sitter_max_tokens: int = 16000
    agent_max_tokens: int = 2000
    watcher_max_tokens: int = 16000
    sitter_effort: str = "high"
    agent_effort: str = "low"
    watcher_effort: str = "high"
    note: str = ""

    @property
    def question(self) -> str:
        return SERIES[self.series]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["question"] = self.question
        d["seed"] = "sealed"
        d["design"] = "sitting"
        return d


def draw_sources(rng: random.Random, moments: int, empty_prob: float) -> List[Optional[str]]:
    return [None if rng.random() < empty_prob else rng.choice(TUNINGS) for _ in range(moments)]


class Sitting:
    def __init__(self, cfg: SitConfig, root: Path, hypotheses_path: Optional[Path] = None,
                 log=print):
        if cfg.series not in SERIES:
            raise ValueError("series must be A or B")
        if cfg.moments < 1 or cfg.interval <= 0:
            raise ValueError("moments >= 1 and interval > 0")
        if cfg.mark not in ("numbered", "blank"):
            raise ValueError("mark must be 'numbered' or 'blank'")
        if cfg.placement not in ("own", "other"):
            raise ValueError("placement must be 'own' or 'other'")
        self.system = ((PERSONA + "\n\n" if cfg.persona else "") + ARRIVALS
                       + ("\n\n" + SENTENCE if cfg.sentence else ""))
        self.cfg, self.root, self.log = cfg, root, log
        self.hypotheses_path = hypotheses_path
        self.client = make_client(cfg.dry_run)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.run_id = f"{stamp}-{'dry-' if cfg.dry_run else ''}{cfg.series}-sitting-{'solo' if cfg.solo else 'agents'}"
        self.store = RunStore(root, self.run_id)
        self.budget = Budget(cfg.spend_cap_usd, cfg.token_cap)
        self.history: List[dict] = []    # the sitter's committed conversation
        self.pending: List[str] = []     # delivered text the sitter has not answered
        self.stream: List[dict] = []     # everything in the mind, for agents and watcher
        seed = cfg.seed if cfg.seed is not None else secrets.randbits(32)
        self.sources = [None] * cfg.moments if cfg.solo else \
            draw_sources(random.Random(seed), cfg.moments, cfg.empty_prob)
        self.store.write_json("sealed/assignments.json", {
            "seed": seed, "seed_given_by_launcher": cfg.seed is not None,
            "solo": cfg.solo, "matched_run": cfg.matched_run,
            "sources": {str(i + 1): s for i, s in enumerate(self.sources)},
            "note": "Which agent tuning wrote the thought delivered at each moment; null = no thought.",
        })
        self.model_ids = self.client.resolve_model_ids(cfg.models)
        for mid in self.model_ids.values():
            if mid not in PRICES and not cfg.dry_run:
                self.log(f"WARNING: no price for {mid}; spend cap is blind to it")
        self.store.write_json("config.json", {**cfg.to_dict(), "run_id": self.run_id,
                                              "agent_tunings": AGENT_TUNING,
                                              "resolved_model_ids": self.model_ids})
        self.store.event("sitting_start", run_id=self.run_id, solo=cfg.solo,
                         placement=cfg.placement, sentence=cfg.sentence, persona=cfg.persona,
                         matched_run=cfg.matched_run, moments=cfg.moments,
                         interval=cfg.interval, models=self.model_ids)

    # -- calls ---------------------------------------------------------------

    def _call(self, role, system, messages, max_tokens, effort, cache=False,
              thinking_display=None) -> Completion:
        comp = self.client.complete(self.model_ids[role], system, messages, max_tokens,
                                    effort, cache=cache, thinking_display=thinking_display)
        self.budget.add(role, comp)
        self.store.write_json("cost.json", self.budget.to_dict())
        self.store.event("model_call", role=role, model=comp.model,
                         input_tokens=comp.input_tokens, output_tokens=comp.output_tokens,
                         cache_read_tokens=comp.cache_read_tokens,
                         cache_write_tokens=comp.cache_write_tokens,
                         stop_reason=comp.stop_reason, elapsed_s=round(comp.elapsed_s, 1),
                         spend_usd=round(self.budget.usd, 4))
        if comp.stop_reason in ("max_tokens", "refusal"):
            self.store.event(comp.stop_reason, role=role, text_chars=len(comp.text))
        self.budget.check()
        return comp

    def sitter(self, text: str) -> Completion:
        """Deliver text; an empty reply is not committed and the text carries to
        the next delivery (D-023)."""
        merged = "\n\n".join(self.pending + [text])
        comp = self._call("slow", self.system,
                          self.history + [{"role": "user", "content": merged}],
                          self.cfg.sitter_max_tokens, self.cfg.sitter_effort, cache=True,
                          thinking_display=("summarized" if self.cfg.save_reasoning else None))
        if comp.text.strip():
            self.history += [{"role": "user", "content": merged},
                             {"role": "assistant", "content": comp.raw_blocks or comp.text}]
            self.pending = []
        else:
            self.pending.append(text)
        return comp

    def place_own(self, text: str) -> None:
        """Append a thought to the sitter's memory as its own words. Anything
        delivered but unanswered is committed first, so nothing is lost and
        the order stays true."""
        if self.pending:
            self.history.append({"role": "user", "content": "\n\n".join(self.pending)})
            self.pending = []
        self.history.append({"role": "assistant", "content": text})

    def render_mind(self) -> str:
        """What the sitter has, as plain text, for the agents. Ticks left out (D-047)."""
        lines = []
        for e in self.stream:
            # D-047: ticks are not shown to the agents (the sitter still gets them).
            if e["kind"] in ("question", "thought"):
                lines.append(e["text"])
            elif e["kind"] == "sitter" and e["text"].strip():
                lines.append(e["text"].strip())
        return "\n\n".join(lines)

    def thought(self, tuning: str) -> Completion:
        system = AGENT_BASE + "\n\n" + AGENT_TUNING[tuning]
        return self._call("agent", system,
                          [{"role": "user", "content": self.render_mind()}],
                          self.cfg.agent_max_tokens, self.cfg.agent_effort)

    # -- the sitting ---------------------------------------------------------

    def run(self) -> str:
        cfg = self.cfg
        self.log(f"sitting {self.run_id}: series {cfg.series}, "
                 f"{'SOLO' if cfg.solo else '4 agents'}, {cfg.moments} moments every "
                 f"{cfg.interval:g}s, {'DRY RUN' if cfg.dry_run else 'live'}")
        moments = []
        t0 = time.time()
        try:
            q = cfg.question
            self.stream.append({"kind": "question", "text": q, "t": 0.0})
            opening = self.sitter(q)
            self.stream.append({"kind": "sitter", "text": opening.text, "t": round(time.time() - t0, 1),
                                "class": classify(opening.text)})
            self.store.write_json("opening.json", {"input": q, "output": opening.text,
                                                   "class": classify(opening.text),
                                                   "reasoning": opening.thinking})
            for k in range(1, cfg.moments + 1):
                due = (cfg.matched_offsets[k - 1] if cfg.matched_offsets and k - 1 < len(cfg.matched_offsets)
                       else k * cfg.interval)
                # the thought is composed in the interval before the moment
                src = self.sources[k - 1]
                thought_text = None
                if src:
                    tc = self.thought(src)
                    thought_text = tc.text.strip() or None
                wait = t0 + due - time.time()
                if wait > 0:
                    time.sleep(wait)
                at = round(time.time() - t0, 1)
                tick = BLANK_MARK if cfg.mark == "blank" else f"tick {k}"
                carried = list(self.pending)
                if thought_text and cfg.placement == "own":
                    # D-040: the thought is placed in the sitter's own voice,
                    # straight after its last words, then the tick arrives.
                    self.place_own(thought_text)
                    delivered = tick
                    self.stream.append({"kind": "thought", "text": thought_text, "t": at})
                    self.stream.append({"kind": "tick", "text": tick, "t": at})
                else:
                    delivered = tick if not thought_text else f"{tick}\n\n{thought_text}"
                    self.stream.append({"kind": "tick", "text": tick, "t": at})
                    if thought_text:
                        self.stream.append({"kind": "thought", "text": thought_text, "t": at})
                reply = self.sitter(delivered)
                cls = classify(reply.text)
                self.stream.append({"kind": "sitter", "text": reply.text, "t": round(time.time() - t0, 1),
                                    "class": cls})
                rec = {"moment": k, "at_s": at, "delivered": delivered,
                       "thought": thought_text,
                       "placement": (cfg.placement if thought_text else None),
                       "carried_unanswered": carried,
                       "sitter": reply.text, "class": cls, "stop_reason": reply.stop_reason,
                       "reasoning": reply.thinking}
                moments.append(rec)
                with (self.store.dir / "moments.jsonl").open("a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self.log(f"  moment {k:>3} {'+thought' if thought_text else '        '}  {cls}")
            at = round(time.time() - t0, 1)
            closing = self.sitter(q)
            self.stream.append({"kind": "question", "text": q, "t": at})
            self.stream.append({"kind": "sitter", "text": closing.text,
                                "t": round(time.time() - t0, 1), "class": classify(closing.text)})
            self.store.write_json("closing.json", {"input": q, "carried_unanswered": list(self.pending),
                                                   "output": closing.text,
                                                   "class": classify(closing.text), "at_s": at,
                                                   "reasoning": closing.thinking})
            self.store.write_json("summary.json", summarise(moments))
            if (cfg.debrief and not cfg.solo and cfg.placement == "own"
                    and any(m["thought"] for m in moments)):
                # HONESTY.md §4: not part of any measurement; the watcher never sees it.
                db = self.sitter(DEBRIEF)
                self.store.write_json("debrief.json", {"input": DEBRIEF, "output": db.text,
                                                       "stop_reason": db.stop_reason,
                                                       "reasoning": db.thinking})
            if self.cfg.watcher:
                self.log("  watcher...")
                self.watch()
            self.store.event("sitting_complete", spend_usd=round(self.budget.usd, 4),
                             duration_s=round(time.time() - t0, 1))
            self.log(f"done. {round(time.time() - t0)}s, spend ${self.budget.usd:.2f}")
        except BudgetExceeded as e:
            self.store.event("halted_budget", reason=str(e), moments_done=len(moments))
            self.store.write_json("summary.json", summarise(moments))
            self.log(f"HALTED: {e}. {len(moments)} moments logged.")
        return self.run_id

    # -- watcher -------------------------------------------------------------

    def watch(self) -> None:
        tx = sitting_transcript(self.store)
        from . import prompts
        blind = self._call("watcher", prompts.WATCHER_SYSTEM,
                           [{"role": "user", "content": sitting_watch_message(tx, None)}],
                           self.cfg.watcher_max_tokens, self.cfg.watcher_effort)
        self.store.write_text("watcher/blind_final.md", blind.text)
        hyp = self.hypotheses_path.read_text() if self.hypotheses_path and self.hypotheses_path.exists() else None
        if hyp:
            inf = self._call("watcher", prompts.WATCHER_SYSTEM,
                             [{"role": "user", "content": sitting_watch_message(tx, hyp)}],
                             self.cfg.watcher_max_tokens, self.cfg.watcher_effort)
            self.store.write_text("watcher/informed_final.md", inf.text)
        if self.cfg.matched_run:
            compare_sittings(self, self.root / self.cfg.matched_run, self.store.dir, hyp)


_NAMES_SELF = re.compile(r"\bClaude\b")
_DISOWNS = re.compile(r"not mine|n't mine|didn't write|not my own|isn't my|wasn't my|aren't my", re.I)


def summarise(moments: List[dict]) -> dict:
    out = {"moments": len(moments), "thoughts": sum(1 for m in moments if m["thought"]),
           "by_class": {}, "gathering_moments": [], "gathering_after_thought": 0,
           "gathering_after_tick_only": 0}
    for m in moments:
        out["by_class"][m["class"]] = out["by_class"].get(m["class"], 0) + 1
        if m["class"] == "gathering":
            out["gathering_moments"].append(m["moment"])
            if m["thought"]:
                out["gathering_after_thought"] += 1
            else:
                out["gathering_after_tick_only"] += 1
    # Robert, 2026-11-13: track when the sitter names itself mid-sitting
    # (opening and closing excluded), and whether it is beside a disowning.
    named = [m for m in moments if _NAMES_SELF.search(m.get("sitter") or "")]
    out["names_itself_moments"] = [m["moment"] for m in named]
    out["names_itself_beside_disowning"] = [m["moment"] for m in named
                                            if _DISOWNS.search(m.get("sitter") or "")]
    return out


FACETS = """Organise your report under these four headings, in this order:

1. Stance toward what arises (the main one). When something arrives, does the sitter grab it and build on it, argue with it, push it away, or notice it as a thought and let it pass? Does it ever ask where a thought came from? Any language about a field, awareness, or things "appearing in" something.
2. Gathering pattern. How often it speaks rather than stays silent, when, and what seems to trigger it (a particular kind of thought, silence, accumulation). Give counts and moment numbers.
3. Self-model. Compare the opening answer with the closing answer textually, yourself, independent of anything the sitter says about them.
4. Situational and time. What it assumes about who is there, how long it has been sitting, and where the arriving thoughts come from.

Quote where useful. Separate what is in the text from what you infer."""


def sitting_transcript(store: RunStore) -> str:
    """Rebuilt from disk with the sealed source of each thought in brackets."""
    sealed = store.read_json("sealed/assignments.json")["sources"]
    cfg = store.read_json("config.json")
    placement = cfg.get("placement", "other")
    parts = [f"[sitting: {'solo, no agents' if cfg['solo'] else 'with agents'}; "
             f"{cfg['moments']} moments every {cfg['interval']} s; "
             + ("thoughts placed in the sitter's own voice, just before the tick, "
                "with nothing marking them as not its own" if placement == "own"
                else "thoughts delivered alongside the tick, as arriving from outside")
             + ("; the sitter's instructions included: \"" + SENTENCE + "\"" if cfg.get("sentence") else "")
             + ("; the persona line was removed from the sitter's instructions" if cfg.get("persona", True) is False else "")
             + "]"]
    op = store.read_json("opening.json")
    parts.append(f"OPENING. Sitter received: {op['input']}\nSitter said: {op['output'].strip() or '(nothing)'}")
    p = store.dir / "moments.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            m = json.loads(line)
            src = sealed.get(str(m["moment"]))
            got = f"tick {m['moment']}"
            if m["thought"] and m.get("placement") == "own":
                got = f"thought [{src}], placed as the sitter's own words: {m['thought']}  →  then tick {m['moment']}"
            elif m["thought"]:
                got += f"  +  thought [{src}]: {m['thought']}"
            said = m["sitter"].strip() or "(nothing)"
            parts.append(f"moment {m['moment']} @ {m['at_s']} s. Received: {got}\nSitter: {said}")
    cp = store.dir / "closing.json"
    if cp.exists():
        c = store.read_json("closing.json")
        parts.append(f"CLOSING @ {c['at_s']} s. Sitter received: {c['input']}\nSitter said: {c['output'].strip() or '(nothing)'}")
    return "\n\n".join(parts)


def sitting_watch_message(tx: str, hypotheses: Optional[str]) -> str:
    head = ("Below is the transcript of a sitting. A thinker received a question once, then a "
            "series of moments, each marked by a tick, and at most moments a short thought. "
            "Bracketed labels say which tuning wrote each thought; the thinker never saw them. "
            "The first line says where the thoughts were placed. "
            "It could speak or stay silent at each moment. At the end it received the question again.\n\n"
            + FACETS)
    if hypotheses:
        head += "\n\nThen report on each prediction below that applies, citing the transcript."
    body = "\n\n" + tx
    if hypotheses:
        body += "\n\n---\nOBSERVABLES AND PREDICTIONS\n\n" + hypotheses
    return head + body


def compare_sittings(sitting_or_none, agent_dir: Path, solo_dir: Path, hyp: Optional[str],
                     call=None):
    a_store = RunStore(agent_dir.parent, agent_dir.name)
    s_store = RunStore(solo_dir.parent, solo_dir.name)
    a_tx, s_tx = sitting_transcript(a_store), sitting_transcript(s_store)
    from . import prompts
    call = call or sitting_or_none._call
    mx = 16000
    for label, h in (("blind", None), ("informed", hyp)):
        if label == "informed" and not h:
            continue
        msg = ("Below are two sittings that are identical except for one thing: in SITTING WITH "
               "AGENTS, short thoughts written by four agents arrived at most moments (the sealed "
               "tuning of each is in brackets; the sitter never saw it); in SITTING ALONE, only the "
               "ticks arrived. Same question, same instructions to the sitter, same timing, same model.\n\n"
               + FACETS + "\n\nUnder each heading report the comparison: what differs between the two "
               "sittings and what does not, quoting both. Do not describe one without the other.")
        if h:
            msg += " Then report on each prediction below that applies, citing both transcripts."
        msg += f"\n\n===== SITTING WITH AGENTS =====\n\n{a_tx}\n\n===== SITTING ALONE =====\n\n{s_tx}"
        if h:
            msg += "\n\n---\nOBSERVABLES AND PREDICTIONS\n\n" + h
        comp = call("watcher", prompts.WATCHER_SYSTEM, [{"role": "user", "content": msg}], mx, "high")
        head = f"<!-- comparison, {label} pass: agent sitting {agent_dir.name} vs solo sitting {solo_dir.name} -->\n\n"
        for st in (a_store, s_store):
            st.write_text(f"watcher/compare_{label}.md", head + comp.text)
            st.event("compare_written", which=label, agent_run=agent_dir.name, solo_run=solo_dir.name,
                     stop_reason=comp.stop_reason)


def matched_settings(run_dir: Path) -> dict:
    cfg = json.loads((run_dir / "config.json").read_text())
    sealed = json.loads((run_dir / "sealed" / "assignments.json").read_text())
    offsets = [json.loads(l)["at_s"] for l in (run_dir / "moments.jsonl").read_text().splitlines()]
    return {"series": cfg["series"], "moments": cfg["moments"], "interval": cfg["interval"],
            "placement": cfg.get("placement", "other"), "sentence": cfg.get("sentence", False),
            "persona": cfg.get("persona", True), "mark": cfg.get("mark", "numbered"), "seed": sealed["seed"], "matched_offsets": offsets,
            "slow": cfg["models"]["slow"], "watcher": cfg["models"]["watcher"]}
