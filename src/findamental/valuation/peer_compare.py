from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class PeerComparisonResult:
    sector: str
    sector_median: float
    delta_pct: float
    interpretation: str


class PeerComparator:
    def __init__(self, sector_medians_path: Path, company_index_path: Path | None = None):
        self.sector_medians = json.loads(sector_medians_path.read_text(encoding="utf-8"))
        if company_index_path is None:
            company_index_path = sector_medians_path.with_name("company_index.json")
        self.company_index = json.loads(company_index_path.read_text(encoding="utf-8"))

    def compare(self, ticker: str, metric: str, value: float) -> PeerComparisonResult:
        company = self.company_index.get(ticker)
        if company is None:
            raise KeyError(f"Unknown ticker: {ticker}")
        sector = company["sector"]
        medians = self.sector_medians.get(sector, {})
        if metric not in medians:
            raise KeyError(f"No sector median for {metric} in {sector}")
        median = float(medians[metric])
        if median == 0:
            raise ValueError(f"Sector median for {metric} in {sector} is zero")
        delta = (value - median) / abs(median)
        direction = "above" if delta >= 0 else "below"
        interpretation = f"{direction} sector median by {abs(delta) * 100:.1f}%"
        return PeerComparisonResult(sector, median, delta, interpretation)
