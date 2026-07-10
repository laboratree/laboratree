"""Agentic reasoning components — LLM findings as Evidence-locked runs.

``agent.reason`` is the generic reasoning tool the flow orchestrator (and any Lab) can dispatch:
give it an objective and real project context, it returns structured findings — every finding an
Evidence record naming the model that produced it, so agent output inherits provenance like any
other run. No key configured → typed ``LLMNotConfigured`` (callers keep deterministic fallbacks);
it never fabricates.

Model choice is pure config (open-weight first): point ``openai_base_url``/``openai_model`` at
any OpenAI-compatible host — e.g. Nous **Hermes** (agentic-tuned open weights) via OpenRouter
(``openai_model=nousresearch/hermes-4-405b``), DeepSeek, or a self-hosted vLLM.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...core.config import settings
from ...core.jsonparse import loads_lenient
from . import llm as agentic_llm

MAX_FINDINGS = 10

_SYSTEM = (
    "You are a rigorous research analyst agent. Reason ONLY over the provided context — never "
    "invent facts, figures, or sources. Answer as JSON: "
    '{"findings": [{"claim": str, "basis": str}], "summary": str}. '
    f"At most {MAX_FINDINGS} findings; every claim must cite its basis in the context."
)


@register
class AgentReason(Component):
    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="agent.reason",
        name="Agent reasoning",
        summary="An LLM agent reasons over supplied project context toward an objective; "
        "each finding is Evidence-locked with the model named. Requires a configured LLM.",
        params_schema={
            "type": "object",
            "required": ["objective", "context"],
            "properties": {
                "objective": {"type": "string", "title": "What to figure out"},
                "context": {"type": "string", "title": "The real material to reason over"},
            },
        },
        inputs=[],
        outputs=[Port(name="findings", dtype="metrics")],
        tags=["agent", "reasoning"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        objective = str(ctx.params["objective"])
        context = str(ctx.params["context"])[:12000]
        raw = agentic_llm.default_complete(
            _SYSTEM, f"OBJECTIVE:\n{objective}\n\nCONTEXT:\n{context}", role="reasoning")
        parsed = loads_lenient(raw) or {}
        findings = [f for f in (parsed.get("findings") or []) if isinstance(f, dict)][:MAX_FINDINGS]
        model = settings.reasoning_model or settings.openai_model or settings.azure_openai_deployment_name
        for i, finding in enumerate(findings, start=1):
            ctx.emit(f"agent_finding_{i}", str(finding.get("claim", ""))[:500],
                     kind="claim", component=self.spec.id, model=model,
                     basis=str(finding.get("basis", ""))[:500])
        return {"findings": findings, "summary": str(parsed.get("summary", ""))[:1000],
                "model": model, "n_findings": len(findings)}
