from pathlib import Path
import re

from findamental.calculations import CalculationInput, CalculationResult, FinancialCalculator
from findamental.cache.store import CacheStore
from findamental.config import settings
from findamental.cv.line_item_matcher import LineItemMatcher
from findamental.index.models import IndexedCell
from findamental.index.resolver import DocumentResolver, ResolvedLookup
from findamental.index.store import DocumentIndexStore
from findamental.maybank_cache import maybank_pdf_path
from findamental.output.response_builder import build_lookup_response
from findamental.output.telegram_response import TelegramResponse
from findamental.query_router import QueryRouter
from findamental.maybank_cache import ensure_maybank_cache
from findamental.reports import AnnualReportManager


class FindamentalService:
    def __init__(self):
        self.store = CacheStore(settings.CACHE_DIR)
        self.index_store = DocumentIndexStore()
        self.matcher = LineItemMatcher(settings.DATA_DIR / "line_items_dict.json")
        self.resolver = DocumentResolver(self.matcher)
        self.calculator = FinancialCalculator()
        self.report_manager = AnnualReportManager(index_store=self.index_store)
        self.router = QueryRouter(
            api_key=settings.LLM_API_KEY or settings.OPENROUTER_API_KEY,
            company_index_path=settings.DATA_DIR / "company_index.json",
            synonyms_path=settings.DATA_DIR / "line_items_dict.json",
            model=settings.LLM_MODEL or settings.OPENROUTER_MODEL,
            base_url=settings.LLM_BASE_URL,
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
        else:
            indexed_response = self._answer_from_annual_report(
                parsed.ticker,
                user_text,
                parsed.metric,
                parsed.period,
            )
            if indexed_response is not None:
                return indexed_response

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
                    "Report not indexed yet. I need full ingest mode to fetch the annual report."
                )
            )

        filing = self.store.filing_for_item(parsed.ticker, item)
        if filing is None:
            return TelegramResponse(text="Hit found. Source filing missing.")
        return build_lookup_response(filing, item, settings.CACHE_DIR)

    def _answer_from_annual_report(
        self,
        ticker: str,
        user_text: str,
        parsed_metric: str | None,
        period: str | None,
    ) -> TelegramResponse | None:
        try:
            document = self.report_manager.ensure_indexed_report(ticker, period)
        except Exception as exc:
            return TelegramResponse(text=f"Report ingest failed: {exc}")
        if document is None:
            return None
        calculation = self.calculator.calculate(document, user_text, period)
        if calculation is not None:
            return _response_from_calculation(calculation)
        resolved = self.resolver.resolve_many(document, user_text, parsed_metric, period)
        if not resolved and period is not None:
            resolved = self.resolver.resolve_many(document, user_text, parsed_metric, None)
        resolved = _shape_lookup_matches(resolved, parsed_metric, user_text)
        if not resolved:
            return TelegramResponse(
                text=(
                    f"Report indexed.\n"
                    f"Company: {document.company_name} ({document.ticker})\n"
                    f"Metric not found: {parsed_metric or user_text}"
                )
            )
        return _response_from_resolved_lookups(resolved)

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
        calculation = self.calculator.calculate(document, user_text, period)
        if calculation is not None:
            return _response_from_calculation(calculation)
        resolved = self.resolver.resolve_many(document, user_text, parsed_metric, period)
        resolved = _shape_lookup_matches(resolved, parsed_metric, user_text)
        if not resolved:
            return None
        return _response_from_resolved_lookups(resolved)


def _supported_companies(company_index_path: Path) -> str:
    import json

    companies = json.loads(company_index_path.read_text(encoding="utf-8"))
    lines = ["Company not found. Supported:"]
    lines.extend(f"- {ticker}: {info['name']}" for ticker, info in companies.items())
    lines.append(
        "\nIf it is a Bursa company not listed here, add it to data/company_index.json and "
        "Findamental can ingest its annual report on demand."
    )
    return "\n".join(lines)


