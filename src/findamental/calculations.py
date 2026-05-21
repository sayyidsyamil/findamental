from dataclasses import dataclass
import re

from findamental.index.models import IndexedCell, IndexedDocument, IndexedRow


@dataclass(frozen=True)
class CalculationInput:
    label: str
    value: float
    unit: str
    page_number: int
    raw_text: str


@dataclass(frozen=True)
class CalculationResult:
    metric: str
    company_name: str
    ticker: str
    period: str
    scope: str
    value: float
    unit: str
    formula: str
    inputs: list[CalculationInput]
    source_pages: list[int]


class FinancialCalculator:
    def calculate(
        self,
        document: IndexedDocument,
        query_text: str,
        period: str | None,
    ) -> CalculationResult | None:
        metric = _detect_metric(query_text)
        if metric is None:
            return None
        resolved_period = _detect_period(query_text) or period or "FY_2025"
        scope = _detect_scope(query_text)
        try:
            return _calculate_metric(document, metric, resolved_period, scope)
        except ValueError:
            return None


def _calculate_metric(
    document: IndexedDocument,
    metric: str,
    period: str,
    scope: str,
) -> CalculationResult | None:
    formulas = {
        "revenue_growth": _revenue_growth,
        "asset_growth": _asset_growth,
        "net_profit_margin": _net_profit_margin,
        "operating_margin": _operating_margin,
        "debt_to_equity": _debt_to_equity,
        "equity_ratio": _equity_ratio,
        "loan_to_deposit": _loan_to_deposit,
        "pe_ratio": _pe_ratio,
        "pb_ratio": _pb_ratio,
        "dividend_yield": _dividend_yield,
        "dividend_payout": _dividend_payout,
    }
    return formulas[metric](document, period, scope)


