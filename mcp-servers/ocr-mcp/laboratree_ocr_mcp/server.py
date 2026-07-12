"""OCR + Document Intelligence — an MCP server.

Turn ANY document — native or scanned PDF, image, Office file, HTML, plain text — into clean
text, structured tables and markdown. OCR is one stage, not the whole story: PDFs with a text
layer are read directly, scanned PDFs and images fall back to OCR, tables are pulled out
structured, and everything else degrades gracefully to decoded text. Any MCP client can plug it
in; the caller passes bytes (base64) + a filename and gets a stable, provenance-stamped result.

Capability Contract: stable typed results · per-document provenance · honest capability
reporting (OCR availability) · version-stamped responses. Transport: stdio.
"""

from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

SERVER_VERSION = "0.1.0"
MAX_TABLE_ROWS = 200
MAX_TEXT_CHARS = 200_000
_TEXTLIKE = {".txt", ".md", ".markdown", ".json", ".csv", ".tsv", ".log", ".rst", ".xml"}
_HTMLLIKE = {".html", ".htm"}

mcp = FastMCP("laboratree-ocr")


# ----------------------------- helpers -----------------------------

def _decode(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"content_base64 is not valid base64: {exc}") from exc


def _meta(filename: str, **extra: Any) -> dict[str, Any]:
    return {"server": "laboratree-ocr", "version": SERVER_VERSION, "filename": filename, **extra}


def _table_to_dict(table: Any) -> dict[str, Any]:
    df = table.df
    return {"name": table.name, "kind": table.kind,
            "columns": [str(c) for c in df.columns],
            "rows": df.head(MAX_TABLE_ROWS).astype(str).values.tolist(),
            "n_rows": int(len(df)), "truncated": len(df) > MAX_TABLE_ROWS}


def _extract_any(filename: str, data: bytes) -> dict[str, Any]:
    """Route to the strongest extractor for the type; degrade gracefully to decoded text."""
    from laboratree.labs.signal.extract import extract_file

    suffix = Path(filename).suffix.lower()
    ocr_used = False
    try:
        result = extract_file(filename, data)
        texts, tables = list(result.texts), [_table_to_dict(t) for t in result.tables]
        # a PDF that yielded no text-layer text but produced text = OCR fallback fired
        if suffix == ".pdf" and texts and not any(t["rows"] for t in tables):
            from laboratree.core.net import pdf_to_text

            ocr_used = not pdf_to_text(data).strip()
    except ValueError:
        # unsupported by the multi-format extractors — try text/HTML/PDF-bytes fallbacks
        texts, tables = _fallback_text(filename, data, suffix), []
    text = "\n\n".join(texts)[:MAX_TEXT_CHARS]
    return {"text": text, "text_blocks": texts, "tables": tables,
            "chars": len(text), "n_tables": len(tables), "ocr_used": ocr_used}


def _fallback_text(filename: str, data: bytes, suffix: str) -> list[str]:
    if data.lstrip()[:5].startswith(b"%PDF"):
        from laboratree.core.net import pdf_to_text

        txt = pdf_to_text(data)
        return [txt] if txt.strip() else []
    if suffix in _HTMLLIKE:
        from laboratree.core.net import html_to_text

        txt = html_to_text(data)
        return [txt] if txt.strip() else []
    if suffix in _TEXTLIKE or not suffix:
        for enc in ("utf-8", "latin-1"):
            try:
                return [data.decode(enc)]
            except UnicodeDecodeError:
                continue
    raise ValueError(f"unsupported document type: {suffix or filename!r}")


