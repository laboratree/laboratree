"""Default LLM callable for agentic reasoning (injectable; tests monkeypatch this)."""

from __future__ import annotations

from ...core.config import settings


class LLMNotConfigured(RuntimeError):
    """No provider key — callers fall back deterministically (never on real API errors)."""


def is_configured() -> bool:
    if settings.llm_provider == "azure":
        return bool(settings.azure_openai_api_key)
    return bool(settings.openai_api_key)


def default_complete(system: str, prompt: str, *, role: str = "reasoning") -> str:
    key = settings.azure_openai_api_key if settings.llm_provider == "azure" else settings.openai_api_key
    if not key:
        raise LLMNotConfigured(f"no API key configured for LLM provider {settings.llm_provider!r}")
    from ...core.llm import get_llm

    return get_llm().complete(prompt, system=system, role=role)
