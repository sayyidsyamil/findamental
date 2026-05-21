from pathlib import Path

from findamental.cache.store import CacheStore
from findamental.config import settings
from findamental.cv.line_item_matcher import LineItemMatcher
from findamental.index.models import IndexedCell
from findamental.index.resolver import DocumentResolver, ResolvedLookup
from findamental.index.store import DocumentIndexStore
from findamental.maybank_cache import FILING_TYPE, maybank_pdf_path
from findamental.output.response_builder import build_lookup_response
from findamental.output.telegram_response import TelegramResponse
from findamental.query_router import QueryRouter
from findamental.maybank_cache import ensure_maybank_cache


class FindamentalService:
    def __init__(self):
        self.store = CacheStore(settings.CACHE_DIR)
        self.index_store = DocumentIndexStore()
        self.matcher = LineItemMatcher(settings.DATA_DIR / "line_items_dict.json")
        self.resolver = DocumentResolver(self.matcher)
        self.router = QueryRouter(
            api_key=settings.OPENROUTER_API_KEY,
            company_index_path=settings.DATA_DIR / "company_index.json",
            synonyms_path=settings.DATA_DIR / "line_items_dict.json",
            model=settings.OPENROUTER_MODEL,
        )

    async def answer(self, user_text: str) -> TelegramResponse:
        if _is_intro_request(user_text):
            return TelegramResponse(text=intro_text())

        parsed = await self.router.parse(user_text)
        if parsed.ticker is None:
            return TelegramResponse(text=_supported_companies(settings.DATA_DIR / "company_index.json"))

        if parsed.ticker == "1155":
            indexed_response = self._answer_from_document_index(user_text, parsed.metric, parsed.period)
            if indexed_response is not None:
                return indexed_response
            ensure_maybank_cache(self.store)

        item = self.store.find_line_item(parsed.ticker, parsed.metric, parsed.period)
        if item is None:
            available = [
                filing for filing in self.store.list_all() if filing.ticker == parsed.ticker
            ]
            metrics = sorted({line.name for filing in available for line in filing.line_items})
            metric_text = ", ".join(metrics) if metrics else "none yet"
            return TelegramResponse(
                text=(
                    f"No hit.\n"
                    f"Ticker: {parsed.ticker}\n"
                    f"Metric: {parsed.metric}\n"
                    f"Cached metrics: {metric_text}\n"
                    "Need new PDF index. Run: make extract"
                )
            )

        filing = self.store.filing_for_item(parsed.ticker, item)
        if filing is None:
            return TelegramResponse(text="Hit found. Source filing missing.")
        return build_lookup_response(filing, item, settings.CACHE_DIR)

    def _answer_from_document_index(
        self,
        user_text: str,
        parsed_metric: str | None,
        period: str | None,
    ) -> TelegramResponse | None:
        pdf = maybank_pdf_path()
        if not pdf.exists():
            return None
        document = self.index_store.ensure_pdf_index(
            pdf_path=pdf,
            ticker="1155",
            company_name="Malayan Banking Berhad",
            document_id="1155_FY_2025_FINANCIAL_STATEMENTS",
        )
        resolved = self.resolver.resolve_many(document, user_text, parsed_metric, period)
        if not resolved:
            return None
        return _response_from_resolved_lookups(resolved)


def _supported_companies(company_index_path: Path) -> str:
    import json

    companies = json.loads(company_index_path.read_text(encoding="utf-8"))
    lines = ["Company not found. Supported:"]
    lines.extend(f"- {ticker}: {info['name']}" for ticker, info in companies.items())
    return "\n".join(lines)


def intro_text() -> str:
    return (
        "<b>Hi. I am Findamental.</b>\n"
        "Ask me Bursa filing questions. I answer with number, page proof, screenshot.\n\n"
        "<b>Try:</b>\n"
        "- Maybank operating revenue 2021\n"
        "- Maybank 2025 ROE\n"
        "- Maybank FY 2025 total assets\n"
        "- Maybank FY 2021 diluted earning\n"
        "- Maybank 2024 cost to income ratio\n\n"
        "Current report: Maybank FY2025 financial statements."
    )


def _is_intro_request(user_text: str) -> bool:
    text = user_text.strip().lower()
    return text in {
        "",
        "hi",
        "hello",
        "hey",
        "start",
        "/start",
        "help",
        "/help",
        "findamental",
        "/findamental",
    }


def _response_from_resolved_lookup(resolved: ResolvedLookup) -> TelegramResponse:
    return _response_from_resolved_lookups([resolved])