def _markdown(doc: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in doc["text_blocks"]:
        parts.append(block.strip())
    for table in doc["tables"]:
        cols = table["columns"] or [f"col{i}" for i in range(len(table["rows"][0]))] \
            if table["rows"] else table["columns"]
        if not cols:
            continue
        parts.append("| " + " | ".join(cols) + " |")
        parts.append("| " + " | ".join("---" for _ in cols) + " |")
        for row in table["rows"][:50]:
            parts.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
    return "\n\n".join(p for p in parts if p)


# ----------------------------- tools -----------------------------

@mcp.tool()
async def extract_document(
    filename: Annotated[str, Field(description="Original filename incl. extension (routes the "
                                              "extractor), e.g. 'paper.pdf', 'scan.png'")],
    content_base64: Annotated[str, Field(description="The document bytes, base64-encoded")],
) -> dict[str, Any]:
    """Extract clean text + structured tables from ANY document — native or scanned PDF, image,
    DOCX, spreadsheet, HTML or plain text. Scanned PDFs and images fall back to OCR
    automatically; the result reports whether OCR was used."""
    data = _decode(content_base64)
    doc = _extract_any(filename, data)
    return {**doc, "_meta": _meta(filename, bytes=len(data))}


@mcp.tool()
async def extract_tables(
    filename: Annotated[str, Field(description="Filename incl. extension")],
    content_base64: Annotated[str, Field(description="Document bytes, base64-encoded")],
) -> dict[str, Any]:
    """Pull only the structured tables out of a document (PDF/DOCX/Excel/CSV) as rows + columns."""
    data = _decode(content_base64)
    doc = _extract_any(filename, data)
    return {"tables": doc["tables"], "n_tables": doc["n_tables"], "_meta": _meta(filename)}


@mcp.tool()
async def to_markdown(
    filename: Annotated[str, Field(description="Filename incl. extension")],
    content_base64: Annotated[str, Field(description="Document bytes, base64-encoded")],
) -> dict[str, Any]:
    """Extract a document and render it as clean Markdown (text blocks + tables)."""
    data = _decode(content_base64)
    doc = _extract_any(filename, data)
    return {"markdown": _markdown(doc), "_meta": _meta(filename)}


@mcp.tool()
async def ocr_image(
    content_base64: Annotated[str, Field(description="Image bytes (PNG/JPG/TIFF), base64-encoded")],
) -> dict[str, Any]:
    """OCR a single image into text (requires the tesseract binary)."""
    from laboratree.ocr import ocr_available, ocr_image_bytes

    if not ocr_available():
        return {"error": "OCR requires the tesseract binary (not installed)", "text": "",
                "_meta": _meta("image", ocr_available=False)}
    text = ocr_image_bytes(_decode(content_base64))
    return {"text": text, "chars": len(text), "_meta": _meta("image", ocr_available=True)}


@mcp.tool()
async def quality_report(
    filename: Annotated[str, Field(description="Filename incl. extension")],
    content_base64: Annotated[str, Field(description="Document bytes, base64-encoded")],
) -> dict[str, Any]:
    """Extract a document and report on the yield — characters, tables, whether OCR was used, and
    a confidence heuristic — so an agent can decide whether the extraction is trustworthy."""
    data = _decode(content_base64)
    doc = _extract_any(filename, data)
    chars = doc["chars"]
    confidence = round(min(1.0, chars / 500) * (0.7 if doc["ocr_used"] else 1.0), 3)
    return {"chars": chars, "n_text_blocks": len(doc["text_blocks"]),
            "n_tables": doc["n_tables"], "ocr_used": doc["ocr_used"],
            "confidence": confidence,
            "verdict": "good" if confidence >= 0.6 else "thin" if chars else "empty",
            "_meta": _meta(filename, bytes=len(data))}


@mcp.tool()
async def capabilities() -> dict[str, Any]:
    """Report what this server can handle — supported file types and whether OCR is available."""
    from laboratree.labs.signal.extract import supported_suffixes
    from laboratree.ocr import ocr_available

    return {"supported_suffixes": sorted(set(supported_suffixes())
                                         | _TEXTLIKE | _HTMLLIKE | {".pdf"}),
            "ocr_available": ocr_available(),
            "note": "PDFs with a text layer are read directly; scanned PDFs and images use OCR "
                    "when tesseract is installed.",
            "_meta": {"server": "laboratree-ocr", "version": SERVER_VERSION}}


def main() -> None:
    """Entrypoint — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
