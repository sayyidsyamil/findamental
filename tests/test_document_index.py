from pathlib import Path

import pytest

from findamental.config import settings
from findamental.cv.line_item_matcher import LineItemMatcher
from findamental.index.resolver import DocumentResolver
from findamental.index.store import DocumentIndexStore
from findamental.maybank_cache import maybank_pdf_path


def test_document_index_resolves_arbitrary_maybank_rows() -> None:
    if not Path("maybank-ar2025-financial-statements.pdf").exists():
        pytest.skip("Real Maybank PDF is not present")

    document = DocumentIndexStore().ensure_pdf_index(
        maybank_pdf_path(),
        "1155",
        "Malayan Banking Berhad",
        "1155_FY_2025_FINANCIAL_STATEMENTS",
    )
    resolver = DocumentResolver(LineItemMatcher(settings.DATA_DIR / "line_items_dict.json"))

    cases = [
        ("Maybank FY 2021 diluted earning", "FY_2021", "Diluted earnings", 69.7, "Group"),
        ("Maybank 2022 deposits from customers", "FY_2022", "Deposits from customers", 614895, "Group"),
        ("Maybank 2023 total liabilities", "FY_2023", "Total liabilities", 930026, "Group"),
        ("Maybank 2025 ROE", "FY_2025", "Return on equity", 11.7, "Group"),
        ("Maybank 2024 cost to income ratio", "FY_2024", "Cost to income", 48.9, "Group"),
    ]
    for query, period, label, value, scope in cases:
        resolved = resolver.resolve(document, query, None, period)
        assert resolved is not None
        assert resolved.row.label == label
        assert resolved.cell.column == period
        assert resolved.cell.scope == scope
        assert resolved.cell.value == pytest.approx(value)
