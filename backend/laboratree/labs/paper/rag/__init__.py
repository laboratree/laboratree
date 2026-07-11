"""Chat-with-paper — retrieval (vector or keyword) + grounded answering with citations."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

CompleteFn = Callable[[str, str], str]
EmbedFn = Callable[[list[str]], list[list[float]]]

_SYSTEM = (
    "You answer questions about a research paper using ONLY the provided context passages. "
    "Cite the passages you use as [ordinal]. If the answer is not in the context, say you cannot "
    "find it in the paper. Be concise and faithful."
)


async def retrieve(
    session: AsyncSession,
    *,
    paper_id: uuid.UUID,
    org_id: uuid.UUID,
    query: str,
    embed_fn: EmbedFn | None = None,
    k: int = 4,
) -> list[dict]:
    """Single-paper retrieval — delegates to the shared hybrid engine (dense + FTS + RRF)."""
    from ....core.retrieval import hybrid_search  # local import avoids a labs<->core cycle

    chunks = await hybrid_search(session, org_id=org_id, paper_id=paper_id,
                                 query=query, k=k, embed_fn=embed_fn)
    return [{"ordinal": c.ordinal, "text": c.text} for c in chunks]


def answer(question: str, passages: list[dict], complete_fn: CompleteFn) -> dict:
    if not passages:
        return {"answer": "No content available for this paper.", "citations": [], "used": []}
    context = "\n\n".join(f"[{p['ordinal']}] {p['text']}" for p in passages)
    prompt = f"=== CONTEXT ===\n{context}\n\n=== QUESTION ===\n{question}"
    text = complete_fn(_SYSTEM, prompt)
    return {
        "answer": text,
        "citations": [p["ordinal"] for p in passages],
        "used": passages,
    }