def _response_from_resolved_lookups(matches: list[ResolvedLookup]) -> TelegramResponse:
    image_paths = _image_paths_for_matches(matches)
    if len(matches) == 1:
        text = _text_for_match(matches[0])
    else:
        lines = [f"<b>{len(matches)} hits.</b>"]
        for index, match in enumerate(matches, start=1):
            value = match.cell.value
            if value is None:
                continue
            unit = _infer_unit(match.row.label, match.row.section, match.row.unit_hint)
            lines.append(
                "\n"
                f"{index}. <b>{match.document.company_name} ({match.document.ticker}) - "
                f"{_period_label(match)}</b>\n"
                f"{_display_label(match.row.label)}: <b>{_format_cell_value(match.cell, unit)}</b>\n"
                f"Proof: {FILING_TYPE.replace('_', ' ')}, page {match.row.page_number} | "
                f"Score: {_format_score(match.score)}"
            )
        text = "\n".join(lines)
    return TelegramResponse(
        text=text,
        image_path=image_paths[0] if image_paths else None,
        image_paths=image_paths,
    )


def _image_paths_for_matches(matches: list[ResolvedLookup]) -> list[Path]:
    paths: list[Path] = []
    seen_visual_sources: set[tuple[str, int, tuple[int, ...]]] = set()
    for match in matches:
        row_bbox_key = tuple(int(value) for value in match.row.bbox)
        key = (match.document.document_id, match.row.page_number, row_bbox_key)
        if key in seen_visual_sources:
            continue
        seen_visual_sources.add(key)
        paths.append(_image_for_match(match))
    return paths


def _image_for_match(resolved: ResolvedLookup) -> Path:
    from findamental.cv.annotator import PageAnnotator

    scope = _slug(resolved.cell.scope) if resolved.cell.scope else None
    suffix = "_".join(
        part
        for part in [
            f"p{resolved.row.page_number}",
            scope,
            resolved.period or "value",
            f"x{int(resolved.cell.bbox[0])}",
            f"y{int(resolved.row.bbox[1])}",
        ]
        if part
    )
    image_name = f"{resolved.document.document_id}_{_slug(resolved.row.label)}_{suffix}.png"
    image_path = settings.CACHE_DIR / image_name
    if not image_path.exists():
        PageAnnotator().crop_and_annotate(
            pdf_path=Path(resolved.document.source_pdf_path),
            page_number=resolved.row.page_number,
            bbox=resolved.row.table_bbox,
            row_bbox=resolved.row.bbox,
            output_path=image_path,
        )
    return image_path


def _text_for_match(resolved: ResolvedLookup) -> str:
    unit = _infer_unit(resolved.row.label, resolved.row.section, resolved.row.unit_hint)
    value = resolved.cell.value
    if value is None:
        return f"Hit: {resolved.row.label}\nValue parse failed."
    label = _display_label(resolved.row.label)
    period = _period_label(resolved)
    return (
        f"<b>{resolved.document.company_name} ({resolved.document.ticker}) - {period}</b>\n"
        f"{label}: <b>{_format_cell_value(resolved.cell, unit)}</b>\n"
        f"Proof: {FILING_TYPE.replace('_', ' ')}, page {resolved.row.page_number}\n"
        f"Score: {_format_score(resolved.score)}"
    )


def _infer_unit(label: str, section: str | None = None, unit_hint: str | None = None) -> str:
    if unit_hint:
        return unit_hint
    lowered = label.lower()
    section_text = (section or "").lower()
    if "sen" in lowered or "earning" in lowered or "per share" in lowered or "dividend" in lowered:
        return "sen"
    if "share price" in lowered:
        return "MYR"
    percentage_terms = [
        "ratio",
        "return on",
        "margin",
        "cost to income",
        "gross impaired",
        "loan loss coverage",
        "capital ratio",
    ]
    if any(term in lowered for term in percentage_terms):
        return "%"
    if "share information" in section_text and "market capitalisation" not in lowered:
        return "MYR"
    return "MYR million"


def _format_cell_value(cell: IndexedCell, unit: str) -> str:
    raw = _clean_number_text(cell.text)
    if unit == "sen":
        return f"{raw} sen"
    if unit == "%":
        return f"{raw}%"
    if unit == "MYR":
        return f"RM {raw}"
    if unit == "MYR thousand":
        return f"RM {raw} thousand"
    return f"RM {raw} million"


def _clean_number_text(text: str) -> str:
    return text.strip().replace("−", "-")


def _format_score(score: float) -> str:
    clamped = min(score, 100.0)
    if clamped.is_integer():
        return f"{int(clamped)}%"
    return f"{clamped:.2f}%".rstrip("0").rstrip(".")


def _display_label(label: str) -> str:
    if label.lower() == "basic earnings":
        return "Basic EPS"
    if label.lower() == "diluted earnings":
        return "Diluted EPS"
    return label


def _period_label(resolved: ResolvedLookup) -> str:
    period = resolved.period or "matched period"
    return f"{resolved.cell.scope} {period}" if resolved.cell.scope else period


def _slug(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]
