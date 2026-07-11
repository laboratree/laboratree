"""Working memory (per run) + the Experience database (long-term strategy memory).

WorkingMemory is the ONLY thing sub-agents share: task summaries and key facts, digested to a
hard character cap and injected into every sub-agent turn — raw scratchpads never cross agent
boundaries (token law). The Experience DB records how each goal went (plan, outcome, lessons)
so `recall_experiences` lets the meta-planner start from what worked last time: top successes
plus at most one failure lesson (labeled "avoid:"), never unfiltered history.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import OrderedDict
from typing import Any

from sqlalchemy import Text, cast, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...projects.models import AgentExperience, ExperienceOutcome
from .goal import Goal

log = logging.getLogger(__name__)

MAX_MEMORY_KEYS = 20
MAX_DIGEST_CHARS = 800
MAX_RECALL = 3
MAX_RECALL_DIGEST_CHARS = 500
MAX_LESSONS = 3


class WorkingMemory:
    """Bounded per-run shared memory (LRU, ≤20 keys); digest ≤800 chars for prompt injection."""

    def __init__(self) -> None:
        self._notes: OrderedDict[str, dict[str, str]] = OrderedDict()

    def note(self, key: str, value: str, *, source: str = "") -> None:
        self._notes.pop(key, None)
        self._notes[key] = {"value": str(value)[:400], "source": source[:80]}
        while len(self._notes) > MAX_MEMORY_KEYS:
            self._notes.popitem(last=False)

    def recall(self, key: str) -> str | None:
        entry = self._notes.get(key)
        return entry["value"] if entry else None

    def digest(self) -> str:
        if not self._notes:
            return ""
        lines = [f"{k}: {v['value']}" for k, v in self._notes.items()]
        out = "WORKING MEMORY (shared notes from earlier tasks):\n" + "\n".join(lines)
        return out[:MAX_DIGEST_CHARS]

    def snapshot(self) -> dict[str, dict[str, str]]:
        return dict(self._notes)


async def record_experience(
    session: AsyncSession, *, org_id: uuid.UUID, project_id: uuid.UUID, goal: Goal,
    plan: list[dict[str, Any]], outcome: ExperienceOutcome, score: float,
    lessons: list[str], refined: bool = False,
) -> AgentExperience:
    experience = AgentExperience(
        org_id=org_id, project_id=project_id, goal_kind=goal.kind,
        goal_text=goal.text[:2000], plan=plan[:10], outcome=outcome,
        score=round(max(0.0, min(1.0, score)), 3),
        lessons=[str(le)[:300] for le in lessons][:MAX_LESSONS], refined=refined,
    )
    session.add(experience)
    await session.flush()
    return experience


async def recall_experiences(
    session: AsyncSession, *, org_id: uuid.UUID, goal: Goal, k: int = MAX_RECALL,
) -> list[AgentExperience]:
    """Lexical FTS over goal_text+lessons, org-scoped; goal_kind match as fallback."""
    hits: list[AgentExperience] = []
    # expression mirrors the migration's GIN index: to_tsvector('english', goal_text||' '||lessons::text)
    document = func.to_tsvector(
        text("'english'"),
        AgentExperience.goal_text + literal(" ") + cast(AgentExperience.lessons, Text))
    # recall wants overlap, not exact asks — OR the goal's terms (websearch default is AND)
    terms = " OR ".join(t for t in re.findall(r"[a-zA-Z0-9]+", goal.text)[:12])
    query_ts = func.websearch_to_tsquery(text("'english'"), terms or goal.text[:100])
    try:
        rows = await session.execute(
            select(AgentExperience)
            .where(AgentExperience.org_id == org_id, document.op("@@")(query_ts))
            .order_by(func.ts_rank_cd(document, query_ts).desc())
            .limit(k * 2)
        )
        hits = list(rows.scalars().all())
    except Exception as exc:
        log.info("experience FTS recall failed (%s); goal_kind fallback", exc)
        await session.rollback()
    if not hits and goal.kind != "general":
        rows = await session.execute(
            select(AgentExperience)
            .where(AgentExperience.org_id == org_id, AgentExperience.goal_kind == goal.kind)
            .order_by(AgentExperience.created_at.desc()).limit(k * 2)
        )
        hits = list(rows.scalars().all())
    # hygiene law: top successes first, at most ONE failure lesson
    successes = [e for e in hits if e.outcome != ExperienceOutcome.FAILED][: k - 1 or 1]
    failures = [e for e in hits if e.outcome == ExperienceOutcome.FAILED][:1]
    return (successes + failures)[:k]


def digest_experiences(experiences: list[AgentExperience]) -> str:
    """≤500-char digest for the meta-planner prompt; failures labeled 'avoid:'."""
    if not experiences:
        return ""
    lines = []
    for e in experiences:
        lesson = "; ".join(str(le) for le in (e.lessons or [])[:2]) or e.goal_text[:80]
        prefix = "avoid:" if e.outcome == ExperienceOutcome.FAILED else "worked:"
        lines.append(f"- {prefix} [{e.goal_kind}] {lesson}")
    return ("PAST EXPERIENCE (from earlier runs):\n" + "\n".join(lines))[:MAX_RECALL_DIGEST_CHARS]


__all__ = ["WorkingMemory", "record_experience", "recall_experiences", "digest_experiences",
           "MAX_MEMORY_KEYS", "MAX_RECALL"]
