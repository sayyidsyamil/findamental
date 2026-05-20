from pathlib import Path

import pytest

from findamental.valuation.peer_compare import PeerComparator
from findamental.valuation.ratios import pb_ratio, pe_ratio, revenue_growth, roe


def test_ratios() -> None:
    assert pe_ratio(10, 2) == 5
    assert pb_ratio(9, 3) == 3
    assert roe(11, 100) == 0.11
    assert revenue_growth(120, 100) == 0.2


def test_zero_guard() -> None:
    with pytest.raises(ValueError):
        pe_ratio(10, 0)


def test_peer_compare() -> None:
    comparator = PeerComparator(Path("data/sector_medians.json"))
    result = comparator.compare("1155", "pe", 13.64)
    assert result.sector == "Financial Services"
    assert result.delta_pct == pytest.approx(0.1)
