"""Prompts for the DeepAgent ReAct loop — versioned in code so runs are reproducible."""

from __future__ import annotations

from typing import Any


def react_system(tool_catalog: str) -> str:
    return (
        "You are a rigorous research agent inside a provenance-locked research platform. "
        "You fulfil ONE research phase using the tools below, one tool call per turn.\n\n"
        f"TOOLS:\n{tool_catalog}\n\n"
        "Respond with EXACTLY one JSON object per turn, either:\n"
        '  {"thought": "<why>", "tool": "<name>", "args": {...}}\n'
        "or, when you have enough to conclude:\n"
        '  {"finish": "<2-3 sentence conclusion>", '
        '"findings": [{"claim": "<verifiable statement>", "basis": "<which observation supports it>"}]}\n\n'
        "Rules: never invent facts, figures, or sources — every claim must trace to an "
        "observation; prefer scholarly sources; if the tools cannot answer, finish honestly "
        "saying what is missing."
    )


def react_turn(objective: str, scratchpad: list[dict[str, Any]]) -> str:
    history = "\n".join(
        f"STEP {s['step']}: thought={s['thought']} tool={s['tool']}({s['args']}) "
        f"-> {s['observation']}"
        for s in scratchpad
    ) or "(no steps yet)"
    return f"OBJECTIVE:\n{objective}\n\nSCRATCHPAD:\n{history}\n\nNext JSON:"
