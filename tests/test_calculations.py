from pathlib import Path

import pytest

from findamental.calculations import FinancialCalculator
from findamental.index.store import DocumentIndexStore
from findamental.maybank_cache import maybank_pdf_path


def test_calculates_maybank_valuation_metrics() -> None:
    if not Path("maybank-ar2025-financial-statements.pdf").exists():
        pytest.skip("Real Maybank PDF is not present")

    document = DocumentIndexStore().ensure_pdf_index(
        maybank_pdf_path(),
        "1155",
        "Malayan Banking Berhad",
        "1155_FY_2025_FINANCIAL_STATEMENTS",
    )
    calculator = FinancialCalculator()

    pe = calculator.calculate(document, "Maybank 2025 PE ratio", "FY_2025")
    assert pe is not None
    assert pe.metric == "Price to earnings"
    assert pe.value == pytest.approx(12.032, rel=1e-3)

    pb = calculator.calculate(document, "Maybank 2025 price to book", "FY_2025")
    assert pb is not None
    assert pb.metric == "Price to book"
    assert pb.value == pytest.approx(1.355, rel=1e-3)


def test_calculates_maybank_growth_and_margin() -> None:
    if not Path("maybank-ar2025-financial-statements.pdf").exists():
        pytest.skip("Real Maybank PDF is not present")

    document = DocumentIndexStore().ensure_pdf_index(
        maybank_pdf_path(),
        "1155",
        "Malayan Banking Berhad",
        "1155_FY_2025_FINANCIAL_STATEMENTS",
    )
    calculator = FinancialCalculator()

    revenue_growth = calculator.calculate(document, "calculate Maybank revenue growth 2025", "FY_2025")
    assert revenue_growth is not None
    assert revenue_growth.metric == "Revenue growth"
    assert revenue_growth.value == pytest.approx(-3.733, rel=1e-3)

    margin = calculator.calculate(document, "calculate Maybank net profit margin 2025", "FY_2025")
    assert margin is not None
    assert margin.metric == "Net profit margin"
    assert margin.value == pytest.approx(15.842, rel=1e-3)
