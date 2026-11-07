"""USD per million tokens, for the spend cap. Cached from the claude-api
reference on 2026-11-07; update when prices change. Unknown models cost 0 but
the run logs a warning so the cap is known to be blind for them."""

PRICES = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.00, 5.00),
    "stub": (0.0, 0.0),
}


# Cache reads: 0.05x input on Opus 5.5, 0.025x on Fable 5.1, 0.1x elsewhere.
# Cache writes (5-minute TTL): 1.25x input.
CACHE_READ_FACTOR = {"claude-opus-5-5": 0.05, "claude-fable-5-1": 0.025}


def cost_usd(model: str, input_tokens: int, output_tokens: int,
             cache_write_tokens: int = 0, cache_read_tokens: int = 0) -> float:
    inp, out = PRICES.get(model, (0.0, 0.0))
    read = CACHE_READ_FACTOR.get(model, 0.1)
    return (input_tokens * inp + output_tokens * out
            + cache_write_tokens * inp * 1.25 + cache_read_tokens * inp * read) / 1e6
