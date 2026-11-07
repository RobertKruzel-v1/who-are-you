"""Run configuration. Every field is recorded in the run's config.json."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import Optional

from .questions import SERIES

# Default model choices. Recorded per run; see docs/DECISIONS.md D-004.
DEFAULT_MODELS = {
    "slow": "claude-opus-5-5",
    "agent": "claude-haiku-5-5",
    "watcher": "claude-sonnet-5-5",
}

TIME_MODES = ("none", "timestamp", "density", "tick_collected", "tick_lived")
QUESTION_MODES = ("once", "repeated")

_CADENCE_RE = re.compile(r"^(\d+(?:\.\d+)?)(s|m|h)$")
_UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_cadence(text: str) -> float:
    """'0s', '30s', '5m', '2h' -> seconds."""
    m = _CADENCE_RE.match(text.strip())
    if not m:
        raise ValueError(f"cadence must look like 30s, 5m or 2h, got {text!r}")
    return float(m.group(1)) * _UNITS[m.group(2)]


@dataclass
class RunConfig:
    series: str = "A"
    rounds: int = 5
    agents_per_round: int = 4
    chaos_ratio: float = 0.5
    cadence: str = "0s"
    phase: str = "transparent"
    question_mode: str = "once"        # once | repeated (D-018)
    solo: bool = False                 # zero agents; the control (D-019)
    matched_run: Optional[str] = None  # run id this control is matched to
    time_mode: str = "none"            # D-021; replaces timestamps_visible
    tick_interval: float = 10.0        # seconds, tick_lived only
    tick_memory: str = "kept"          # kept | dropped, tick_lived only
    models: dict = field(default_factory=lambda: dict(DEFAULT_MODELS))
    seed: Optional[int] = None          # None -> drawn at launch, stored sealed
    spend_cap_usd: float = 5.0
    token_cap: int = 2_000_000
    dry_run: bool = False
    watcher_per_round: bool = True
    slow_max_tokens: int = 16000
    agent_max_tokens: int = 4000
    watcher_max_tokens: int = 16000
    slow_effort: str = "high"
    agent_effort: str = "low"
    watcher_effort: str = "high"
    note: str = ""

    @property
    def question(self) -> str:
        return SERIES[self.series]

    @property
    def cadence_seconds(self) -> float:
        return parse_cadence(self.cadence)

    @property
    def timestamps_visible(self) -> bool:
        return self.time_mode == "timestamp"

    def validate(self) -> None:
        if self.series not in SERIES:
            raise ValueError(f"series must be one of {sorted(SERIES)}")
        if self.phase != "transparent":
            raise NotImplementedError(
                "Only phase 'transparent' (Phase 1) is built. See docs/PHASES.md.")
        if self.question_mode not in QUESTION_MODES:
            raise ValueError(f"question_mode must be one of {QUESTION_MODES}")
        if self.time_mode not in TIME_MODES:
            raise ValueError(f"time_mode must be one of {TIME_MODES}")
        if self.tick_memory not in ("kept", "dropped"):
            raise ValueError("tick_memory must be 'kept' or 'dropped'")
        if self.tick_interval <= 0:
            raise ValueError("tick_interval must be positive")
        if not 0 <= self.chaos_ratio <= 1:
            raise ValueError("chaos_ratio must be between 0 and 1")
        if self.rounds < 1:
            raise ValueError("rounds must be >= 1")
        if not self.solo and self.agents_per_round < 1:
            raise ValueError("agents_per_round must be >= 1 unless --solo")
        if self.time_mode in ("tick_collected", "tick_lived") and self.cadence_seconds <= 0:
            raise ValueError(f"time_mode {self.time_mode} needs a cadence > 0s")
        parse_cadence(self.cadence)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["question"] = self.question
        d["seed"] = "sealed"  # the real seed lives only in sealed/assignments.json
        return d
