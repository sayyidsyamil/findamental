import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from rich.console import Console

from findamental.cache.store import CacheStore, ExtractedFiling, ExtractedLineItem
from findamental.config import settings
from findamental.cv.line_item_matcher import LineItemMatcher, parse_numeric_value
from findamental.maybank_cache import build_maybank_cache
from findamental.output.telegram_response import TelegramResponse
from findamental.service import FindamentalService, intro_text


console = Console()


def query_main() -> None:
    parser = argparse.ArgumentParser(description="Query the Findamental local cache")
    parser.add_argument("--json", action="store_true", help="Output structured JSON for charting")
    parser.add_argument("query", nargs="*")
    args = parser.parse_args()
    query = " ".join(args.query).strip()
    if not query:
        if args.json:
            print(json.dumps({"error": "No query provided"}))
            return
        console.print(intro_text())
        return
    response = asyncio.run(FindamentalService().answer(query))
    if args.json:
        chart_data = _build_chart_data(response)
        print(json.dumps(chart_data))
        return
    console.print(response.text)
    if response.image_path:
        console.print(f"Image: {response.image_path}")
    for image_path in response.image_paths or []:
        if image_path != response.image_path:
            console.print(f"Image: {image_path}")


def extract_main() -> None:
    from findamental.cv.docling_pipeline import DoclingExtractor

    matcher = LineItemMatcher(settings.DATA_DIR / "line_items_dict.json")
    store = CacheStore(settings.CACHE_DIR)
    pdfs = sorted(settings.DEMO_FILINGS_DIR.glob("*.pdf"))
    root_maybank_pdf = settings.DATA_DIR.parent / "maybank-ar2025-financial-statements.pdf"
    if root_maybank_pdf.exists() and root_maybank_pdf not in pdfs:
        pdfs.append(root_maybank_pdf)
    if not pdfs:
        console.print("[red]No PDFs found in data/demo_filings/[/red]")
        return

    for pdf in pdfs:
        ticker, company_name, filing_type = _infer_filing_metadata(pdf)
        if ticker == "1155" and filing_type == "FY_2025_FINANCIAL_STATEMENTS":
            filing = build_maybank_cache(pdf, matcher)
            store.save(filing)
            console.print(
                f"[green]Saved {filing.ticker} {filing.filing_type}: "
                f"{len(filing.line_items)} real PDF items[/green]"
            )
            continue

        extractor = DoclingExtractor()
        tables = extractor.extract_tables_with_bboxes(pdf)
        line_items: list[ExtractedLineItem] = []
        for table in tables:
            rows = table["rows"]
            for metric in matcher.synonyms:
                match = matcher.match(metric, rows)
                if match is None:
                    continue
                value = parse_numeric_value(rows[match.row_index])
                if value is None:
                    continue
                line_items.append(
                    ExtractedLineItem(
                        name=match.canonical_name,
                        raw_label=match.raw_label,
                        value=value,
                        period=_period_from_filing_type(filing_type),
                        source_page=table["page_number"],
                        source_bbox=table["bbox"],
                        annotated_image_path="",
                        confidence=match.confidence,
                    )
                )
        store.save(
            ExtractedFiling(
                ticker=ticker,
                company_name=company_name,
                filing_type=filing_type,
                source_pdf_path=str(pdf),
                extracted_at=datetime.utcnow(),
                line_items=line_items,
            )
        )
        console.print(f"[green]Saved {ticker} {filing_type}: {len(line_items)} items[/green]")


def _infer_filing_metadata(pdf: Path) -> tuple[str, str, str]:
    name = pdf.stem.lower()
    mapping = {
        "maybank": ("1155", "Malayan Banking Berhad"),
        "tenaga": ("5347", "Tenaga Nasional Berhad"),
        "tnb": ("5347", "Tenaga Nasional Berhad"),
        "public": ("1295", "Public Bank Berhad"),
        "hartalega": ("5168", "Hartalega Holdings Berhad"),
        "airasia": ("5099", "AirAsia X Berhad"),
        "aax": ("5099", "AirAsia X Berhad"),
    }
    ticker, company = next((value for key, value in mapping.items() if key in name), ("UNKNOWN", pdf.stem))
    if "ar2025" in name or ("2025" in name and "financial" in name):
        filing_type = "FY_2025_FINANCIAL_STATEMENTS"
    elif "q3" in name and "2024" in name:
        filing_type = "Q3_2024_INTERIM"
    else:
        filing_type = "DEMO_FILING"
    return ticker, company, filing_type


def _period_from_filing_type(filing_type: str) -> str:
    if filing_type.startswith("FY_2025"):
        return "FY_2025"
    if filing_type.startswith("Q3_2024"):
        return "Q3_2024"
    return filing_type


def _parse_chart_number(raw: str) -> float | None:
    s = raw.strip().replace(",", "")
    is_negative = s.startswith("(") and s.endswith(")")
    if is_negative:
        s = "-" + s[1:-1]
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _infer_chart_unit(labels: list[str]) -> str:
    joined = " ".join(labels).lower()
    if any(t in joined for t in ["%", "ratio", "roe", "roa", "margin", "return on"]):
        return "%"
    if any(t in joined for t in ["eps", "sen", "per share"]):
        return "sen"
    return "RM million"


def _build_chart_data(response: TelegramResponse) -> dict:
    text = response.text
    labels: list[str] = []
    values: list[float] = []
    title = ""
    current_period: str | None = None

    for line in text.splitlines():
        if not title:
            m = re.search(r"<b>(.+?)</b>", line)
            if m:
                title = m.group(1)

        header_match = re.search(r"<b>(?:.*?)\s*-\s*(.+?)</b>", line)
        if header_match:
            current_period = header_match.group(1).strip()

        value_match = re.search(r":\s*<b>(.+?)</b>", line)
        if value_match and current_period:
            num = _parse_chart_number(value_match.group(1))
            if num is not None:
                label_m = re.match(r"([^:\n]+?)\s*:", line)
                label = label_m.group(1).strip() if label_m else "Value"
                labels.append(f"{label} ({current_period})")
                values.append(num)

    unit = _infer_chart_unit(labels)
    return {"title": title, "labels": labels, "values": values, "unit": unit}
