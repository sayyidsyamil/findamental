from datetime import UTC, datetime
import json
from pathlib import Path

from findamental.index.models import IndexedDocument, IndexedRow


class DocumentPackBuilder:
    def __init__(self, pack_root: Path):
        self.pack_root = pack_root

    def build(self, document: IndexedDocument) -> Path:
        pack_dir = self.pack_root / document.document_id
        pack_dir.mkdir(parents=True, exist_ok=True)
        (pack_dir / "manifest.json").write_text(
            json.dumps(_manifest(document), indent=2),
            encoding="utf-8",
        )
        (pack_dir / "report.txt").write_text(_report_text(document), encoding="utf-8")
        (pack_dir / "report.md").write_text(_report_markdown(document), encoding="utf-8")
        (pack_dir / "tables.json").write_text(
            json.dumps(_tables(document), indent=2),
            encoding="utf-8",
        )
        (pack_dir / "layout.json").write_text(
            json.dumps(_layout(document), indent=2),
            encoding="utf-8",
        )
        return pack_dir


def _manifest(document: IndexedDocument) -> dict:
    return {
        "document_id": document.document_id,
        "ticker": document.ticker,
        "company_name": document.company_name,
        "source_pdf_path": document.source_pdf_path,
        "parser": document.parser,
        "indexed_at": document.indexed_at.isoformat(),
        "packed_at": datetime.now(UTC).isoformat(),
        "pages": len(document.pages),
        "rows": sum(len(page.rows) for page in document.pages),
    }


def _report_text(document: IndexedDocument) -> str:
    chunks = []
    for page in document.pages:
        chunks.append(f"\n\n=== PAGE {page.page_number} ===\n\n")
        chunks.append(page.text.strip())
        if page.rows:
            chunks.append("\n\n--- Indexed numeric rows ---\n")
            for row in page.rows:
                values = " | ".join(
                    f"{_cell_label(cell.column, cell.scope)}={cell.text}"
                    for cell in row.cells
                    if cell.value is not None
                )
                chunks.append(f"{row.label}: {values}")
    return "\n".join(chunks).strip() + "\n"


def _report_markdown(document: IndexedDocument) -> str:
    chunks = [f"# {document.company_name} ({document.ticker})\n"]
    for page in document.pages:
        chunks.append(f"\n## Page {page.page_number}\n")
        text = page.text.strip()
        if text:
            chunks.append("```text\n" + text + "\n```\n")
        if page.rows:
            chunks.append("### Indexed Numeric Rows\n")
            chunks.append("| Label | Values |")
            chunks.append("|---|---|")
            for row in page.rows:
                values = "<br>".join(
                    f"{_cell_label(cell.column, cell.scope)}: {cell.text}"
                    for cell in row.cells
                    if cell.value is not None
                )
                chunks.append(f"| {_escape_md(row.label)} | {_escape_md(values)} |")
    return "\n".join(chunks) + "\n"


def _tables(document: IndexedDocument) -> dict:
    return {
        "document_id": document.document_id,
        "tables": [
            {
                "page_number": page.page_number,
                "rows": [_row_to_table_json(row) for row in page.rows],
            }
            for page in document.pages
            if page.rows
        ],
    }


def _layout(document: IndexedDocument) -> dict:
    return {
        "document_id": document.document_id,
        "pages": [
            {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "rows": [
                    {
                        "label": row.label,
                        "bbox": row.bbox,
                        "table_bbox": row.table_bbox,
                        "section": row.section,
                        "unit_hint": row.unit_hint,
                        "cells": [
                            {
                                "text": cell.text,
                                "value": cell.value,
                                "column": cell.column,
                                "scope": cell.scope,
                                "bbox": cell.bbox,
                            }
                            for cell in row.cells
                        ],
                    }
                    for row in page.rows
                ],
            }
            for page in document.pages
        ],
    }


def _row_to_table_json(row: IndexedRow) -> dict:
    return {
        "label": row.label,
        "section": row.section,
        "unit_hint": row.unit_hint,
        "bbox": row.bbox,
        "table_bbox": row.table_bbox,
        "cells": [
            {
                "column": cell.column,
                "text": cell.text,
                "value": cell.value,
                "bbox": cell.bbox,
                "scope": cell.scope,
            }
            for cell in row.cells
        ],
    }


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def _cell_label(column: str | None, scope: str | None) -> str:
    if column and scope:
        return f"{scope} {column}"
    return column or scope or "?"
