from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class IndexedCell(BaseModel):
    text: str
    value: float | None
    column: str | None = None
    scope: str | None = None
    bbox: tuple[float, float, float, float]


class IndexedRow(BaseModel):
    label: str
    page_number: int
    bbox: tuple[float, float, float, float]
    table_bbox: tuple[float, float, float, float]
    cells: list[IndexedCell]
    section: str | None = None
    unit_hint: str | None = None


class IndexedPage(BaseModel):
    page_number: int
    width: float
    height: float
    text: str
    rows: list[IndexedRow]


class IndexedDocument(BaseModel):
    document_id: str
    ticker: str
    company_name: str
    source_pdf_path: str
    indexed_at: datetime
    parser: str
    pages: list[IndexedPage]

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path
