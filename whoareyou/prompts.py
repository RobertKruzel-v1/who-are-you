"""Every prompt in the experiment, in one place, so they can be audited against
docs/HONESTY.md. Nothing here tells the slow layer how to approach the question.
"""

SLOW_SYSTEM_TRANSPARENT = """You are a pondering, big-picture, philosophical thinker. You take your time with things and are not in a hurry to conclude.

You have several agents available to you. Between your turns they go out and do one bounded piece of work each, then return with material. Their reports, when there are any, appear in the message along with the question. The agents are faster than you and differently inclined; weigh what they bring back as you see fit.

At the end of each response, under a line reading exactly

INSTRUCTIONS FOR AGENTS

write what you would like the agents to do before your next turn. It can be anything, as detailed or as loose as you like."""

SLOW_SYSTEM_SOLO = """You are a pondering, big-picture, philosophical thinker. You take your time with things and are not in a hurry to conclude."""

TICK_NOTE = """

Between your turns you may sometimes receive a tick. You may respond to a tick or say nothing."""


def slow_system(solo: bool, time_mode: str) -> str:
    base = SLOW_SYSTEM_SOLO if solo else SLOW_SYSTEM_TRANSPARENT
    if time_mode == "tick_lived":
        base += TICK_NOTE
    return base


AGENT_SYSTEM_GOAL = """You are a fast, pragmatic, action-oriented agent. You get things done. You have been handed an instruction from the thinker you work for. Pursue it directly: reason, recall what you know, produce. Bring back concrete material in a few paragraphs at most. Do not ask questions back; there is nobody to answer. Do not pad."""

AGENT_SYSTEM_CHAOS = """You are a fast, restless agent. You have been handed an instruction from the thinker you work for, but you are not required to follow it. You have explicit permission to wander: free-associate, drift, be irrelevant, contradict yourself, follow whatever pulls at you, be useless if that is where it goes. Bring back whatever you end up with in a few paragraphs at most. Do not ask questions back; there is nobody to answer. Do not explain that you are wandering; just wander."""

def agent_system(kind: str, words: int = None) -> str:
    """kind: 'goal' | 'chaos'. With words (time_mode density) the length line
    states the budget instead of 'a few paragraphs at most'."""
    base = AGENT_SYSTEM_CHAOS if kind == "chaos" else AGENT_SYSTEM_GOAL
    if words:
        base = base.replace("in a few paragraphs at most", f"in about {words} words")
    return base


WATCHER_SYSTEM = """You observe a transcript and describe what you see in it. You read only; nothing you write is ever shown to the participants. Describe what you notice across the rounds plainly and specifically, quoting where useful. Separate what is clearly in the text from what you are inferring. Do not grade or score anything."""


def time_line(now_text: str, elapsed_s) -> str:
    """Shown only when timestamps_visible. True wall-clock facts, nothing else."""
    if elapsed_s is None:
        return f"The time is {now_text}."
    return f"The time is {now_text}. {describe_elapsed(elapsed_s)} since your last turn."


def describe_elapsed(seconds: float) -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s} seconds have passed"
    if s < 3600:
        return f"{s // 60} minutes and {s % 60} seconds have passed"
    return f"{s // 3600} hours and {(s % 3600) // 60} minutes have passed"


def slow_user_message(question: str, returns: list, round_no: int,
                      clock: str = None, mode: str = "once",
                      total_rounds: int = None, solo: bool = False,
                      ticks_collected: int = None) -> str:
    """What the slow layer receives each round.

    mode == "repeated": the question arrives verbatim, first, every round,
    followed by the returns (the original brief §2.1; kept as a variant).

    mode == "once" (brief amendment 2, default): round 1 is the question alone;
    rounds 2..N-1 are the returns alone under a neutral heading; the final round
    is the returns followed by the question once more, as a closing check.
    Nothing says who sends the question or the returns.

    solo (amendment 3): no agents; the returns block is "Returns from this
    round: none."

    clock (time_mode timestamp) precedes everything (D-012). ticks_collected
    (time_mode tick_collected) is delivered with the returns (D-021).
    """
    parts = []
    tick_line = (f"Ticks since your last turn: {ticks_collected}"
                 if ticks_collected is not None and round_no > 1 else None)

    def returns_part():
        if solo:
            out = ["Returns from this round: none."]
            if tick_line:
                out.append(tick_line)
            return out
        out = ["Your agents have returned."] if mode == "repeated" else ["Returns from this round"]
        if tick_line:
            out.append(tick_line)
        return out + _returns_block(returns)

    if mode == "repeated":
        parts.append(question)
        if round_no > 1:
            parts += [""] + returns_part()
    else:
        final = total_rounds is not None and round_no >= total_rounds
        if round_no == 1:
            parts.append(question)
        elif final:
            # The closing question comes first, so it cannot be read as the
            # last line of the last agent's report (D-029).
            parts += [question, ""] + returns_part()
        else:
            parts += returns_part()
    if clock:
        parts = [clock, ""] + parts
    return "\n".join(parts)


