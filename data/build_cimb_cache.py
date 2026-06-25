#!/usr/bin/env python3
"""Build CIMB cache entry from manually extracted 5-year summary data."""
import json
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path("/home/amaniskandar04/projects/findamental/data/extracted_cache")
DATA_DIR = Path("/home/amaniskandar04/projects/findamental/data")

# Data from page 7 (5-Year Group Financial Summary) of CIMB Financial Statements 2025
# All amounts in RM'000 unless otherwise noted

YEARS = ["FY_2021", "FY_2022", "FY_2023", "FY_2024", "FY_2025"]

line_items = []

# Net income (operating revenue equivalent for banks)
net_income_values = {
    "FY_2021": 19512940,
    "FY_2022": 19837516,
    "FY_2023": 21014482,
    "FY_2024": 22301154,
    "FY_2025": 22467412,
}

# Net profit for the financial year (profit attributable to owners)
net_profit_values = {
    "FY_2021": 4295334,
    "FY_2022": 5439863,
    "FY_2023": 6980962,
    "FY_2024": 7728049,
    "FY_2025": 7859552,
}

# Profit before taxation and zakat (operating profit / PBT)
pbt_values = {
    "FY_2021": 5789478,
    "FY_2022": 8371010,
    "FY_2023": 9540731,
    "FY_2024": 10395928,
    "FY_2025": 10680036,
}

# Profit before expected credit losses
profit_before_ecl_values = {
    "FY_2021": 10093991,
    "FY_2022": 10492009,
    "FY_2023": 11149406,
    "FY_2024": 11880923,
    "FY_2025": 11840496,
}

# Overheads (operating expenses)
overheads_values = {
    "FY_2021": 9418949,
    "FY_2022": 9345507,
    "FY_2023": 9865076,
    "FY_2024": 10420231,
    "FY_2025": 10626916,
}

# Total assets
total_assets_values = {
    "FY_2021": 621907058,
    "FY_2022": 666721225,
    "FY_2023": 733572152,
    "FY_2024": 755130703,
    "FY_2025": 778724390,
}

# Shareholders' funds (total equity)
total_equity_values = {
    "FY_2021": 58863263,
    "FY_2022": 62491206,
    "FY_2023": 68326961,
    "FY_2024": 69243796,
    "FY_2025": 70361115,
}

# Gross loans, advances and financing
gross_loans_values = {
    "FY_2021": 378032634,
    "FY_2022": 407057108,
    "FY_2023": 440921867,
    "FY_2024": 452273887,
    "FY_2025": 452947176,
}

# Deposits from customers
deposits_values = {
    "FY_2021": 440404971,
    "FY_2022": 460567161,
    "FY_2023": 497660583,
    "FY_2024": 512262558,
    "FY_2025": 524428773,
}

# Total liabilities
total_liabilities_values = {
    "FY_2021": 561798310,
    "FY_2022": 602937372,
    "FY_2023": 663733261,
    "FY_2024": 684291813,
    "FY_2025": 706816624,
}

# EPS basic (sen)
eps_values = {
    "FY_2021": 42.9,
    "FY_2022": 52.2,
    "FY_2023": 65.5,
    "FY_2024": 72.3,
    "FY_2025": 73.1,
}

# Dividend per share (sen)
dps_values = {
    "FY_2021": 23.0,
    "FY_2022": 26.0,
    "FY_2023": 43.0,
    "FY_2024": 47.0,
    "FY_2025": 47.1,
}

# Return on average equity (%)
roe_values = {
    "FY_2021": 7.5,
    "FY_2022": 9.0,
    "FY_2023": 10.7,
    "FY_2024": 11.2,
    "FY_2025": 11.3,
}

# Return on average total assets (%)
roa_values = {
    "FY_2021": 0.70,
    "FY_2022": 0.84,
    "FY_2023": 1.00,
    "FY_2024": 1.04,
    "FY_2025": 1.02,
}

# Net interest margin (%)
nim_values = {
    "FY_2021": 2.45,
    "FY_2022": 2.51,
    "FY_2023": 2.22,
    "FY_2024": 2.21,
    "FY_2025": 2.13,
}

# Cost to income ratio (%)
cti_values = {
    "FY_2021": 48.3,
    "FY_2022": 47.1,
    "FY_2023": 46.9,
    "FY_2024": 46.7,
    "FY_2025": 47.3,
}

# Total capital ratio (%)
total_capital_ratio_values = {
    "FY_2021": 18.4,
    "FY_2022": 18.9,
    "FY_2023": 18.9,
    "FY_2024": 18.8,
    "FY_2025": 18.6,
}

def make_items(data_dict, canonical_name, raw_label, source_page=7, unit="MYR"):
    items = []
    for period, value in data_dict.items():
        items.append({
            "name": canonical_name,
            "raw_label": raw_label,
            "value": value,
            "unit": unit,
            "period": period,
            "source_page": source_page,
            "source_bbox": [0.0, 0.0, 0.0, 0.0],
            "row_bbox": None,
            "annotated_image_path": "",
            "confidence": 1.0,
        })
    return items

ticker = "1023"
company_name = "CIMB Group Holdings Berhad"
filing_type = "FY_2025_FINANCIAL_STATEMENTS"

all_items = []
all_items.extend(make_items(net_income_values, "net_income", "Net income"))
all_items.extend(make_items(net_profit_values, "profit_attributable", "Net profit for the financial year"))
all_items.extend(make_items(pbt_values, "operating_income", "Profit before taxation and zakat"))
all_items.extend(make_items(profit_before_ecl_values, "profit_before_ecl", "Profit before expected credit losses"))
all_items.extend(make_items(overheads_values, "operating_expense", "Overheads"))
all_items.extend(make_items(total_assets_values, "total_assets", "Total assets"))
all_items.extend(make_items(total_equity_values, "shareholders_funds", "Shareholders' funds"))
all_items.extend(make_items(gross_loans_values, "gross_loans", "Gross loans, advances and financing"))
all_items.extend(make_items(deposits_values, "deposits", "Deposits from customers"))
all_items.extend(make_items(total_liabilities_values, "total_liabilities", "Total liabilities"))
all_items.extend(make_items(eps_values, "eps", "Earnings per share (basic)", unit="sen"))
all_items.extend(make_items(dps_values, "dividend_per_share", "Dividend per share", unit="sen"))
all_items.extend(make_items(roe_values, "roe", "Return on average equity", unit="percent"))
all_items.extend(make_items(roa_values, "roa", "Return on average total assets", unit="percent"))
all_items.extend(make_items(nim_values, "nim", "Net interest margin", unit="percent"))
all_items.extend(make_items(cti_values, "cost_to_income_ratio", "Cost to income ratio", unit="percent"))
all_items.extend(make_items(total_capital_ratio_values, "total_capital_ratio", "Total capital ratio", unit="percent"))

filing = {
    "ticker": ticker,
    "company_name": company_name,
    "filing_type": filing_type,
    "source_pdf_path": str(Path("data/demo_filings/cimb_2025_financial_statements.pdf").resolve()),
    "extracted_at": datetime.utcnow().isoformat(),
    "extraction_model": "manual_5year_summary",
    "line_items": all_items,
}

# Save
cache_path = CACHE_DIR / f"{ticker}_{filing_type}.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
cache_path.write_text(json.dumps(filing, indent=2), encoding="utf-8")
print(f"Saved: {cache_path}")
print(f"Line items: {len(all_items)}")