def intro_text() -> str:
    return (
        "<b>Hi. I am Findamental.</b>\n"
        "Ask me Bursa filing questions. I answer with number, page proof, screenshot.\n\n"
        "<b>Try:</b>\n"
        "- Maybank operating revenue 2021\n"
        "- Maybank 2025 ROE\n"
        "- Maybank 2025 PE ratio\n"
        "- calculate Maybank revenue growth 2025\n"
        "- CIMB revenue 2024\n"
        "- Tenaga revenue 2024\n"
        "- YTLPOWR revenue\n"
        "- Maybank FY 2025 total assets\n"
        "- Maybank FY 2021 diluted earning\n"
        "- Maybank 2024 cost to income ratio\n\n"
        "Current mode: on-demand annual report ingest plus local document search."
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


def _response_from_calculation(calculation: CalculationResult) -> TelegramResponse:
    lines = [
        f"<b>{calculation.company_name} ({calculation.ticker}) - "
        f"{calculation.scope} {calculation.period}</b>",
        f"{calculation.metric}: <b>{_format_calculated_value(calculation.value, calculation.unit)}</b>",
        f"Formula: {calculation.formula}",
        "Inputs:",
    ]
    for item in calculation.inputs:
        lines.append(
            f"- {item.label}: {_format_input_value(item)} "
            f"(page {item.page_number})"
        )
    pages = ", ".join(str(page) for page in calculation.source_pages)
    lines.append(f"Proof: FY 2025 FINANCIAL STATEMENTS, page {pages}")
    return TelegramResponse(text="\n".join(lines))


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
                f"Proof: {_source_label(match.document)}, page {match.row.page_number} | "
                f"Score: {_format_score(match.score)}"
            )
        text = "\n".join(lines)
    return TelegramResponse(
        text=text,
        image_path=image_paths[0] if image_paths else None,
        image_paths=image_paths,
    )


def _shape_lookup_matches(
    matches: list[ResolvedLookup],
    parsed_metric: str | None,
    user_text: str,
) -> list[ResolvedLookup]:
    valued = [match for match in matches if match.cell.value is not None]
    if not valued:
        return []

    if parsed_metric == "revenue" and _is_plain_revenue_query(user_text):
        primary = [match for match in valued if _is_primary_revenue_match(match)]
        if primary:
            return _limit_matches(_dedupe_financial_cells(_prefer_revenue_rows(primary)), 8)

    if parsed_metric == "net_income" and _is_plain_net_profit_query(user_text):
        primary = [match for match in valued if _is_primary_net_profit_match(match)]
        if primary:
            return _limit_matches(_dedupe_financial_cells(primary), 8)

    return _limit_matches(_dedupe_financial_cells(valued), 12)


def _is_plain_net_profit_query(user_text: str) -> bool:
    text = _norm(user_text)
    has_net_profit = "net profit" in text or "profit for" in text or "net income" in text
    if not has_net_profit:
        return False
    noisy_terms = {"segment", "before tax", "before taxation", "gain on", "loss on"}
    return not any(term in text for term in noisy_terms)


def _is_primary_net_profit_match(match: ResolvedLookup) -> bool:
    label = _norm(match.row.label)
    if label in {
        "net profit",
        "profit for the year",
        "profit for the financial year",
        "profit for the period",
        "profit attributable to owners",
        "profit attributable to equity holders",
        "profit attributable to equity holders of the bank",
        "profit attributable to equity holders of the parent",
    }:
        return True
    if label.startswith("profit for the"):
        return True
    if label.startswith("profit attributable"):
        return True
    return False


def _is_plain_revenue_query(user_text: str) -> bool:
    text = _norm(user_text)
    noisy_revenue_terms = {
        "growth",
        "recognised",
        "recognized",
        "contract",
        "segment",
        "insurance",
        "disaggregation",
    }
    return "revenue" in text and not any(term in text for term in noisy_revenue_terms)


def _is_primary_revenue_match(match: ResolvedLookup) -> bool:
    label = _norm(match.row.label)
    section = _norm(match.row.section or "")
    if label in {
        "revenue",
        "total revenue",
        "operating revenue",
        "gross revenue",
        "revenue from contracts with customers",
    }:
        return True
    if label.startswith("total revenue"):
        return True
    if label == "total" and "revenue" in section:
        return True
    return False


def _prefer_revenue_rows(matches: list[ResolvedLookup]) -> list[ResolvedLookup]:
    million_rows = [match for match in matches if match.row.unit_hint == "MYR million"]
    candidates = million_rows or matches
    deduped = _dedupe_financial_cells(candidates)

    groups: dict[tuple, list[ResolvedLookup]] = {}
    for match in deduped:
        row_key = (
            match.document.document_id,
            match.row.page_number,
            _norm(match.row.label),
        )
        groups.setdefault(row_key, []).append(match)

    row_maxes = {}
    global_max = 0.0
    for key, group in groups.items():
        row_max = max(abs(m.cell.value or 0.0) for m in group)
        row_maxes[key] = row_max
        global_max = max(global_max, row_max)

    if global_max <= 0:
        return deduped

    kept: list[ResolvedLookup] = []
    for key, group in groups.items():
        label = key[2]
        if row_maxes[key] >= global_max * 0.8 or label.startswith("total revenue"):
            kept.extend(group)

    return kept or deduped


