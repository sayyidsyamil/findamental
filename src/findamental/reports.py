from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from urllib.parse import quote_plus, unquote, urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from findamental.config import settings
from findamental.index.models import IndexedDocument
from findamental.index.store import DocumentIndexStore

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


@dataclass(frozen=True)
class ReportRef:
    ticker: str
    company_name: str
    year: int
    url: str
    source: str

    @property
    def document_id(self) -> str:
        return f"{self.ticker}_FY_{self.year}_ANNUAL_REPORT"

    @property
    def filename(self) -> str:
        return f"{self.ticker}_{self.year}_annual_report.pdf"


class AnnualReportManager:
    def __init__(
        self,
        company_index_path: Path | None = None,
        report_sources_path: Path | None = None,
        index_store: DocumentIndexStore | None = None,
    ):
        self.company_index_path = company_index_path or (settings.DATA_DIR / "company_index.json")
        self.report_sources_path = report_sources_path or (settings.DATA_DIR / "report_sources.json")
        self.company_index = json.loads(self.company_index_path.read_text(encoding="utf-8"))
        self.report_sources = (
            json.loads(self.report_sources_path.read_text(encoding="utf-8"))
            if self.report_sources_path.exists()
            else {}
        )
        self.index_store = index_store or DocumentIndexStore()

    def ensure_indexed_report(self, ticker: str, period: str | None = None) -> IndexedDocument | None:
        ref = self.resolve_report(ticker, period)
        if ref is None:
            return None
        try:
            pdf_path = self.ensure_pdf(ref)
        except Exception:
            company = self.company_index.get(ticker)
            found = (
                self._find_report_online(ticker, company["name"], ref.year)
                if company
                else None
            )
            if found is None:
                raise
            fallback_ref = ReportRef(
                ticker=ref.ticker,
                company_name=ref.company_name,
                year=ref.year,
                url=found[0],
                source=found[1],
            )
            pdf_path = self.ensure_pdf(fallback_ref)
        return self.index_store.ensure_pdf_index(
            pdf_path=pdf_path,
            ticker=ref.ticker,
            company_name=ref.company_name,
            document_id=ref.document_id,
        )

    def resolve_report(self, ticker: str, period: str | None = None) -> ReportRef | None:
        company = self.company_index.get(ticker)
        if not company:
            return None
        year = _year_from_period(period) or _latest_year(self.report_sources.get(ticker, {}))
        if year is None:
            year = 2024

        source = self._source_for(ticker, year)
        if source is not None:
            return ReportRef(
                ticker=ticker,
                company_name=company["name"],
                year=year,
                url=source["url"],
                source=source.get("source", "configured report source"),
            )

        found = self._find_report_online(ticker, company["name"], year)
        if found is None:
            return None
        return ReportRef(
            ticker=ticker,
            company_name=company["name"],
            year=year,
            url=found[0],
            source=found[1],
        )

    def ensure_pdf(self, ref: ReportRef) -> Path:
        settings.DEMO_FILINGS_DIR.mkdir(parents=True, exist_ok=True)
        path = settings.DEMO_FILINGS_DIR / ref.filename
        if path.exists() and path.stat().st_size > 10_000:
            return path
        self._download_pdf(ref.url, path)
        return path

    def _source_for(self, ticker: str, year: int) -> dict | None:
        ticker_sources = self.report_sources.get(ticker, {})
        reports = ticker_sources.get("reports", {})
        source = reports.get(str(year))
        if source:
            return source
        latest = ticker_sources.get("latest_year")
        if latest and str(latest) in reports:
            return reports[str(latest)]
        return None

    def _find_report_online(
        self,
        ticker: str,
        company_name: str,
        year: int,
    ) -> tuple[str, str] | None:
        queries = [
            f"{company_name} annual report {year} PDF",
            f"{ticker} Bursa Malaysia annual report {year} PDF",
            f"{company_name} financial statements {year} PDF",
        ]
        for query in queries:
            for url in _duckduckgo_result_urls(query):
                pdf_url = _best_pdf_from_url(url, company_name, year)
                if pdf_url:
                    return pdf_url, url
        return None

    def _download_pdf(self, url: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream(
            "GET",
            url,
            follow_redirects=True,
            timeout=90,
            headers=HTTP_HEADERS,
        ) as response:
            response.raise_for_status()
            with path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    if chunk:
                        handle.write(chunk)
        if path.stat().st_size < 10_000:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded report is too small: {url}")


def _year_from_period(period: str | None) -> int | None:
    if not period:
        return None
    match = re.search(r"(20\d{2})", period)
    return int(match.group(1)) if match else None


def _latest_year(source: dict) -> int | None:
    latest = source.get("latest_year")
    if latest:
        return int(latest)
    reports = source.get("reports", {})
    years = [int(year) for year in reports if str(year).isdigit()]
    return max(years) if years else None


def _duckduckgo_result_urls(query: str) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        response = httpx.get(url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
        response.raise_for_status()
    except Exception:
        return []
    tree = HTMLParser(response.text)
    urls = []
    for node in tree.css("a.result__a"):
        href = node.attributes.get("href")
        if not href:
            continue
        urls.append(_unwrap_duckduckgo_url(href))
    return urls


def _unwrap_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.query:
        match = re.search(r"(?:^|&)uddg=([^&]+)", parsed.query)
        if match:
            return unquote(match.group(1))
    return url


def _best_pdf_from_url(url: str, company_name: str, year: int) -> str | None:
    if _looks_like_pdf_url(url, company_name, year):
        return url
    try:
        response = httpx.get(url, follow_redirects=True, timeout=20, headers=HTTP_HEADERS)
        response.raise_for_status()
    except Exception:
        return None
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" in content_type:
        return str(response.url)
    tree = HTMLParser(response.text)
    candidates = []
    for node in tree.css("a"):
        href = node.attributes.get("href")
        text = node.text(separator=" ", strip=True)
        if not href:
            continue
        absolute = urljoin(str(response.url), href)
        haystack = f"{absolute} {text}".lower()
        if ".pdf" in haystack and str(year) in haystack and "annual" in haystack:
            score = _source_score(absolute, company_name)
            candidates.append((score, absolute))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _looks_like_pdf_url(url: str, company_name: str, year: int) -> bool:
    lowered = url.lower()
    if ".pdf" not in lowered or str(year) not in lowered:
        return False
    return "annual" in lowered or "integrated" in lowered or _source_score(url, company_name) > 0


def _source_score(url: str, company_name: str) -> int:
    host = urlparse(url).netloc.lower()
    company_tokens = [token for token in re.findall(r"[a-z]+", company_name.lower()) if len(token) > 2]
    score = sum(5 for token in company_tokens if token in host or token in url.lower())
    if "bursamalaysia" in host:
        score += 4
    if "annualreports" in host:
        score += 1
    return score
