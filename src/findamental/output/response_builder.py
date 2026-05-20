from pathlib import Path

from findamental.cache.store import ExtractedFiling, ExtractedLineItem
from findamental.output.telegram_response import TelegramResponse


def build_lookup_response(
    filing: ExtractedFiling,
    item: ExtractedLineItem,
    cache_dir: Path,
) -> TelegramResponse:
    image = cache_dir / item.annotated_image_path if item.annotated_image_path else None
    value_text = _format_value(item.value, item.unit)
    label = _display_label(item)
    text = (
        f"<b>{filing.company_name} ({filing.ticker}) - {item.period}</b>\n"
        f"{label}: <b>{value_text}</b>\n"
        f"Proof: {filing.filing_type.replace('_', ' ')}, page {item.source_page}\n"
        f"Score: {_format_score(item.confidence)}"
    )
    return TelegramResponse(
        text=text,
        image_path=image if image and image.exists() else None,
        image_paths=[image] if image and image.exists() else None,
        inline_buttons=[
            ("Chart trend", f"chart:{filing.ticker}:{item.name}"),
            ("Valuation", f"valuation:{filing.ticker}"),
        ],
    )


def _format_value(value: float, unit: str) -> str:
    number = _format_exact_float(value)
    if unit == "sen":
        return f"{number} sen"
    if unit == "MYR million":
        return f"RM {number} million"
    if unit == "MYR":
        return f"RM {number}"
    return f"{number} {unit}".strip()


def _format_exact_float(value: float) -> str:
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,}".rstrip("0").rstrip(".")


def _format_score(score: float) -> str:
    if score.is_integer():
        return f"{int(score)}%"
    return f"{score:.2f}%".rstrip("0").rstrip(".")


def _display_label(item: ExtractedLineItem) -> str:
    if item.name == "eps" and "diluted" in item.raw_label.lower():
        return "Diluted EPS"
    labels = {
        "eps": "EPS",
        "net_income": "Net Income",
        "operating_income": "Operating Income",
        "total_assets": "Total Assets",
        "total_equity": "Total Equity",
        "revenue": "Revenue",
    }
    return labels.get(item.name, item.name.replace("_", " ").title())
