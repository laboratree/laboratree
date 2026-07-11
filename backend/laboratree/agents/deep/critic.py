"""Critic — findings survive only when the recorded observations support them."""

from __future__ import annotations

import logging
from typing import Any

from ...core.jsonparse import loads_lenient
from ...labs.agentic import llm as agentic_llm
from . import prompts

log = logging.getLogger(__name__)

MAX_AUDIT_OBS_CHARS = 6000


def audit_findings(
    findings: list[dict[str, Any]], scratchpad: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """One batched audit pass. Returns (surviving findings, drop notes).

    Keyless or on any failure: everything survives (the citation-gate tests still apply) —
    the critic only ever REMOVES unsupported claims, it never invents.
    """
    if not findings or not agentic_llm.is_configured():
        return findings, []
    observations = "\n".join(
        f'<observation id={s["step"]}>{s.get("observation", "")}</observation>'
        for s in scratchpad if s.get("kind", "tool") == "tool"
    )[:MAX_AUDIT_OBS_CHARS]
    listing = "\n".join(f'{i}: {f.get("claim", "")}' for i, f in enumerate(findings))
    try:
        raw = agentic_llm.default_complete(
            prompts.critic_system(),
            f"OBSERVATIONS:\n{observations}\n\nFINDINGS:\n{listing}", role="reasoning")
    except agentic_llm.LLMNotConfigured:
        return findings, []
    verdicts = (loads_lenient(raw) or {}).get("verdicts") or []
    unsupported = {int(v["index"]) for v in verdicts
                   if isinstance(v, dict) and v.get("supported") is False
                   and str(v.get("index", "")).lstrip("-").isdigit()}
    if not unsupported:
        return findings, []
    survivors = [f for i, f in enumerate(findings) if i not in unsupported]
    notes = [f"critic dropped unsupported finding: {findings[i].get('claim', '')[:120]}"
             for i in sorted(unsupported) if i < len(findings)]
    log.info("critic dropped %d/%d findings", len(notes), len(findings))
    return survivors, notes


__all__ = ["audit_findings"]