def _dedupe_financial_cells(matches: list[ResolvedLookup]) -> list[ResolvedLookup]:
    best_by_slot: dict[tuple[str, int, str, str | None, str | None], ResolvedLookup] = {}
    for match in matches:
        key = (
            match.document.document_id,
            match.row.page_number,
            _norm(match.row.label),
            match.cell.column,
            match.cell.scope,
        )
        existing = best_by_slot.get(key)
        if existing is None or _financial_cell_rank(match) > _financial_cell_rank(existing):
            best_by_slot[key] = match

    unique: list[ResolvedLookup] = []
    seen_values: set[tuple[str, str, str | None, str | None, str]] = set()
    for match in sorted(
        best_by_slot.values(),
        key=lambda item: (-item.score, item.row.page_number, _norm(item.row.label)),
    ):
        value_key = (
            match.document.document_id,
            _norm(match.row.label),
            match.cell.column,
            match.cell.scope,
            _clean_number_text(match.cell.text),
        )
        if value_key in seen_values:
            continue
        seen_values.add(value_key)
        unique.append(match)
    return unique


def _financial_cell_rank(match: ResolvedLookup) -> tuple[float, float]:
    value = match.cell.value or 0.0
    text = match.cell.text.strip()
    note_penalty = -1000.0 if abs(value) < 100 and re_fullmatch_int(text) else 0.0
    return (note_penalty + abs(value), match.score)


def re_fullmatch_int(text: str) -> bool:
    return bool(re.fullmatch(r"\(?\d{1,2}\)?", text.replace(",", "")))


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _limit_matches(matches: list[ResolvedLookup], limit: int) -> list[ResolvedLookup]:
    return matches[:limit]


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
    ts = int(resolved.document.indexed_at.timestamp())
    image_name = f"{resolved.document.document_id}_{_slug(resolved.row.label)}_{suffix}_{ts}.png"
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
        f"Proof: {_source_label(resolved.document)}, page {resolved.row.page_number}\n"
        f"Score: {_format_score(resolved.score)}"
    )


def _source_label(document) -> str:
    return document.document_id.replace("_", " ")


def _infer_unit(label: str, section: str | None = None, unit_hint: str | None = None) -> str:
    lowered = label.lower()
    section_text = (section or "").lower()
    if unit_hint in {"MYR million", "MYR thousand", "MYR"}:
        return unit_hint
    if "revenue" in lowered:
        return "MYR million"
    if lowered == "total" and "revenue" in section_text:
        return "MYR million"
    if unit_hint and not (
        unit_hint in {"sen", "%"} and any(term in lowered for term in {"asset", "revenue", "income", "profit"})
    ):
        return unit_hint
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
    value = cell.value
    if unit == "MYR million" and value is not None and abs(value) >= 1_000_000:
        unit = "MYR thousand"
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
    return text.strip().replace("âˆ’", "-")


def _format_score(score: float) -> str:
    clamped = min(score, 100.0)
    if clamped.is_integer():
        return f"{int(clamped)}%"
    return f"{clamped:.2f}%".rstrip("0").rstrip(".")


def _format_calculated_value(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value:,.2f}%"
    if unit == "x":
        return f"{value:,.2f}x"
    return f"{value:,.2f} {unit}".strip()


def _format_input_value(item: CalculationInput) -> str:
    if item.label.lower().startswith("share price"):
        return f"RM {item.raw_text}"
    if item.unit == "MYR million":
        return f"RM {item.raw_text} million"
    if item.unit == "MYR thousand":
        return f"RM {item.raw_text} thousand"
    if item.unit == "sen":
        return f"{item.raw_text} sen"
    if item.unit == "%":
        return f"{item.raw_text}%"
    return item.raw_text


def _display_label(label: str) -> str:
    if label.lower() == "basic earnings":
        return "Basic EPS"
    if label.lower() == "diluted earnings":
        return "Diluted EPS"
    return label


def _period_label(resolved: ResolvedLookup) -> str:
    period = resolved.period or "matched period"
    if resolved.cell.scope == "Group":
        return f"Group {period}"
    if resolved.cell.scope == "Bank" and resolved.document.ticker == "1155":
        return f"Bank {period}"
    return period


def _slug(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]

