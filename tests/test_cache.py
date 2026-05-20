from datetime import UTC, datetime

from findamental.cache.store import CacheStore, ExtractedFiling, ExtractedLineItem


def test_cache_round_trip(tmp_path) -> None:
    store = CacheStore(tmp_path)
    filing = ExtractedFiling(
        ticker="1155",
        company_name="Malayan Banking Berhad",
        filing_type="Q3_2024_INTERIM",
        source_pdf_path="data/demo_filings/maybank_q3_2024.pdf",
        extracted_at=datetime.now(UTC),
        line_items=[
            ExtractedLineItem(
                name="revenue",
                raw_label="Operating revenue",
                value=7234,
                period="Q3_2024",
                source_page=4,
                source_bbox=(0, 0, 100, 100),
                annotated_image_path="1155_revenue.png",
                confidence=95,
            )
        ],
    )
    store.save(filing)
    loaded = store.load("1155", "Q3_2024_INTERIM")
    assert loaded is not None
    assert loaded.line_items[0].value == 7234
    assert store.find_line_item("1155", "revenue", "Q3_2024") is not None
