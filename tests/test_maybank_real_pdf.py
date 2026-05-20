from pathlib import Path

import pytest

from findamental.cache.store import CacheStore
from findamental.config import settings
from findamental.maybank_cache import ensure_maybank_cache


def test_real_maybank_pdf_caches_all_summary_years() -> None:
    pdf = Path("maybank-ar2025-financial-statements.pdf")
    if not pdf.exists():
        pytest.skip("Real Maybank PDF is not present")

    filing = ensure_maybank_cache(CacheStore(settings.CACHE_DIR))
    assert filing is not None
    periods = {item.period for item in filing.line_items}
    assert {"FY_2021", "FY_2022", "FY_2023", "FY_2024", "FY_2025"}.issubset(periods)

    eps_2021 = next(
        item for item in filing.line_items if item.name == "eps" and item.period == "FY_2021"
    )
    assert eps_2021.value == pytest.approx(69.7)
    assert eps_2021.unit == "sen"
