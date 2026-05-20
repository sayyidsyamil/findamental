from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class ExtractedLineItem(BaseModel):
    name: str
    raw_label: str
    value: float
    unit: str = "MYR"
    period: str
    source_page: int
    source_bbox: tuple[float, float, float, float]
    row_bbox: tuple[float, float, float, float] | None = None
    annotated_image_path: str
    confidence: float


class ExtractedFiling(BaseModel):
    ticker: str
    company_name: str
    filing_type: str
    source_pdf_path: str
    extracted_at: datetime
    extraction_model: str = "granite-docling-258M-mlx"
    line_items: list[ExtractedLineItem]


class CacheStore:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, filing: ExtractedFiling) -> Path:
        path = self.cache_dir / f"{filing.ticker}_{filing.filing_type}.json"
        path.write_text(filing.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, ticker: str, filing_type: str) -> ExtractedFiling | None:
        path = self.cache_dir / f"{ticker}_{filing_type}.json"
        if not path.exists():
            return None
        return ExtractedFiling.model_validate_json(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[ExtractedFiling]:
        filings = []
        for path in sorted(self.cache_dir.glob("*.json")):
            try:
                filings.append(ExtractedFiling.model_validate_json(path.read_text(encoding="utf-8")))
            except ValueError:
                continue
        return filings

    def find_line_item(
        self,
        ticker: str,
        canonical_name: str,
        period: str | None = None,
    ) -> ExtractedLineItem | None:
        candidates: list[ExtractedLineItem] = []
        for filing in self.list_all():
            if filing.ticker != ticker:
                continue
            candidates.extend(item for item in filing.line_items if item.name == canonical_name)

        if period:
            exact = [item for item in candidates if item.period.lower() == period.lower()]
            if exact:
                return exact[0]
        return candidates[0] if candidates else None

    def filing_for_item(self, ticker: str, item: ExtractedLineItem) -> ExtractedFiling | None:
        for filing in self.list_all():
            if filing.ticker != ticker:
                continue
            if any(candidate == item for candidate in filing.line_items):
                return filing
        return None
