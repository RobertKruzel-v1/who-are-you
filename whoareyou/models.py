"""Model clients. One real client over the Anthropic SDK, one stub for dry runs.

Both expose `complete(model, system, messages, max_tokens, effort) -> Completion`.
Nothing here adds framing to prompts; prompts live in prompts.py.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Completion:
    text: str
    model: str                 # model id the API reports it served
    input_tokens: int
    output_tokens: int
    stop_reason: str
    elapsed_s: float
    raw_blocks: list = field(default_factory=list)
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


class StubClient:
    """Deterministic text, zero spend. Lets the orchestration be verified."""

    def __init__(self) -> None:
        self.calls = 0

    def resolve_model_ids(self, models: dict) -> dict:
        return {k: f"stub:{v}" for k, v in models.items()}

    def complete(self, model: str, system: str, messages: List[dict],
                 max_tokens: int, effort: str, cache: bool = False) -> Completion:
        self.calls += 1
        last = messages[-1]["content"] if messages else ""
        digest = hashlib.sha1(last.encode()).hexdigest()[:8]
        role = "slow" if "pondering" in system else ("watcher" if "observe" in system else "agent")
        if role == "slow" and last.startswith("tick "):
            text = "" if self.calls % 2 else f"[stub tick reply / {digest}]"
        elif role == "slow" and "INSTRUCTIONS FOR AGENTS" not in system:
            text = f"[stub solo response #{self.calls} / {digest}] Still with the question."
        elif role == "slow":
            text = (f"[stub slow response #{self.calls} / {digest}]\n"
                    "I notice the question again. Here is a stub musing.\n\n"
                    "INSTRUCTIONS FOR AGENTS\n"
                    f"Look into stub thread {digest}.")
        elif role == "watcher":
            text = f"[stub watcher report / {digest}] Nothing observed; this is a dry run."
        else:
            text = f"[stub agent return / {digest}] Material about: {last[:60]!r}"
        return Completion(text=text, model="stub", input_tokens=len(last) // 4,
                          output_tokens=len(text) // 4, stop_reason="end_turn",
                          elapsed_s=0.0)


class AnthropicClient:
    def __init__(self) -> None:
        import anthropic  # imported lazily so dry runs need no key
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(timeout=600.0, max_retries=3)

    def list_models(self) -> List[str]:
        return [m.id for m in self.client.models.list()]

    def resolve_model_ids(self, models: dict) -> dict:
        """Confirm each configured model exists via the Models API and return
        the exact ids the API reports. Fails loudly on an unknown model."""
        out = {}
        for role, mid in models.items():
            info = self.client.models.retrieve(mid)
            out[role] = info.id
        return out

    def complete(self, model: str, system: str, messages: List[dict],
                 max_tokens: int, effort: str, cache: bool = False) -> Completion:
        t0 = time.time()
        kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                      messages=messages, output_config={"effort": effort})
        if cache:
            # Top-level automatic caching: the growing conversation prefix is
            # re-read cheaply on the next call. Changes cost, not behaviour.
            kwargs["cache_control"] = {"type": "ephemeral"}
        with self.client.messages.stream(**kwargs) as stream:
            resp = stream.get_final_message()
        text = "".join(b.text for b in resp.content if b.type == "text")
        return Completion(
            text=text, model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            stop_reason=resp.stop_reason or "unknown",
            elapsed_s=time.time() - t0,
            raw_blocks=[b.model_dump(exclude_none=True) for b in resp.content],
            cache_write_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
        )


def make_client(dry_run: bool):
    return StubClient() if dry_run else AnthropicClient()
