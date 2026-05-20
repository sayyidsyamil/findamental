from dataclasses import dataclass
import json
from pathlib import Path
import re

from rapidfuzz import fuzz


@dataclass(frozen=True)
class MatchResult:
    row_index: int
    canonical_name: str
    raw_label: str
    confidence: float


class LineItemMatcher:
    def __init__(self, synonyms_path: Path):
        self.synonyms_path = synonyms_path
        raw = json.loads(synonyms_path.read_text(encoding="utf-8"))
        self.synonyms: dict[str, list[str]] = {}
        for canonical, groups in raw.items():
            phrases = [canonical.replace("_", " ")]
            for values in groups.values():
                phrases.extend(str(value) for value in values)
            self.synonyms[canonical] = [_normalize(phrase) for phrase in phrases]

    def canonical_for_query(self, query: str) -> tuple[str | None, float]:
        best_name = None
        best_score = 0.0
        normalized = _normalize(query)
        for canonical, phrases in self.synonyms.items():
            for phrase in phrases:
                score = float(fuzz.token_set_ratio(normalized, phrase))
                if score > best_score:
                    best_name = canonical
                    best_score = score
        return best_name, best_score

    def match(self, query: str, table_rows: list[list[str]]) -> MatchResult | None:
        target, query_score = self.canonical_for_query(query)
        if target is None or query_score < 55:
            return None

        best: MatchResult | None = None
        for index, row in enumerate(table_rows):
            if not row:
                continue
            raw_label = str(row[0])
            label = _normalize(raw_label)
            score = max(float(fuzz.token_set_ratio(label, phrase)) for phrase in self.synonyms[target])
            if best is None or score > best.confidence:
                best = MatchResult(index, target, raw_label, score)

        if best is None or best.confidence < 75:
            return None
        return best


def parse_numeric_value(cells: list[str]) -> float | None:
    for cell in cells[1:] or cells:
        text = str(cell).strip()
        if not text or text in {"-", "—"}:
            continue
        negative = "(" in text and ")" in text
        cleaned = re.sub(r"[^0-9.\-]", "", text)
        if cleaned in {"", ".", "-"}:
            continue
        try:
            value = float(cleaned)
        except ValueError:
            continue
        return -value if negative and value > 0 else value
    return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("_", " ")).strip()
