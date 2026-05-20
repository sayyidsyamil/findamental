from datetime import UTC, datetime
from pathlib import Path

from findamental.cache.store import CacheStore, ExtractedFiling, ExtractedLineItem
from findamental.config import settings
from findamental.cv.annotator import PageAnnotator
from findamental.cv.line_item_matcher import LineItemMatcher
from findamental.cv.pymupdf_summary import PyMuPDFSummaryExtractor


FILING_TYPE = "FY_2025_FINANCIAL_STATEMENTS"


def maybank_pdf_path() -> Path:
    return settings.DATA_DIR.parent / "maybank-ar2025-financial-statements.pdf"


def ensure_maybank_cache(store: CacheStore | None = None) -> ExtractedFiling | None:
    pdf = maybank_pdf_path()
    if not pdf.exists():
        return None

    store = store or CacheStore(settings.CACHE_DIR)
    cache_path = settings.CACHE_DIR / f"1155_{FILING_TYPE}.json"
    existing = store.load("1155", FILING_TYPE)
    if existing and cache_path.stat().st_mtime >= pdf.stat().st_mtime and _has_multi_year_cache(existing):
        return existing

    matcher = LineItemMatcher(settings.DATA_DIR / "line_items_dict.json")
    filing = build_maybank_cache(pdf, matcher)
    store.save(filing)
    return filing


def build_maybank_cache(pdf: Path, matcher: LineItemMatcher) -> ExtractedFiling:
    extractor = PyMuPDFSummaryExtractor(matcher)
    annotator = PageAnnotator()
    rows = extractor.extract_group_summary(pdf)
    line_items = []
    image_by_metric: dict[str, str] = {}

    for row in rows:
        image_name = image_by_metric.setdefault(
            row.canonical_name,
            f"1155_summary_{row.canonical_name}.png",
        )
        image_path = settings.CACHE_DIR / image_name
        if not image_path.exists():
            annotator.crop_and_annotate(
                pdf_path=pdf,
                page_number=row.page_number,
                bbox=row.table_bbox,
                row_bbox=row.row_bbox,
                output_path=image_path,
            )
        line_items.append(
            ExtractedLineItem(
                name=row.canonical_name,
                raw_label=row.label,
                value=row.value,
                unit="sen" if row.canonical_name == "eps" else "MYR million",
                period=row.period,
                source_page=row.page_number,
                source_bbox=row.table_bbox,
                row_bbox=row.row_bbox,
                annotated_image_path=image_name,
                confidence=row.confidence,
            )
        )

    return ExtractedFiling(
        ticker="1155",
        company_name="Malayan Banking Berhad",
        filing_type=FILING_TYPE,
        source_pdf_path=str(pdf),
        extracted_at=datetime.now(UTC),
        extraction_model="granite-docling-258M-mlx+pymupdf-summary-fallback",
        line_items=line_items,
    )


def _has_multi_year_cache(filing: ExtractedFiling) -> bool:
    periods = {item.period for item in filing.line_items}
    return {"FY_2021", "FY_2022", "FY_2023", "FY_2024", "FY_2025"}.issubset(periods)
