"""Default LLM callables for the Paper Lab (wrap the app LLMClient).

Kept as module-level functions so services take them as injectable defaults and tests can
monkeypatch them without a live model.
"""

from __future__ import annotations


def default_complete(system: str, prompt: str, *, role: str = "reasoning") -> str:
    from openai import BadRequestError

    from ...core.llm import get_llm

    # Card/walkthrough JSON can be very large (dozens of variables, per-model math) — without an
    # explicit output budget some deployments truncate mid-JSON and the whole card parses empty.
    try:
        return get_llm().complete(prompt, system=system, role=role, max_completion_tokens=16000)
    except BadRequestError:  # older deployments only accept the legacy parameter name
        try:
            return get_llm().complete(prompt, system=system, role=role, max_tokens=8000)
        except BadRequestError:
            return get_llm().complete(prompt, system=system, role=role)


def default_embed(texts: list[str]) -> list[list[float]]:
    from ...core.llm import get_llm

    return get_llm().embed(texts)