def _revenue_growth(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    prior = _prior_period(period)
    current_revenue = _input(document, "Operating revenue", period, scope)
    prior_revenue = _input(document, "Operating revenue", prior, scope)
    if not current_revenue or not prior_revenue:
        return None
    value = (current_revenue.value - prior_revenue.value) / prior_revenue.value * 100
    return _result(
        document,
        "Revenue growth",
        period,
        scope,
        value,
        "%",
        "(Operating revenue current - Operating revenue prior) / Operating revenue prior",
        [current_revenue, prior_revenue],
    )


def _asset_growth(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    prior = _prior_period(period)
    current_assets = _input(document, "Total assets", period, scope)
    prior_assets = _input(document, "Total assets", prior, scope)
    if not current_assets or not prior_assets:
        return None
    value = (current_assets.value - prior_assets.value) / prior_assets.value * 100
    return _result(
        document,
        "Asset growth",
        period,
        scope,
        value,
        "%",
        "(Total assets current - Total assets prior) / Total assets prior",
        [current_assets, prior_assets],
    )


def _net_profit_margin(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    profit = _input(document, "Profit attributable to equity holders of the Bank", period, scope)
    revenue = _input(document, "Operating revenue", period, scope)
    if not profit or not revenue:
        return None
    value = profit.value / revenue.value * 100
    return _result(
        document,
        "Net profit margin",
        period,
        scope,
        value,
        "%",
        "Profit attributable to equity holders of the Bank / Operating revenue",
        [profit, revenue],
    )


def _operating_margin(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    operating_profit = _input(document, "Operating profit", period, scope)
    revenue = _input(document, "Operating revenue", period, scope)
    if not operating_profit or not revenue:
        return None
    value = operating_profit.value / revenue.value * 100
    return _result(
        document,
        "Operating margin",
        period,
        scope,
        value,
        "%",
        "Operating profit / Operating revenue",
        [operating_profit, revenue],
    )


def _debt_to_equity(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    liabilities = _input(document, "Total liabilities", period, scope)
    equity = _input(document, "Shareholders’ equity", period, scope)
    if not liabilities or not equity:
        return None
    value = liabilities.value / equity.value
    return _result(
        document,
        "Debt to equity",
        period,
        scope,
        value,
        "x",
        "Total liabilities / Shareholders' equity",
        [liabilities, equity],
    )


def _equity_ratio(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    equity = _input(document, "Shareholders’ equity", period, scope)
    assets = _input(document, "Total assets", period, scope)
    if not equity or not assets:
        return None
    value = equity.value / assets.value * 100
    return _result(
        document,
        "Equity ratio",
        period,
        scope,
        value,
        "%",
        "Shareholders' equity / Total assets",
        [equity, assets],
    )


def _loan_to_deposit(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    loans = _input(document, "Loans, advances and financing", period, scope)
    deposits = _input(document, "Deposits from customers", period, scope)
    if not loans or not deposits:
        return None
    value = loans.value / deposits.value * 100
    return _result(
        document,
        "Loan to deposit",
        period,
        scope,
        value,
        "%",
        "Loans, advances and financing / Deposits from customers",
        [loans, deposits],
    )


def _pe_ratio(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    share_price = _input(document, "Share price as at", period, "Group")
    eps = _input(document, "Basic earnings", period, "Group")
    if not share_price or not eps:
        return None
    value = share_price.value / (eps.value / 100)
    return _result(
        document,
        "Price to earnings",
        period,
        "Group",
        value,
        "x",
        "Share price / Basic EPS",
        [share_price, eps],
    )


def _pb_ratio(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    share_price = _input(document, "Share price as at", period, "Group")
    net_assets = _input(document, "Net assets (sen)", period, "Group")
    if not share_price or not net_assets:
        return None
    value = share_price.value / (net_assets.value / 100)
    return _result(
        document,
        "Price to book",
        period,
        "Group",
        value,
        "x",
        "Share price / Net assets per share",
        [share_price, net_assets],
    )


def _dividend_yield(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    dividend = _input(document, "Gross dividend", period, "Group")
    share_price = _input(document, "Share price as at", period, "Group")
    if not dividend or not share_price:
        return None
    value = (dividend.value / 100) / share_price.value * 100
    return _result(
        document,
        "Dividend yield",
        period,
        "Group",
        value,
        "%",
        "Gross dividend per share / Share price",
        [dividend, share_price],
    )


def _dividend_payout(document: IndexedDocument, period: str, scope: str) -> CalculationResult | None:
    dividend = _input(document, "Gross dividend", period, "Group")
    eps = _input(document, "Basic earnings", period, "Group")
    if not dividend or not eps:
        return None
    value = dividend.value / eps.value * 100
    return _result(
        document,
        "Dividend payout",
        period,
        "Group",
        value,
        "%",
        "Gross dividend / Basic EPS",
        [dividend, eps],
    )


def _input(
    document: IndexedDocument,
    label: str,
    period: str,
    scope: str,
) -> CalculationInput | None:
    for row in _candidate_rows(document, label):
        cell = _cell(row, period, scope)
        if cell and cell.value is not None:
            return CalculationInput(
                label=row.label,
                value=cell.value,
                unit=row.unit_hint or "",
                page_number=row.page_number,
                raw_text=cell.text,
            )
    return None


def _candidate_rows(document: IndexedDocument, label: str) -> list[IndexedRow]:
    wanted = _normalize(label)
    rows = [
        row
        for page in document.pages
        for row in page.rows
        if _normalize(row.label) == wanted
    ]
    return sorted(rows, key=lambda row: (row.page_number != 5, row.page_number))


def _cell(row: IndexedRow, period: str, scope: str) -> IndexedCell | None:
    cells = [
        cell
        for cell in row.cells
        if cell.column == period and cell.scope == scope and cell.value is not None
    ]
    if cells:
        return cells[0]
    if scope != "Group":
        return None
    fallback = [
        cell
        for cell in row.cells
        if cell.column == period and cell.value is not None
    ]
    return fallback[0] if fallback else None


def _result(
    document: IndexedDocument,
    metric: str,
    period: str,
    scope: str,
    value: float,
    unit: str,
    formula: str,
    inputs: list[CalculationInput],
) -> CalculationResult:
    return CalculationResult(
        metric=metric,
        company_name=document.company_name,
        ticker=document.ticker,
        period=period,
        scope=scope,
        value=value,
        unit=unit,
        formula=formula,
        inputs=inputs,
        source_pages=sorted({item.page_number for item in inputs}),
    )


def _detect_metric(query_text: str) -> str | None:
    text = query_text.lower()
    patterns = [
        ("revenue_growth", ["revenue growth", "sales growth", "growth in revenue"]),
        ("asset_growth", ["asset growth", "assets growth", "growth in assets"]),
        ("net_profit_margin", ["net profit margin", "profit margin", "net margin"]),
        ("operating_margin", ["operating margin"]),
        ("debt_to_equity", ["debt to equity", "liabilities to equity", "liability to equity"]),
        ("equity_ratio", ["equity ratio", "equity to assets", "shareholders equity to assets"]),
        ("loan_to_deposit", ["loan to deposit", "loans to deposits", "financing to deposits"]),
        ("pe_ratio", ["p/e", "pe ratio", "price to earnings", "price earnings", "valuation"]),
        ("pb_ratio", ["p/b", "pb ratio", "price to book"]),
        ("dividend_yield", ["dividend yield"]),
        ("dividend_payout", ["dividend payout", "payout ratio"]),
    ]
    for metric, phrases in patterns:
        if any(phrase in text for phrase in phrases):
            return metric
    if "calculate" not in text and "calc" not in text and "derive" not in text:
        return None
    if "revenue" in text and "growth" in text:
        return "revenue_growth"
    if "asset" in text and "growth" in text:
        return "asset_growth"
    if "margin" in text and "profit" in text:
        return "net_profit_margin"
    return None


def _detect_scope(query_text: str) -> str:
    text = query_text.lower()
    if re.search(r"\bbank\b", text):
        return "Bank"
    return "Group"


def _detect_period(query_text: str) -> str | None:
    match = re.search(r"\b(?:fy\s*)?(20\d{2})\b", query_text.lower())
    return f"FY_{match.group(1)}" if match else None


def _prior_period(period: str) -> str:
    match = re.fullmatch(r"FY_(20\d{2})", period)
    if not match:
        raise ValueError(f"Cannot derive prior period from {period}")
    return f"FY_{int(match.group(1)) - 1}"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
