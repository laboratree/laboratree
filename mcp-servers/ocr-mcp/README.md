# Laboratree — OCR + Document Intelligence MCP

A standalone **MCP server** that turns *any* document into clean text, structured tables and
Markdown. OCR is one stage, not the whole product: PDFs with a text layer are read directly,
scanned PDFs and images fall back to OCR, tables come out structured, and unknown types degrade
gracefully to decoded text. Any MCP client can plug it in.

## Tools

| Tool | What it does |
|------|--------------|
| `extract_document` | Any document → text + structured tables. Auto-routes by type; OCR fallback for scans/images. Reports whether OCR was used. |
| `extract_tables` | Just the structured tables (PDF/DOCX/Excel/CSV) as rows + columns. |
| `to_markdown` | Extract and render as clean Markdown (text + tables). |
| `ocr_image` | OCR a single image (PNG/JPG/TIFF) → text. |
| `quality_report` | Yield report: chars, tables, OCR-used, confidence, verdict — so an agent can judge trust. |
| `capabilities` | Supported file types + whether OCR (tesseract) is available. |

Documents are passed as **base64** (portable over MCP's JSON transport). Every response is
version-stamped with `_meta` and reports its provenance — the **Capability Contract**.

## Run it

```bash
uv run laboratree-ocr-mcp          # stdio transport
```

## Connect it (any MCP client)

```jsonc
{
  "mcpServers": {
    "laboratree-ocr": {
      "command": "uv",
      "args": ["run", "laboratree-ocr-mcp"]
    }
  }
}
```

## Configuration

- **Native PDF text, tables, DOCX, Excel, CSV, HTML, plain text** work out of the box.
- **Scanned PDFs and images** need the **tesseract** binary installed (`capabilities` reports
  availability honestly; without it, image OCR returns a clear error instead of guessing).
