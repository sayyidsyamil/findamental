from pathlib import Path

import pytest

from findamental.config import settings
from findamental.cv.line_item_matcher import LineItemMatcher
from findamental.index.models import IndexedCell
from findamental.index.pymupdf_indexer import _unit_hint_from_text
from findamental.index.resolver import DocumentResolver
from findamental.index.store import DocumentIndexStore
from findamental.maybank_cache import maybank_pdf_path
from findamental.service import _format_cell_value


def test_unit_hint_ignores_substring_ratio_inside_words() -> None:
    assert _unit_hint_from_text("Income from operations") is None
    assert _unit_hint_from_text("registration of preparation narration") is None
    assert _unit_hint_from_text("Dividend Payout Ratio") == "%"
    assert _unit_hint_from_text("Capital adequacy (%)") == "%"


def test_unit_hint_ignores_substring_sen_inside_words() -> None:
    assert _unit_hint_from_text("consensus expenses") is None
    assert _unit_hint_from_text("Basic (sen)") == "sen"


def test_unit_hint_detects_rm_thousand_and_million() -> None:
    assert _unit_hint_from_text("RM'000 RM'000") == "MYR thousand"
    assert _unit_hint_from_text("RM’000") == "MYR thousand"
    assert _unit_hint_from_text("(RM' million)") == "MYR million"


def test_format_cell_value_demotes_implausible_million() -> None:
    cell = IndexedCell(text="10,831,348", value=10_831_348.0, column="FY_2025", bbox=(0, 0, 0, 0))
    assert _format_cell_value(cell, "MYR million") == "RM 10,831,348 thousand"


def test_format_cell_value_keeps_million_for_summary_scale() -> None:
    cell = IndexedCell(text="66,369", value=66_369.0, column="FY_2025", bbox=(0, 0, 0, 0))
    assert _format_cell_value(cell, "MYR million") == "RM 66,369 million"


def test_net_profit_query_does_not_match_disposal_gain() -> None:
    if not Path("maybank-ar2025-financial-statements.pdf").exists():
        pytest.skip("Real Maybank PDF is not present")

    document = DocumentIndexStore().ensure_pdf_index(
        maybank_pdf_path(),
        "1155",
        "Malayan Banking Berhad",
        "1155_FY_2025_FINANCIAL_STATEMENTS",
    )
    resolver = DocumentResolver(LineItemMatcher(settings.DATA_DIR / "line_items_dict.json"))
    resolved = resolver.resolve(document, "Maybank net profit 2024", "net_income", "FY_2024")
    assert resolved is not None
    label = resolved.row.label.lower()
    assert "disposal" not in label
    assert "gain on" not in label
    assert "profit" in label


def test_profit_for_the_year_uses_correct_unit() -> None:
    if not Path("maybank-ar2025-financial-statements.pdf").exists():
        pytest.skip("Real Maybank PDF is not present")

    document = DocumentIndexStore().ensure_pdf_index(
        maybank_pdf_path(),
        "1155",
        "Malayan Banking Berhad",
        "1155_FY_2025_FINANCIAL_STATEMENTS",
    )
    profit_rows = [
        row
        for page in document.pages
        for row in page.rows
        if row.label.lower().startswith("profit for the financial year")
    ]
    assert profit_rows, "Expected at least one 'Profit for the financial year' row"
    for row in profit_rows:
        for cell in row.cells:
            if cell.value is not None and abs(cell.value) > 1_000_000:
                assert row.unit_hint != "%", (
                    f"Page {row.page_number} row {row.label!r} has unit_hint='%' "
                    f"but value {cell.value} indicates RM thousand or larger"
                )
