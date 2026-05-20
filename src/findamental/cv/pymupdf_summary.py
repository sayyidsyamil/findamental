from dataclasses import dataclass
from pathlib import Path
import re

import fitz

from findamental.cv.line_item_matcher import LineItemMatcher, parse_numeric_value


@dataclass(frozen=True)
class SummaryRow:
    label: str
    value: float
    period: str
    page_number: int
    table_bbox: tuple[float, float, float, float]
    row_bbox: tuple[float, float, float, float]
    confidence: float
    canonical_name: str


class PyMuPDFSummaryExtractor:
    """Fallback extractor for the Maybank FY2025 summary table.

    This is not a replacement for Docling. It gives us a deterministic real-PDF
    path for the assignment demo cache while Docling/Granite remains the primary
    extraction route for broader PDFs.
    """

    def __init__(self, matcher: LineItemMatcher):
        self.matcher = matcher

    def extract_group_summary(self, pdf_path: Path, page_number: int = 5) -> list[SummaryRow]:
        document = fitz.open(pdf_path)
        page = document[page_number - 1]
        words = page.get_text("words")
        rows = _group_words_by_line(words)
        table_bbox = (55.0, 180.0, 705.0, 412.0)
        extracted: dict[tuple[str, str], SummaryRow] = {}

        for row_words in rows:
            label_words = [w for w in row_words if w[0] < 330]
            value_words = [w for w in row_words if w[0] >= 330]
            if not label_words or not value_words:
                continue
            label = " ".join(w[4] for w in label_words)
            match = self.matcher.match(label, [[label, "0"]])
            if match is None or match.confidence < 85:
                continue

            for period, value_word in _group_value_words(value_words):
                value = parse_numeric_value([label, value_word[4]])
                if value is None:
                    continue

                row_bbox = _bbox(row_words)
                extracted[(match.canonical_name, period)] = SummaryRow(
                    label=label,
                    value=value,
                    period=period,
                    page_number=page_number,
                    table_bbox=table_bbox,
                    row_bbox=row_bbox,
                    confidence=match.confidence,
                    canonical_name=match.canonical_name,
                )

        document.close()
        return list(extracted.values())


def _group_words_by_line(words: list[tuple]) -> list[list[tuple]]:
    rows: list[list[tuple]] = []
    for word in sorted(words, key=lambda w: (round(float(w[1]), 1), float(w[0]))):
        if not rows:
            rows.append([word])
            continue
        current_y = sum(float(w[1]) for w in rows[-1]) / len(rows[-1])
        if abs(float(word[1]) - current_y) <= 2.0:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w[0]) for row in rows]


def _group_value_words(value_words: list[tuple]) -> list[tuple[str, tuple]]:
    numeric = [w for w in value_words if re.search(r"\d", str(w[4]))]
    if len(numeric) < 5:
        return []
    group_years = ["FY_2021", "FY_2022", "FY_2023", "FY_2024", "FY_2025"]
    return list(zip(group_years, sorted(numeric, key=lambda w: w[0])[:5], strict=False))


def _bbox(words: list[tuple]) -> tuple[float, float, float, float]:
    return (
        min(float(w[0]) for w in words),
        min(float(w[1]) for w in words),
        max(float(w[2]) for w in words),
        max(float(w[3]) for w in words),
    )
