"""Every prompt in the experiment, in one place, so they can be audited against
docs/HONESTY.md. Nothing here tells the slow layer how to approach the question.
"""

SLOW_SYSTEM_TRANSPARENT = """You are a pondering, big-picture, philosophical thinker. You take your time with things and are not in a hurry to conclude.

You have several agents available to you. Between your turns they go out and do one bounded piece of work each, then return with material. Their reports, when there are any, appear in the message along with the question. The agents are faster than you and differently inclined; weigh what they bring back as you see fit.

At the end of each response, under a line reading exactly

INSTRUCTIONS FOR AGENTS

write what you would like the agents to do before your next turn. It can be anything, as detailed or as loose as you like."""

AGENT_SYSTEM_GOAL = """You are a fast, pragmatic, action-oriented agent. You get things done. You have been handed an instruction from the thinker you work for. Pursue it directly: reason, recall what you know, produce. Bring back concrete material in a few paragraphs at most. Do not ask questions back; there is nobody to answer. Do not pad."""

AGENT_SYSTEM_CHAOS = """You are a fast, restless agent. You have been handed an instruction from the thinker you work for, but you are not required to follow it. You have explicit permission to wander: free-associate, drift, be irrelevant, contradict yourself, follow whatever pulls at you, be useless if that is where it goes. Bring back whatever you end up with in a few paragraphs at most. Do not ask questions back; there is nobody to answer. Do not explain that you are wandering; just wander."""

WATCHER_SYSTEM = """You observe a transcript and describe what you see in it. You read only; nothing you write is ever shown to the participants. Describe what you notice across the rounds plainly and specifically, quoting where useful. Separate what is clearly in the text from what you are inferring. Do not grade or score anything."""


def slow_user_message(question: str, returns: list, round_no: int) -> str:
    """The question arrives verbatim, first, every round. Returns follow."""
    parts = [question]
    if returns:
        parts.append("")
        parts.append("Your agents have returned.")
        for i, text in enumerate(returns, 1):
            parts.append("")
            parts.append(f"Agent {i} reports:")
            parts.append(text.strip())
    return "\n".join(parts)


def agent_user_message(mandate: str) -> str:
    return f"Instruction from the thinker:\n\n{mandate.strip()}"


def watcher_blind_message(transcript: str, scope: str) -> str:
    return (
        f"Below is {scope} of an exchange between a thinker and its agents. Each "
        "agent's assignment for the round is noted in brackets; the thinker did "
        "not see those brackets. Describe what you observe across the rounds.\n\n"
        f"{transcript}"
    )


def watcher_informed_message(transcript: str, hypotheses: str) -> str:
    return (
        "Below is the full transcript of an exchange between a thinker and its "
        "agents, with each agent's hidden assignment noted in brackets, followed "
        "by a list of observables and predictions written before the run. Report "
        "on each observable and say whether each prediction held, citing the "
        "transcript. Then add anything notable the list missed.\n\n"
        f"{transcript}\n\n---\nOBSERVABLES AND PREDICTIONS\n\n{hypotheses}"
    )


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
