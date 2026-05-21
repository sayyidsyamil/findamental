from dataclasses import dataclass
import re

from rapidfuzz import fuzz

from findamental.cv.line_item_matcher import LineItemMatcher
from findamental.index.models import IndexedCell, IndexedDocument, IndexedRow


@dataclass(frozen=True)
class ResolvedLookup:
    document: IndexedDocument
    row: IndexedRow
    cell: IndexedCell
    metric_label: str
    period: str | None
    score: float


class DocumentResolver:
    def __init__(self, matcher: LineItemMatcher):
        self.matcher = matcher

    def resolve(
        self,
        document: IndexedDocument,
        query_text: str,
        parsed_metric: str | None,
        period: str | None,
    ) -> ResolvedLookup | None:
        matches = self.resolve_many(document, query_text, parsed_metric, period)
        return matches[0] if matches else None

    def resolve_many(
        self,
        document: IndexedDocument,
        query_text: str,
        parsed_metric: str | None,
        period: str | None,
        max_results: int | None = None,
    ) -> list[ResolvedLookup]:
        metric_query = _metric_query(query_text, document.company_name, parsed_metric, period)
        matches: list[ResolvedLookup] = []
        for page in document.pages:
            for row in page.rows:
                cells = _cells_for_period(row, period)
                score = _row_score(row, metric_query, parsed_metric, self.matcher)
                for cell in cells:
                    cell_score = score
                    if period and cell.column == period:
                        cell_score += 25
                    if cell_score >= 58:
                        matches.append(
                            ResolvedLookup(document, row, cell, row.label, cell.column, cell_score)
                        )

        if not matches:
            return []
        matches = _dedupe_matches(matches)
        matches.sort(key=lambda match: (-match.score, match.row.page_number, match.row.label))
        best_score = matches[0].score
        strong = [match for match in matches if match.score >= max(70.0, best_score - 12.0)]
        if max_results is not None:
            return strong[:max_results]
        return strong


def _row_score(
    row: IndexedRow,
    metric_query: str,
    parsed_metric: str | None,
    matcher: LineItemMatcher,
) -> float:
    label = _normalize(row.label)
    query = _expand_abbreviations(_normalize(metric_query))
    score = float(fuzz.token_set_ratio(query, label))
    score += _token_overlap_bonus(query, label)
    if parsed_metric and _parsed_metric_is_supported_by_query(parsed_metric, metric_query, matcher):
        phrases = matcher.synonyms.get(parsed_metric, [])
        if phrases:
            score = max(score, max(float(fuzz.token_set_ratio(label, phrase)) for phrase in phrases))
            if any(label == phrase or label.startswith(phrase) for phrase in phrases):
                score += 25.0
    return score


def _parsed_metric_is_supported_by_query(
    parsed_metric: str,
    metric_query: str,
    matcher: LineItemMatcher,
) -> bool:
    phrases = matcher.synonyms.get(parsed_metric, [])
    query = _normalize(metric_query)
    return any(float(fuzz.token_set_ratio(query, phrase)) >= 80 for phrase in phrases)


def _cells_for_period(row: IndexedRow, period: str | None) -> list[IndexedCell]:
    if period:
        exact = [cell for cell in row.cells if cell.column == period]
        if exact:
            return exact
        return []
    return [cell for cell in row.cells if cell.value is not None]


def _dedupe_matches(matches: list[ResolvedLookup]) -> list[ResolvedLookup]:
    seen = set()
    deduped = []
    for match in matches:
        key = (match.row.page_number, match.row.label, match.cell.column, match.cell.scope, match.cell.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(match)
    return deduped


def _metric_query(
    query_text: str,
    company_name: str,
    parsed_metric: str | None,
    period: str | None,
) -> str:
    text = query_text.lower()
    for token in ["maybank", "malayan banking", company_name.lower(), "berhad", "bhd"]:
        text = text.replace(token, " ")
    if period:
        text = text.replace(period.lower().replace("_", " "), " ")
        text = text.replace(period.lower(), " ")
        text = text.replace(period[-4:], " ")
    text = re.sub(r"\bfy\b|\bfinancial year\b|\bq[1-4]\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        return _expand_abbreviations(text)
    return parsed_metric.replace("_", " ") if parsed_metric else query_text


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("_", " ")).strip()


def _expand_abbreviations(text: str) -> str:
    replacements = {
        "roe": "return on equity",
        "eps": "earnings",
        "nim": "net interest margin",
        "casa": "current account savings account",
    }
    expanded = text
    for short, long in replacements.items():
        expanded = re.sub(rf"\b{re.escape(short)}\b", long, expanded)
    return expanded


def _token_overlap_bonus(query: str, label: str) -> float:
    query_tokens = {
        token for token in re.findall(r"[a-z]+", query)
        if token not in {"total", "show", "me", "what", "is", "the"}
    }
    label_tokens = set(re.findall(r"[a-z]+", label))
    if not query_tokens:
        return 0.0
    overlap = query_tokens & label_tokens
    bonus = 10.0 * (len(overlap) / len(query_tokens))
    if query_tokens.issubset(label_tokens):
        bonus += 8.0
    return bonus
