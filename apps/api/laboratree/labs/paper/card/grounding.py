"""Card grounding — link every factual claim in the card back to the paper text that supports it.

Deterministic (zero LLM): numbers are the strong signal. A claim like "scored 99.16% accuracy and
100% precision" is verified when a chunk contains those same numbers; softer claims fall back to
keyword overlap. The result is a {claim-key: [{ordinal, quote}]} map the UI renders as
"✓ verified in paper §N" badges — and, just as important, an honest ABSENCE for anything the
model may have invented.
"""

from __future__ import annotations

import re

_NUM = re.compile(r"\d+(?:\.\d+)?")
_WORD = re.compile(r"[a-zA-Z]{5,}")
_TRIVIAL = {"0", "1", "2", "3", "4", "5", "10", "100"}  # too common to prove anything alone


def _numbers(text: str) -> set[str]:
    return {n for n in _NUM.findall(text or "") if n not in _TRIVIAL}


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")}


def _quote_around(chunk: str, needles: set[str]) -> str:
    """The sentence(s) in the chunk containing the first matched needle — the human-checkable bit."""
    sentences = re.split(r"(?<=[.!?])\s+", chunk)
    for s in sentences:
        if any(n in s for n in needles):
            return s.strip()[:320]
    return chunk.strip()[:320]


def _ground_claim(claim: str, chunks: list[tuple[int, str]]) -> list[dict]:
    nums = _numbers(claim)
    kws = _keywords(claim)
    if not nums and len(kws) < 3:
        return []
    best: tuple[float, int, str, set[str], set[str]] | None = None
    for ordinal, text in chunks:
        hit_nums = nums & _numbers(text)
        hit_kws = (kws & _keywords(text)) if kws else set()
        score = 3.0 * len(hit_nums) + 0.2 * len(hit_kws)
        if best is None or score > best[0]:
            best = (score, ordinal, text, hit_nums, hit_kws)
    if best is None:
        return []
    _score, ordinal, text, hit_nums, hit_kws = best
    # verified only when at least one non-trivial NUMBER matches, or keyword overlap is strong
    num_verified = bool(hit_nums)
    kw_verified = not nums and kws and len(hit_kws) >= max(4, len(kws) // 2)
    if not (num_verified or kw_verified):
        return []
    needles = hit_nums if hit_nums else set(sorted(hit_kws)[:3])
    return [{"ordinal": int(ordinal), "quote": _quote_around(text, needles)}]


def ground_card(card: dict, chunks: list[tuple[int, str]]) -> dict[str, list[dict]]:
    """Ground the card's checkable claims. Keys: model:{i}, variant:{i}, results, best_model,
    data_sample. Only VERIFIED claims appear — a missing key means 'could not verify'."""
    if not isinstance(card, dict) or card.get("paper_type") != "empirical" or not chunks:
        return {}
    out: dict[str, list[dict]] = {}

    def put(key: str, claim: str) -> None:
        if claim and (g := _ground_claim(str(claim), chunks)):
            out[key] = g

    for i, m in enumerate(card.get("models_used") or []):
        if isinstance(m, dict):
            put(f"model:{i}", m.get("result", ""))
    for i, v in enumerate(card.get("variants") or []):
        if isinstance(v, dict):
            put(f"variant:{i}", v.get("description", ""))
    put("results", card.get("results", ""))
    put("best_model", card.get("best_model", ""))
    put("data_sample", card.get("data_sample", ""))
    return out
