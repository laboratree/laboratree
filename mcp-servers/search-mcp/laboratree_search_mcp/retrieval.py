"""DB-free hybrid retrieval — BM25 lexical + optional dense embeddings, fused with RRF.

Portable on purpose: the caller hands in the documents (from search, files, anywhere) and gets
back a ranked, deduplicated set of the most relevant passages. No datastore required, so this
MCP runs anywhere; when an embedding backend is configured it adds a dense leg, otherwise the
lexical leg alone still ranks well.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

RRF_K = 60
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass
class Ranked:
    ordinal: int
    text: str
    score: float
    lexical_rank: int | None
    dense_rank: int | None


def _bm25_scores(query: str, docs: list[list[str]], *, k1: float = 1.5,
                 b: float = 0.75) -> list[float]:
    n = len(docs)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in docs) / n or 1.0
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    q_terms = [t for t in set(_tokenize(query)) if df.get(t)]
    scores = [0.0] * n
    for i, doc in enumerate(docs):
        tf = Counter(doc)
        dl = len(doc) or 1
        for term in q_terms:
            f = tf.get(term, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            scores[i] += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
    return scores


def _rank_order(scores: list[float]) -> dict[int, int]:
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return {idx: rank for rank, idx in enumerate(order) if scores[idx] > 0}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def hybrid_retrieve(query: str, documents: list[str], *, k: int = 6,
                    embed_fn=None) -> list[Ranked]:
    """Rank ``documents`` against ``query`` with BM25 (+ optional dense) fused by RRF."""
    docs = [d for d in documents if d and d.strip()]
    if not docs:
        return []
    tokenized = [_tokenize(d) for d in docs]
    lexical = _rank_order(_bm25_scores(query, tokenized))

    dense: dict[int, int] = {}
    if embed_fn is not None:
        try:
            vectors = embed_fn([query, *docs])
            qv, dvs = vectors[0], vectors[1:]
            sims = [_cosine(qv, dv) for dv in dvs]
            dense = {idx: rank for rank, idx in enumerate(
                sorted(range(len(sims)), key=lambda i: sims[i], reverse=True))}
        except Exception:
            dense = {}   # dense leg is best-effort; lexical still ranks

    fused: dict[int, float] = {}
    for idx in set(lexical) | set(dense):
        score = 0.0
        if idx in lexical:
            score += 1.0 / (RRF_K + lexical[idx])
        if idx in dense:
            score += 1.0 / (RRF_K + dense[idx])
        fused[idx] = score

    ordered = sorted(fused, key=lambda i: fused[i], reverse=True)[:k]
    return [Ranked(ordinal=idx, text=docs[idx], score=round(fused[idx], 6),
                   lexical_rank=lexical.get(idx), dense_rank=dense.get(idx))
            for idx in ordered]


__all__ = ["hybrid_retrieve", "Ranked", "RRF_K"]
