"""Deliverables Studio — compose Evidence-bound blocks into a client report.

The moat rule (U1) lives in ``validate_blocks``: any block that carries a number, table, chart, or
quote MUST bind an ``evidence_id`` that exists in the project. Hand-typed figures cannot be placed.
``render_html`` produces a branded, provenance-annotated document.
"""

from __future__ import annotations

import html
import logging
from typing import Any

log = logging.getLogger(__name__)

# Blocks that assert a fact from the data — each must bind a real Evidence record.
EVIDENCE_BLOCK_TYPES = frozenset({"stat", "table", "chart", "quote"})
# Free-text / structural blocks — no Evidence required.
FREE_BLOCK_TYPES = frozenset({"heading", "text", "methodology"})
ALL_BLOCK_TYPES = EVIDENCE_BLOCK_TYPES | FREE_BLOCK_TYPES


def validate_blocks(
    blocks: list[dict[str, Any]], valid_evidence_ids: set[str]
) -> list[str]:
    """Return errors; empty means valid. Evidence blocks must reference a known Evidence id."""
    errors: list[str] = []
    for i, block in enumerate(blocks or []):
        if not isinstance(block, dict):
            errors.append(f"block[{i}] is not an object")
            continue
        btype = block.get("type")
        if btype not in ALL_BLOCK_TYPES:
            errors.append(f"block[{i}]: unknown type {btype!r}")
            continue
        if btype in EVIDENCE_BLOCK_TYPES:
            evidence_id = str(block.get("evidence_id", ""))
            if not evidence_id:
                errors.append(f"block[{i}] ({btype}): must bind an evidence_id")
            elif evidence_id not in valid_evidence_ids:
                errors.append(
                    f"block[{i}] ({btype}): evidence {evidence_id} is not in this project — "
                    "a claim can only cite real Evidence"
                )
    return errors


# ----------------------------- render -----------------------------

_CSS = """
body{font-family:Inter,system-ui,sans-serif;color:#1E2A22;max-width:820px;margin:0 auto;padding:32px}
h1{font-family:Georgia,serif;color:#14342A;border-bottom:3px solid #6DB33F;padding-bottom:8px}
h2{font-family:Georgia,serif;color:#14342A;margin-top:28px}
.stat{font-size:2rem;color:#14342A;font-weight:600}
.stat-label{color:#5b6b60;font-size:.9rem}
.prov{font-size:.72rem;color:#8a978d;margin-top:4px}
.prov code{background:#f0f5ee;padding:1px 5px;border-radius:4px}
blockquote{border-left:3px solid #6DB33F;margin:12px 0;padding:6px 16px;background:#f7fbf5;color:#2c4437}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:.85rem}
th,td{border:1px solid #cfe0cc;padding:5px 8px;text-align:left}
th{background:#eef6ea}
.card{border:1px solid #E4EBE1;border-radius:12px;padding:16px;margin:14px 0}
.unbacked{color:#b91c1c;font-style:italic}
.foot{margin-top:40px;color:#8a978d;font-size:.75rem;border-top:1px solid #E4EBE1;padding-top:10px}
"""


def _prov(ev: dict[str, Any]) -> str:
    run = str(ev.get("run_id") or "")[:8]
    return (f'<div class="prov">Evidence <code>{html.escape(str(ev.get("label","")))}</code>'
            f' · run <code>{html.escape(run)}</code></div>')


def _render_value(value: Any) -> str:
    if isinstance(value, dict):
        # a table-ish evidence value: {columns/rows} or arbitrary dict
        if "rows" in value and "columns" in value:
            head = "".join(f"<th>{html.escape(str(c))}</th>" for c in value["columns"])
            body = "".join(
                "<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>"
                for row in value["rows"]
            )
            return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        return "<pre>" + html.escape(str(value)) + "</pre>"
    return html.escape(str(value))


def render_html(
    title: str,
    blocks: list[dict[str, Any]],
    evidence_map: dict[str, dict[str, Any]],
    *,
    logo_svg: str = "",
) -> str:
    """Render the report to branded HTML with provenance footnotes under each Evidence block."""
    parts: list[str] = []
    for block in blocks or []:
        btype = block.get("type")
        if btype == "heading":
            parts.append(f"<h2>{html.escape(str(block.get('text', '')))}</h2>")
        elif btype in ("text", "methodology"):
            label = "Methodology" if btype == "methodology" else ""
            body = html.escape(str(block.get("text", ""))).replace("\n", "<br>")
            head = f"<h2>{label}</h2>" if label else ""
            parts.append(f'<div class="card">{head}{body}</div>')
        elif btype in EVIDENCE_BLOCK_TYPES:
            ev = evidence_map.get(str(block.get("evidence_id", "")))
            if ev is None:
                parts.append('<div class="card unbacked">⚠ unbacked claim — evidence missing</div>')
                continue
            value = ev.get("value")
            caption = html.escape(str(block.get("caption", "") or block.get("label", "")))
            if btype == "stat":
                lbl = caption or html.escape(str(ev.get("label", "")))
                parts.append(
                    f'<div class="card"><div class="stat">{_render_value(value)}</div>'
                    f'<div class="stat-label">{lbl}</div>{_prov(ev)}</div>'
                )
            elif btype == "quote":
                text = value.get("text") if isinstance(value, dict) else value
                parts.append(
                    f'<div class="card"><blockquote>“{html.escape(str(text))}”</blockquote>'
                    f'{f"<div class=stat-label>{caption}</div>" if caption else ""}{_prov(ev)}</div>'
                )
            else:  # table / chart
                cap = f"<div class='stat-label'>{caption}</div>" if caption else ""
                parts.append(f'<div class="card">{_render_value(value)}{cap}{_prov(ev)}</div>')

    logo = logo_svg or ""
    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_CSS}</style><title>{html.escape(title)}</title></head><body>"
        f"{logo}<h1>{html.escape(title)}</h1>{''.join(parts)}"
        f"<div class='foot'>Laboratree · Grow · Innovate · Impact — every figure above is bound "
        f"to a re-runnable Evidence record.</div></body></html>"
    )


__all__ = ["EVIDENCE_BLOCK_TYPES", "FREE_BLOCK_TYPES", "ALL_BLOCK_TYPES",
           "validate_blocks", "render_html"]
