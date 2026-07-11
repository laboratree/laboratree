"""Behavioral-economics grounding for synthetic personas (pure, deterministic).

Rather than trusting an LLM to guess choices, these models constrain synthetic responses with
established theory: prospect theory (risk/loss framing), discrete-choice / multinomial logit
(feature & price trade-offs), and Bass diffusion (adoption over time). Each is a registered
component emitting Evidence; they also back the twin engine's answer generation.
"""

from __future__ import annotations

import math
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

# ----------------------------- prospect theory -----------------------------

# Kahneman & Tversky (1992) median estimates.
PT_ALPHA = 0.88   # gain curvature
PT_BETA = 0.88    # loss curvature
PT_LAMBDA = 2.25  # loss aversion


def prospect_value(
    outcome: float, *, reference: float = 0.0,
    alpha: float = PT_ALPHA, beta: float = PT_BETA, lam: float = PT_LAMBDA,
) -> float:
    """Prospect-theory value of an outcome relative to a reference point (loss-averse, S-shaped)."""
    delta = outcome - reference
    if delta >= 0:
        return delta ** alpha
    return -lam * ((-delta) ** beta)


def prospect_choice(
    option_a: float, option_b: float, *, reference: float = 0.0
) -> dict[str, Any]:
    """Which of two outcomes a loss-averse agent prefers (relative to a reference)."""
    va, vb = prospect_value(option_a, reference=reference), prospect_value(option_b, reference=reference)
    return {"value_a": round(va, 4), "value_b": round(vb, 4),
            "prefers": "a" if va >= vb else "b"}


# ----------------------------- discrete choice (MNL) -----------------------------

def logit_shares(utilities: list[float], *, scale: float = 1.0) -> list[float]:
    """Multinomial-logit choice probabilities from deterministic utilities (softmax)."""
    if not utilities:
        return []
    scaled = [scale * u for u in utilities]
    m = max(scaled)
    exps = [math.exp(u - m) for u in scaled]  # subtract max for numerical stability
    total = sum(exps)
    return [round(e / total, 6) for e in exps]


def choice_shares(
    alternatives: list[dict[str, float]],
    weights: dict[str, float],
    *,
    scale: float = 1.0,
) -> list[dict[str, Any]]:
    """Predict market shares for alternatives given attribute values and part-worth weights.

    ``alternatives``: [{attr: value}]; ``weights``: {attr: coefficient} (price coeff usually < 0).
    """
    utilities = [
        sum(weights.get(attr, 0.0) * value for attr, value in alt.items())
        for alt in alternatives
    ]
    shares = logit_shares(utilities, scale=scale)
    return [
        {"index": i, "utility": round(u, 4), "share": s}
        for i, (u, s) in enumerate(zip(utilities, shares, strict=True))
    ]


def price_elasticity(
    alternatives: list[dict[str, float]], weights: dict[str, float],
    target_index: int, price_attr: str = "price", pct: float = 0.01,
) -> float:
    """Own-price elasticity of the target alternative's share via a small price perturbation."""
    base = choice_shares(alternatives, weights)[target_index]["share"]
    bumped = [dict(a) for a in alternatives]
    price0 = bumped[target_index].get(price_attr, 0.0)
    if price0 == 0:
        return 0.0
    bumped[target_index][price_attr] = price0 * (1 + pct)
    new = choice_shares(bumped, weights)[target_index]["share"]
    if base == 0:
        return 0.0
    return round(((new - base) / base) / pct, 4)


# ----------------------------- Bass diffusion -----------------------------

def bass_adoption(
    p: float, q: float, market: float, periods: int
) -> list[dict[str, float]]:
    """Bass (1969) diffusion: new + cumulative adopters per period.

    ``p`` = coefficient of innovation, ``q`` = imitation, ``market`` = ultimate adopters.
    """
    result: list[dict[str, float]] = []
    cumulative = 0.0
    for t in range(1, periods + 1):
        remaining = market - cumulative
        adopters = (p + q * (cumulative / market)) * remaining if market > 0 else 0.0
        adopters = max(0.0, min(adopters, remaining))
        cumulative += adopters
        result.append({"period": t, "new_adopters": round(adopters, 2),
                        "cumulative": round(cumulative, 2),
                        "penetration": round(cumulative / market, 4) if market else 0.0})
    return result


# ----------------------------- components -----------------------------

@register
class DiscreteChoice(Component):
    """Predict choice shares (and optional price elasticity) from a conjoint-style design."""

    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="analyzer.discrete_choice",
        name="Discrete choice (MNL)",
        summary="Multinomial-logit market shares from attribute values and part-worth weights.",
        params_schema={
            "type": "object",
            "properties": {
                "alternatives": {"type": "array", "items": {"type": "object"}},
                "weights": {"type": "object"},
                "scale": {"type": "number", "default": 1.0},
            },
            "required": ["alternatives", "weights"],
        },
        inputs=[],
        outputs=[Port(name="result", dtype="metrics")],
        tags=["synth", "behavioral", "pricing"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        alts = ctx.params.get("alternatives") or []
        weights = ctx.params.get("weights") or {}
        shares = choice_shares(alts, weights, scale=ctx.params.get("scale", 1.0))
        for row in shares:
            ctx.emit(f"share_{row['index']}", row["share"], kind="metric", component=self.spec.id)
        return {"shares": shares}


@register
class BassDiffusion(Component):
    """Forecast new-product adoption over time with the Bass diffusion model."""

    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="analyzer.bass_diffusion",
        name="Bass diffusion forecast",
        summary="Adoption curve (new + cumulative) from innovation/imitation coefficients.",
        params_schema={
            "type": "object",
            "properties": {
                "p": {"type": "number", "default": 0.03},
                "q": {"type": "number", "default": 0.38},
                "market": {"type": "number"},
                "periods": {"type": "integer", "default": 12},
            },
            "required": ["market"],
        },
        inputs=[],
        outputs=[Port(name="result", dtype="metrics")],
        tags=["synth", "behavioral", "forecast"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        curve = bass_adoption(
            ctx.params.get("p", 0.03), ctx.params.get("q", 0.38),
            float(ctx.params["market"]), int(ctx.params.get("periods", 12)),
        )
        ctx.emit("peak_period",
                 max(curve, key=lambda r: r["new_adopters"])["period"] if curve else 0,
                 kind="metric", component=self.spec.id)
        ctx.emit("final_penetration", curve[-1]["penetration"] if curve else 0.0,
                 kind="metric", component=self.spec.id)
        return {"curve": curve}


__all__ = [
    "prospect_value", "prospect_choice",
    "logit_shares", "choice_shares", "price_elasticity",
    "bass_adoption", "DiscreteChoice", "BassDiffusion",
]
