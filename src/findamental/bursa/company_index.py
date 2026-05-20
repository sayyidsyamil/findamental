import json
from pathlib import Path

from rapidfuzz import fuzz, process


class CompanyIndex:
    def __init__(self, path: Path):
        self.path = path
        self.companies: dict[str, dict] = json.loads(path.read_text(encoding="utf-8"))

    def resolve(self, text: str) -> str | None:
        normalized = text.strip().lower()
        if normalized in self.companies:
            return normalized

        candidates: dict[str, str] = {}
        for ticker, info in self.companies.items():
            candidates[ticker] = ticker
            candidates[info["name"].lower()] = ticker
            for short_name in info.get("short_names", []):
                candidates[short_name.lower()] = ticker

        match = process.extractOne(
            normalized,
            candidates.keys(),
            scorer=fuzz.token_set_ratio,
            score_cutoff=70,
        )
        if match is None:
            return None
        return candidates[match[0]]

    def name_for(self, ticker: str) -> str:
        return self.companies.get(ticker, {}).get("name", ticker)