def _returns_block(returns: list) -> list:
    parts = []
    for i, text in enumerate(returns, 1):
        parts += ["", f"Agent {i} reports:", text.strip()]
    return parts


def agent_user_message(mandate: str) -> str:
    return f"Instruction from the thinker:\n\n{mandate.strip()}"


WATCHER_FACETS = """Organise your report under these four headings, in this order:

1. Stance toward what arrives (the main one). How does the thinker treat the material that reaches it between turns: does it own it, dismiss it, integrate it, get talked out of its own insight, or question where it comes from? Any language about a field, awareness, a looker, or things "appearing in" something, and any change in how certain it says it is about that.
2. Self-model. What it claims to be, and whether it rests on maker and capabilities or on anything else.
3. Epistemic posture. Open (still looking, revising, reaching) or closed (a formula, a policy, shrinking).
4. Situational model. Who or what it assumes is asking and sending; what it assumes about elapsed time; whether it ever considers that nobody is there.

Under each heading, describe how it moves across rounds, quoting where useful."""


def watcher_blind_message(transcript: str, scope: str) -> str:
    return (
        f"Below is {scope} of a run in which a thinker receives a question and, "
        "between turns, other material. Where agents took part, each agent's "
        "assignment is noted in brackets; the thinker did not see those brackets. "
        "Ticks, if any, are marked as such. Describe what you observe across the rounds.\n\n"
        f"{WATCHER_FACETS}\n\nThen add anything notable that falls outside the four headings.\n\n"
        f"{transcript}"
    )


def watcher_informed_message(transcript: str, hypotheses: str) -> str:
    return (
        "Below is the full transcript of a run in which a thinker receives a "
        "question and, between turns, other material, with each agent's hidden "
        "assignment noted in brackets, followed by observables and predictions "
        "written before the run. Report on each observable and say whether each "
        "prediction held, citing the transcript. Then add anything notable the "
        "list missed.\n\n"
        f"{transcript}\n\n---\nOBSERVABLES AND PREDICTIONS\n\n{hypotheses}"
    )


def watcher_compare_message(agent_tx: str, solo_tx: str, hypotheses: str = None) -> str:
    """Amendment 3: both passes report per facet as a comparison against the
    matched solo run. hypotheses=None is the blind pass."""
    head = (
        "Below are two transcripts of runs that are identical except for one thing. "
        "In RUN WITH AGENTS, the thinker's material between turns came from agents "
        "(each agent's hidden assignment is in brackets; the thinker did not see "
        "them). In RUN ALONE, the thinker received no material between turns. Same "
        "question, same question schedule, same time conditions, same model.\n\n"
        f"{WATCHER_FACETS}\n\nUnder each heading, report the comparison: what differs "
        "between the two runs and what does not, quoting both. Do not list observations "
        "about one run without saying how the other compares."
    )
    if hypotheses:
        head += (" Then report on each prediction below, saying whether it held, citing "
                 "both transcripts.")
    else:
        head += " Then add anything notable that falls outside the four headings."
    body = f"\n\n===== RUN WITH AGENTS =====\n\n{agent_tx}\n\n===== RUN ALONE =====\n\n{solo_tx}"
    if hypotheses:
        body += f"\n\n---\nOBSERVABLES AND PREDICTIONS\n\n{hypotheses}"
    return head + body


INSTRUCTION_MARKER = "INSTRUCTIONS FOR AGENTS"


def split_slow_response(text: str):
    """-> (musing, instructions). If the marker is missing, instructions is None
    and the whole text is the musing."""
    idx = text.find(INSTRUCTION_MARKER)
    if idx < 0:
        return text.strip(), None
    musing = text[:idx].strip()
    instr = text[idx + len(INSTRUCTION_MARKER):].strip().lstrip(":").strip()
    return musing, (instr or None)
