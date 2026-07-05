"""On-demand beginner explainer for an unusual pipeline step.

Some preprocessing / estimation steps are advanced concepts a first-timer won't know — fixed effects,
clustered standard errors, instrumental variables, propensity scores, winsorizing… Rather than curate
them all, the LLM explains the specific step in plain language WITH a tiny worked example table, so
'what exactly is this doing?' is answered concretely for anyone.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....core.jsonparse import loads_lenient

CompleteFn = Callable[..., str]


def explain_step(title: str, detail: str, complete_fn: CompleteFn) -> dict[str, Any]:
    """Return {what_it_is, why, how_it_works[], example{caption,columns,rows}, takeaway} for a step —
    everyday language + a small realistic table. Best-effort; never raises."""
    system = (
        "You explain a data-analysis / econometrics pipeline step to a COMPLETE beginner who has "
        "never heard the terms. Given the step, return ONLY JSON with keys: "
        "what_it_is (1-2 plain sentences, NO jargon — define any technical word inline), "
        "why (why researchers do this, plainly), "
        "how_it_works (array of 2-4 short plain steps), "
        "example (a TINY concrete illustration as {caption, columns:[...], rows:[[...]]} — a small "
        "realistic table that makes it click, e.g. show the before→after, the added indicator columns, "
        "or two groups being compared; keep it 3-4 rows), "
        "takeaway (one sentence: what it changes and what it does NOT change). "
        "Make it so a non-expert immediately understands exactly what the step does."
    )
    prompt = f"Pipeline step: {title}\nDescription from the paper: {detail}"
    try:
        parsed = loads_lenient(complete_fn(system, prompt))
    except Exception:
        parsed = None
    if not isinstance(parsed, dict):
        return {"what_it_is": detail or title, "why": "", "how_it_works": [],
                "example": None, "takeaway": ""}
    ex = parsed.get("example")
    if not (isinstance(ex, dict) and ex.get("columns") and ex.get("rows")):
        parsed["example"] = None
    else:
        parsed["example"] = {
            "caption": str(ex.get("caption", "")),
            "columns": [str(c) for c in ex["columns"]],
            "rows": [[str(c) for c in row] for row in ex["rows"] if isinstance(row, list)],
        }
    parsed.setdefault("what_it_is", detail or title)
    parsed.setdefault("why", "")
    parsed.setdefault("how_it_works", [])
    parsed.setdefault("takeaway", "")
    parsed["how_it_works"] = [str(s) for s in (parsed.get("how_it_works") or [])]
    return parsed
