from datetime import UTC, datetime
from pathlib import Path
import re

import fitz

from findamental.cv.line_item_matcher import parse_numeric_value
from findamental.index.models import IndexedCell, IndexedDocument, IndexedPage, IndexedRow


class PyMuPDFDocumentIndexer:
    def index_pdf(
        self,
        pdf_path: Path,
        ticker: str,
        company_name: str,
        document_id: str,
    ) -> IndexedDocument:
        document = fitz.open(pdf_path)
        pages = []
        for page_index, page in enumerate(document, start=1):
            words = page.get_text("words")
            rows = _rows_from_words(words, page_index, page.rect.width)
            pages.append(
                IndexedPage(
                    page_number=page_index,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    text=page.get_text("text"),
                    rows=rows,
                )
            )
        document.close()
        return IndexedDocument(
            document_id=document_id,
            ticker=ticker,
            company_name=company_name,
            source_pdf_path=str(pdf_path),
            indexed_at=datetime.now(UTC),
            parser="pymupdf-coordinate-indexer",
            pages=pages,
        )


def _rows_from_words(words: list[tuple], page_number: int, page_width: float) -> list[IndexedRow]:
    visual_rows = _group_words_by_y(words)
    year_columns = _year_columns(visual_rows)
    indexed = []
    current_section = None
    current_unit = None
    for row_words in visual_rows:
        text = " ".join(str(w[4]) for w in row_words).strip()
        if not text:
            continue
        unit = _unit_hint_from_text(text)
        if unit:
            current_unit = unit
        if _looks_like_section(text):
            current_section = text
            continue

        cells = _numeric_cells(row_words, year_columns)
        if not cells:
            continue
        label_words = _label_words(row_words)
        if not label_words:
            continue
        label = " ".join(str(w[4]) for w in label_words).strip()
        if not _useful_label(label):
            continue
        row_bbox = _bbox(row_words)
        indexed.append(
            IndexedRow(
                label=label,
                page_number=page_number,
                bbox=row_bbox,
                table_bbox=_table_bbox_for_row(row_bbox, page_width),
                cells=cells,
                section=current_section,
                unit_hint=current_unit,
            )
        )
    return indexed


def _group_words_by_y(words: list[tuple]) -> list[list[tuple]]:
    rows: list[list[tuple]] = []
    for word in sorted(words, key=lambda w: (round(float(w[1]), 1), float(w[0]))):
        if not rows:
            rows.append([word])
            continue
        current_y = sum(float(w[1]) for w in rows[-1]) / len(rows[-1])
        if abs(float(word[1]) - current_y) <= 4.0:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: float(w[0])) for row in rows]


def _year_columns(rows: list[list[tuple]]) -> list[tuple[str, str | None, float]]:
    columns: list[tuple[str, str | None, float]] = []
    scope_markers = _scope_markers(rows[:8])
    for row in rows[:40]:
        for word in row:
            text = str(word[4])
            if re.fullmatch(r"20\d{2}", text):
                x_center = (float(word[0]) + float(word[2])) / 2
                columns.append((f"FY_{text}", _scope_for_x(x_center, scope_markers), x_center))
    deduped: list[tuple[str, str | None, float]] = []
    for column in sorted(columns, key=lambda item: item[2]):
        if all(abs(column[2] - existing[2]) > 8 for existing in deduped):
            deduped.append(column)
    if _looks_like_group_bank_years(deduped):
        deduped = [
            (name, "Group" if index < 5 else "Bank", x)
            for index, (name, _scope, x) in enumerate(deduped)
        ]
    return deduped


def _numeric_cells(
    row_words: list[tuple],
    year_columns: list[tuple[str, str | None, float]],
) -> list[IndexedCell]:
    cells = []
    for word in row_words:
        text = str(word[4]).strip()
        value = parse_numeric_value(["label", text])
        if value is None:
            continue
        x_center = (float(word[0]) + float(word[2])) / 2
        column = _nearest_column(x_center, year_columns)
        cells.append(
            IndexedCell(
                text=text,
                value=value,
                column=column[0] if column else None,
                scope=column[1] if column else None,
                bbox=(float(word[0]), float(word[1]), float(word[2]), float(word[3])),
            )
        )
    return cells


def _nearest_column(
    x_center: float,
    columns: list[tuple[str, str | None, float]],
) -> tuple[str, str | None, float] | None:
    if not columns:
        return None
    column, distance = min(
        ((column, abs(x_center - column[2])) for column in columns),
        key=lambda item: item[1],
    )
    return column if distance <= 28 else None


def _scope_markers(rows: list[list[tuple]]) -> list[tuple[str, float]]:
    markers = []
    for row in rows:
        for word in row:
            text = str(word[4]).strip()
            if text.lower() in {"group", "bank"}:
                markers.append((text.title(), (float(word[0]) + float(word[2])) / 2))
    return sorted(markers, key=lambda item: item[1])


def _scope_for_x(x_center: float, markers: list[tuple[str, float]]) -> str | None:
    if not markers:
        return None
    scope, _ = min(markers, key=lambda marker: abs(x_center - marker[1]))
    return scope


def _looks_like_group_bank_years(columns: list[tuple[str, str | None, float]]) -> bool:
    names = [column[0] for column in columns]
    return names[:7] == [
        "FY_2021",
        "FY_2022",
        "FY_2023",
        "FY_2024",
        "FY_2025",
        "FY_2024",
        "FY_2025",
    ]


def _unit_hint_from_text(text: str) -> str | None:
    normalized = text.lower().replace("’", "'").replace("`", "'")
    if "rm' million" in normalized or "rm million" in normalized:
        return "MYR million"
    if "rm'000" in normalized or "rm '000" in normalized or "rm000" in normalized:
        return "MYR thousand"
    if re.search(r"\bsen\b", normalized):
        return "sen"
    if "(%)" in normalized or re.search(r"\bratio\b", normalized):
        return "%"
    return None


def _label_words(row_words: list[tuple]) -> list[tuple]:
    first_numeric_x = None
    for word in row_words:
        if parse_numeric_value(["label", str(word[4])]) is not None:
            first_numeric_x = float(word[0])
            break
    if first_numeric_x is None:
        return []
    return [word for word in row_words if float(word[0]) < first_numeric_x - 8]


def _useful_label(label: str) -> bool:
    if len(label) < 3:
        return False
    if re.fullmatch(r"[\d\s,().%-]+", label):
        return False
    return any(char.isalpha() for char in label)


def _looks_like_section(text: str) -> bool:
    alpha = re.sub(r"[^A-Za-z ]", "", text).strip()
    return len(alpha) >= 8 and alpha.upper() == alpha and not re.search(r"\d", text)


def _bbox(words: list[tuple]) -> tuple[float, float, float, float]:
    return (
        min(float(w[0]) for w in words),
        min(float(w[1]) for w in words),
        max(float(w[2]) for w in words),
        max(float(w[3]) for w in words),
    )


def _table_bbox_for_row(row_bbox: tuple[float, float, float, float], page_width: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = row_bbox
    return (max(0.0, x0 - 12), max(0.0, y0 - 90), min(page_width, x1 + 12), y1 + 90)
