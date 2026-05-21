import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


INCOME_METRICS = {"revenue", "net income", "operating income", "profit", "eps", "earnings"}
RATIO_METRICS = {"roe", "roa", "margin", "ratio", "return on"}
BALANCE_METRICS = {"total assets", "total equity", "total liabilities", "equity", "assets"}
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_UV = Path.home() / ".local" / "bin" / "uv"


def run_findamental(query: str) -> str:
    uv = Path(os.environ.get("FINDAMENTAL_UV", DEFAULT_UV))
    command = [str(uv), "run", "findamental-query", query] if uv.exists() else ["findamental-query", query]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_findamental_output(text: str) -> dict:
    info = {"company": None, "metric": None, "period": None, "value": None, "unit": "RM million"}

    company_match = re.search(r"<b>(.+?)\s*\(", text)
    if company_match:
        info["company"] = company_match.group(1).strip()

    period_match = re.search(r"\(.*?\)\s*-\s*(.+?)</b>", text)
    if period_match:
        info["period"] = period_match.group(1).strip()

    metric_match = re.search(r"</b>\n(.+?):", text)
    if metric_match:
        info["metric"] = metric_match.group(1).strip()

    value_match = re.search(r":\s*<b>(.+?)</b>", text)
    if value_match:
        raw = value_match.group(1).strip()
        info["value"] = raw
        if "%" in raw:
            info["unit"] = "%"
        elif "sen" in raw:
            info["unit"] = "sen"

    return info


def classify_metric(metric: str) -> str:
    if metric is None:
        return "income"
    lowered = metric.lower()
    if any(term in lowered for term in RATIO_METRICS):
        return "ratio"
    if any(term in lowered for term in BALANCE_METRICS):
        return "balance"
    return "income"


def build_suggestions(query: str, info: dict) -> list[dict]:
    metric = info.get("metric") or "metric"
    company = info.get("company") or ""
    category = classify_metric(metric)

    base_q = f'"{query}"'
    suggestions = []

    if category == "income":
        suggestions = [
            {
                "type": "bar",
                "desc": f"{metric} single-period bar",
                "args": f'--query {base_q} --type bar',
            },
            {
                "type": "line",
                "desc": f"{metric} trend across periods",
                "args": f'--query {base_q} --type line',
            },
            {
                "type": "grouped",
                "desc": f"{metric} vs Net Income side by side",
                "args": f'--query {base_q} --type grouped',
            },
            {
                "type": "waterfall",
                "desc": "Income waterfall: Revenue to Net Income breakdown",
                "args": (
                    f"--data '{{\"Revenue\": 0, \"Operating Expenses\": -0, \"Net Income\": 0}}' "
                    f"--type waterfall --title \"{company} Income Waterfall\""
                ),
            },
        ]
    elif category == "ratio":
        suggestions = [
            {
                "type": "bar",
                "desc": f"{metric} bar",
                "args": f'--query {base_q} --type bar',
            },
            {
                "type": "line",
                "desc": f"{metric} trend over time",
                "args": f'--query {base_q} --type line',
            },
            {
                "type": "pie",
                "desc": f"{metric} as part of a breakdown",
                "args": f'--query {base_q} --type pie',
            },
        ]
    else:
        suggestions = [
            {
                "type": "waterfall",
                "desc": "Balance sheet waterfall breakdown",
                "args": f'--query {base_q} --type waterfall',
            },
            {
                "type": "bar",
                "desc": f"{metric} single-period bar",
                "args": f'--query {base_q} --type bar',
            },
            {
                "type": "pie",
                "desc": f"{metric} composition breakdown",
                "args": f'--query {base_q} --type pie',
            },
        ]

    return suggestions


def main():
    parser = argparse.ArgumentParser(description="Suggest chart options for a financial query")
    parser.add_argument("--query", required=True, help="Natural language financial query")
    args = parser.parse_args()

    output = run_findamental(args.query)
    if not output:
        print("No data returned from findamental-query. Check the query or cache.")
        sys.exit(1)

    info = parse_findamental_output(output)

    company = info.get("company") or "Company"
    metric = info.get("metric") or "metric"
    period = info.get("period") or ""
    value = info.get("value") or "?"

    print(f"Available: {company} {metric} {period} - {value}\n")
    print("Suggested charts:")

    suggestions = build_suggestions(args.query, info)
    for i, s in enumerate(suggestions, start=1):
        print(f"{i}. {s['type']:<10} - {s['desc']}")
        print(f"             visualise.py {s['args']} --output data/chart.png")
        print()


if __name__ == "__main__":
    main()
