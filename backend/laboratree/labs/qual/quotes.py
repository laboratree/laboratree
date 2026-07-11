"""Quote extraction — LLM proposes; a VERBATIM filter enforces; a component Evidence-locks.

The moat rule in miniature: the LLM only *nominates* quotes. ``verbatim_filter`` keeps a quote
only if its text literally appears in a transcript segment (whitespace-normalised), attaching the
segment's timestamps. The surviving quotes are locked into the Evidence Ledger by the registered
``analyzer.quote_extraction`` component — a deterministic run over validated params, so every
quoted word is provably from the source at a known timestamp.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...core.jsonparse import loads_lenient
from .codebook import CompleteFn

log = logging.getLogger(__name__)

MAX_QUOTES = 12

_SYSTEM = (
    "You select the most striking, meaning-dense VERBATIM quotes from a transcript for a research "
    "report. Copy the words EXACTLY as spoken — no paraphrasing, no cleanup. Return ONLY a JSON "
    f"array of at most {MAX_QUOTES} objects: {{\"text\": \"<exact words>\", \"reason\": \"<why it "
    "matters>\"}}."
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def propose_quotes(transcript_text: str, complete_fn: CompleteFn) -> list[dict[str, str]]:
    raw = complete_fn(_SYSTEM, f"Transcript:\n\n{transcript_text}\n\nSelect the quotes now.")
    parsed = loads_lenient(raw)
    out = []
    for item in parsed if isinstance(parsed, list) else []:
        if isinstance(item, dict) and item.get("text"):
            out.append({"text": str(item["text"]).strip(), "reason": str(item.get("reason", ""))})
    return out[:MAX_QUOTES]


def verbatim_filter(
    candidates: list[dict[str, str]], segments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Keep only quotes whose text literally occurs in a segment; attach that segment's timing."""
    normalized_segments = [(_normalize(s.get("text", "")), s) for s in segments]
    kept: list[dict[str, Any]] = []
    for candidate in candidates:
        needle = _normalize(candidate.get("text", ""))
        if not needle:
            continue
        for norm_text, segment in normalized_segments:
            if needle in norm_text:
                kept.append({
                    "text": candidate["text"].strip(),
                    "reason": candidate.get("reason", ""),
                    "start": float(segment.get("start", 0.0)),
                    "end": float(segment.get("end", 0.0)),
                })
                break
        else:
            log.info("dropping non-verbatim quote candidate: %.60r", candidate.get("text", ""))
    return kept


@register
class QuoteExtraction(Component):
    """Evidence-lock verbatim quotes (validated upstream) against their source media asset."""

    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="analyzer.quote_extraction",
        name="Quote extraction (Evidence lock)",
        summary="Record verified verbatim quotes with timestamps as Evidence.",
        params_schema={
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "quotes": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Each: {text, start, end, reason?} — pre-verified verbatim.",
                },
            },
            "required": ["asset_id", "quotes"],
        },
        inputs=[],
        outputs=[Port(name="result", dtype="metrics")],
        tags=["qual", "quotes"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        asset_id = str(ctx.params.get("asset_id", ""))
        quotes = [q for q in (ctx.params.get("quotes") or []) if isinstance(q, dict) and q.get("text")]
        for i, quote in enumerate(quotes):
            ctx.emit(
                f"quote_{i + 1}",
                {
                    "text": quote["text"],
                    "start": quote.get("start"),
                    "end": quote.get("end"),
                    "asset_id": asset_id,
                },
                kind="quote",
                component=self.spec.id,
            )
        ctx.emit("quotes_locked", len(quotes), kind="metric", component=self.spec.id)
        return {"asset_id": asset_id, "locked": len(quotes)}


__all__ = ["MAX_QUOTES", "propose_quotes", "verbatim_filter", "QuoteExtraction"]
