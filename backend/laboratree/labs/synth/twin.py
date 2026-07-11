"""Twin simulation (LLM, injectable) + dry-run aggregation (pure).

A twin takes the instrument once and returns its answers plus any confusion / drop-off. The
aggregation turns N twin runs into a design report: predicted completion, per-question drop-off,
confusing items, and expected answer distributions.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from ...core.jsonparse import loads_lenient
from .personas import describe

log = logging.getLogger(__name__)

CompleteFn = Callable[[str, str], str]

_SYSTEM = (
    "You role-play a single survey respondent with the given profile. Take the survey honestly and "
    "in character. If a question is confusing, leading, or something you'd refuse, note it. If at "
    "some point you would abandon the survey, report where. Return ONLY JSON of the form "
    '{"answers": {"<qid>": <value>}, "confusions": [{"qid": "<qid>", "note": "<why>"}], '
    '"dropped_at": "<qid or null>"}. For single-choice use one option string; for multi use a list; '
    "for scale/number use a number; for text use a short string."
)


def _questions_block(structure: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in structure.get("sections", []) or []:
        for q in section.get("questions", []) or []:
            desc = f"- {q.get('id')} ({q.get('type')}): {q.get('text')}"
            if q.get("options"):
                desc += f" [options: {', '.join(map(str, q['options']))}]"
            if q.get("scale"):
                desc += f" [scale {q['scale'].get('min')}–{q['scale'].get('max')}]"
            lines.append(desc)
    return "\n".join(lines)


def simulate_persona(
    structure: dict[str, Any], persona: dict[str, Any], complete_fn: CompleteFn
) -> dict[str, Any]:
    """Simulate one persona taking the survey. Returns {answers, confusions, dropped_at}."""
    prompt = (
        f"Respondent profile: {describe(persona)}.\n\n"
        f"Survey questions:\n{_questions_block(structure)}\n\n"
        "Take the survey now."
    )
    try:
        raw = complete_fn(_SYSTEM, prompt)
        parsed = loads_lenient(raw)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        log.warning("twin simulation parse failed for %s: %s", persona.get("id"), exc)
        parsed = None
    if not isinstance(parsed, dict):
        return {"answers": {}, "confusions": [], "dropped_at": None, "persona_id": persona.get("id")}
    return {
        "answers": parsed.get("answers") if isinstance(parsed.get("answers"), dict) else {},
        "confusions": parsed.get("confusions") if isinstance(parsed.get("confusions"), list) else [],
        "dropped_at": parsed.get("dropped_at") or None,
        "persona_id": persona.get("id"),
    }


def _memory_block(persona: dict[str, Any]) -> str:
    """Summarise a persona's prior survey waves so its new answers stay consistent."""
    memory = persona.get("memory") or []
    if not memory:
        return ""
    lines = []
    for episode in memory[-3:]:  # last few waves are enough context
        answers = episode.get("answers") or {}
        summary = ", ".join(f"{k}={v}" for k, v in list(answers.items())[:8])
        lines.append(f"- wave {episode.get('wave', '?')}: {summary}")
    return "Your past answers (stay consistent with these):\n" + "\n".join(lines) + "\n\n"


def simulate_persona_wave(
    structure: dict[str, Any], persona: dict[str, Any], complete_fn: CompleteFn,
    *, social_context: str = "",
) -> dict[str, Any]:
    """Simulate a persisted persona, conditioned on its bio, prior waves, and social circle."""
    bio = persona.get("bio") or describe(persona)
    prompt = (
        f"You are this respondent: {bio}\n\n"
        f"{_memory_block(persona)}"
        f"{social_context}"
        f"Survey questions:\n{_questions_block(structure)}\n\n"
        "Take the survey now, in character and consistent with your past answers."
    )
    try:
        parsed = loads_lenient(complete_fn(_SYSTEM, prompt))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        log.warning("persona wave parse failed for %s: %s", persona.get("handle"), exc)
        parsed = None
    if not isinstance(parsed, dict):
        return {"answers": {}, "confusions": [], "dropped_at": None}
    return {
        "answers": parsed.get("answers") if isinstance(parsed.get("answers"), dict) else {},
        "confusions": parsed.get("confusions") if isinstance(parsed.get("confusions"), list) else [],
        "dropped_at": parsed.get("dropped_at") or None,
    }


def aggregate_dry_run(
    structure: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Aggregate twin runs into a design report (pure)."""
    n = len(results)
    completed = sum(1 for r in results if not r.get("dropped_at"))

    dropoff: Counter[str] = Counter()
    confusion_counts: Counter[str] = Counter()
    confusion_notes: dict[str, list[str]] = defaultdict(list)
    distributions: dict[str, Counter[Any]] = defaultdict(Counter)

    for r in results:
        if r.get("dropped_at"):
            dropoff[str(r["dropped_at"])] += 1
        for c in r.get("confusions") or []:
            if isinstance(c, dict) and c.get("qid"):
                qid = str(c["qid"])
                confusion_counts[qid] += 1
                if c.get("note") and len(confusion_notes[qid]) < 3:
                    confusion_notes[qid].append(str(c["note"]))
        for qid, value in (r.get("answers") or {}).items():
            if value in (None, "", []):
                continue
            key = tuple(value) if isinstance(value, list) else value
            distributions[str(qid)][key] += 1

    return {
        "n": n,
        "completed": completed,
        "completion_rate": round(completed / n, 3) if n else 0.0,
        "predicted_dropoff": [
            {"qid": qid, "dropped": count}
            for qid, count in sorted(dropoff.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "confusing_items": [
            {"qid": qid, "count": count, "notes": confusion_notes.get(qid, [])}
            for qid, count in sorted(confusion_counts.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "distributions": {
            qid: [{"value": list(v) if isinstance(v, tuple) else v, "count": c}
                  for v, c in counts.most_common()]
            for qid, counts in distributions.items()
        },
        "caveat": "Synthetic dry-run — approximates real respondents; use for instrument design, "
                  "not as evidence of real-world results.",
    }


__all__ = ["CompleteFn", "simulate_persona", "simulate_persona_wave", "aggregate_dry_run"]
