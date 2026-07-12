"""The shared ReAct core — one loop, every agent (DeepAgent tasks, Lab agents, specialists).

Laws baked in (they are not optional per caller):
- one tool call per turn, JSON-decided, leniently parsed;
- per-tool timeout (a hung fetch cannot stall a run);
- session rollback after a failing tool (a dirty session must never poison later steps);
- observations are FENCED as data (`<observation id=n>`) — fetched content can never become
  instructions (prompt-injection law);
- per-run tool memo — the same tool+args within a run returns the cached observation
  (token law: never pay twice);
- oversized observations are summarized once (cheap model) with the full payload archived,
  the scratchpad carries the summary;
- every scratchpad entry streams to ``on_step`` so callers persist progress live.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ...core.jsonparse import loads_lenient
from ...labs.agentic import llm as agentic_llm
from ..flow import FlowContext
from ..tools import AgentTool
from . import prompts

log = logging.getLogger(__name__)

MAX_STEPS = 8
TOOL_TIMEOUT_S = 60.0
MAX_OBSERVATION_CHARS = 1500

OnStep = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class ReactResult:
    summary: str
    findings: list[dict[str, Any]]
    scratchpad: list[dict[str, Any]]
    llm_calls: int = 0
    hit_budget: bool = False


@dataclass
class ToolRunner:
    """Executes one tool with the laws applied; extended by callers (e.g. run_component binding)."""

    ctx: FlowContext
    tools: dict[str, AgentTool]
    memo: dict[str, Any] = field(default_factory=dict)

    async def call(self, name: str, args: dict[str, Any]) -> Any:
        memo_key = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
        if memo_key in self.memo:
            return self.memo[memo_key]
        tool = self.tools.get(name)
        if tool is None:
            return {"error": f"unknown or unavailable tool: {name}"}
        try:
            result = await asyncio.wait_for(self._invoke(tool, args), timeout=TOOL_TIMEOUT_S)
        except TimeoutError:
            return {"error": f"tool {name} timed out after {TOOL_TIMEOUT_S:.0f}s"}
        except Exception as exc:
            # a failing tool is an observation, not a crash — but never leave the session dirty
            log.warning("tool %s failed: %s", name, exc)
            try:
                await self.ctx.session.rollback()
            except Exception:  # rollback is best-effort on a torn session
                log.debug("session rollback after tool failure also failed")
            return {"error": str(exc)[:300]}
        self.memo[memo_key] = result
        return result

    async def _invoke(self, tool: AgentTool, args: dict[str, Any]) -> Any:
        if asyncio.iscoroutinefunction(tool.fn):
            return await tool.fn(**args)
        return await asyncio.to_thread(tool.fn, **args)


def _observation_text(value: Any) -> str:
    try:
        text = json.dumps(value, default=str)
    except Exception:
        text = str(value)
    return text


_URL_IN_TEXT = re.compile(r"https?://[^\s)\"'>]+")
MAX_SEEN_URLS = 200


def _stash_urls(ctx: FlowContext, text: str) -> None:
    """Accumulate raw source URLs from a tool observation into run state, before compaction
    can summarize them away — deterministic post-steps (e.g. PDF archiving) act on these."""
    seen: list[str] = ctx.state.setdefault("seen_urls", [])
    for raw in _URL_IN_TEXT.findall(text):
        if len(seen) >= MAX_SEEN_URLS:
            break
        url = raw.rstrip(".,;)")
        if url not in seen:
            seen.append(url)


def _compact(ctx: FlowContext, text: str) -> str:
    """Summarize an oversized observation once (cheap model); archive stays with the caller."""
    if len(text) <= MAX_OBSERVATION_CHARS:
        return text
    try:
        summary = agentic_llm.default_complete(
            "Summarize this tool output in <=10 dense lines preserving every number, name and "
            "URL a researcher would need. Output only the summary.",
            text[:8000], role="generation")
        return f"(summarized from {len(text)} chars) {summary}"[:MAX_OBSERVATION_CHARS]
    except Exception:
        return text[:MAX_OBSERVATION_CHARS]


async def react_loop(
    ctx: FlowContext,
    *,
    objective: str,
    tools: dict[str, AgentTool],
    system: str,
    max_steps: int = MAX_STEPS,
    runner: ToolRunner | None = None,
    on_step: OnStep | None = None,
    context_note: str = "",
) -> ReactResult:
    runner = runner or ToolRunner(ctx=ctx, tools=tools)
    scratchpad: list[dict[str, Any]] = []
    summary, findings, llm_calls, hit_budget = "", [], 0, False

    async def _emit(step: dict[str, Any]) -> None:
        scratchpad.append(step)
        if on_step is not None:
            try:
                await on_step(step)
            except Exception:  # progress streaming must never break the run
                log.debug("on_step callback failed (non-fatal)")

    for step_no in range(1, max_steps + 1):
        turn = prompts.react_turn(objective, scratchpad, context_note=context_note)
        raw = agentic_llm.default_complete(system, turn, role="reasoning")
        llm_calls += 1
        decision = loads_lenient(raw) or {}

        if "finish" in decision:
            summary = str(decision.get("finish", ""))[:1000]
            findings = [f for f in (decision.get("findings") or []) if isinstance(f, dict)]
            break

        tool_name = str(decision.get("tool", ""))
        args = dict(decision.get("args") or {})
        observation = await runner.call(tool_name, args)
        obs_text = _observation_text(observation)
        _stash_urls(ctx, obs_text)   # capture raw source URLs BEFORE compaction (post-steps use them)
        await _emit({
            "kind": "tool", "step": step_no,
            "thought": str(decision.get("thought", ""))[:400],
            "tool": tool_name, "args": _observation_text(args)[:400],
            "observation": _compact(ctx, obs_text),
        })
    else:
        summary = f"stopped at the {max_steps}-step budget without finishing"
        hit_budget = True

    return ReactResult(summary=summary, findings=findings, scratchpad=scratchpad,
                       llm_calls=llm_calls, hit_budget=hit_budget)


__all__ = ["react_loop", "ReactResult", "ToolRunner", "MAX_STEPS", "TOOL_TIMEOUT_S",
           "MAX_OBSERVATION_CHARS"]
