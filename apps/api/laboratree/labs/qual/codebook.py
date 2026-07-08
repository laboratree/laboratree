"""Codebook proposal — LLM drafts themes from transcripts; a human approves before use."""

from __future__ import annotations

import logging
from collections.abc import Callable

from ...core.jsonparse import loads_lenient

log = logging.getLogger(__name__)

CompleteFn = Callable[[str, str], str]

MAX_CODES = 14
MAX_CHARS_PER_TRANSCRIPT = 6000

_SYSTEM = (
    "You are a qualitative researcher building a thematic codebook from interview transcripts. "
    "Identify the distinct, recurring themes. Return ONLY a JSON array of at most "
    f"{MAX_CODES} objects: {{\"name\": \"<short-kebab-or-title>\", \"definition\": \"<one clear "
    "sentence: when to apply this code>\"}}. No overlapping or catch-all codes."
)


def propose_codebook(transcript_texts: list[str], complete_fn: CompleteFn) -> list[dict[str, str]]:
    """Draft a codebook from transcripts. Output is validated/deduped; empty list on parse failure."""
    corpus = "\n\n---\n\n".join(t[:MAX_CHARS_PER_TRANSCRIPT] for t in transcript_texts if t)
    raw = complete_fn(_SYSTEM, f"Transcripts:\n\n{corpus}\n\nPropose the codebook now.")
    parsed = loads_lenient(raw)
    codes: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        definition = str(item.get("definition", "")).strip()
        key = name.lower()
        if name and definition and key not in seen:
            seen.add(key)
            codes.append({"name": name, "definition": definition})
        if len(codes) >= MAX_CODES:
            break
    log.info("codebook proposal: %d codes from %d transcripts", len(codes), len(transcript_texts))
    return codes


__all__ = ["CompleteFn", "MAX_CODES", "propose_codebook"]
