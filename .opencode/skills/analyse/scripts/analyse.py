import json
import re
import sys
from pathlib import Path


def parse_number(s: str) -> float:
    s = s.strip().replace(",", "").replace("(", "-").replace(")", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_key_values(text: str) -> dict[str, float]:
    data = {}
    for line in text.splitlines():
        parts = re.split(r"[:=]\s*", line.strip(), maxsplit=1)
        if len(parts) == 2:
            key, val = parts
            num = parse_number(val)
            if num != 0.0 or val.strip().replace(",", "").replace("-", "").isdigit():
                data[key.strip()] = num
    return data


def compute_yoy(data: dict[str, float]) -> list[dict]:
    results = []
    for key in sorted(data):
        results.append({"label": key, "value": data[key]})
    return results


def compute_etr(tax: float, profit: float) -> float:
    return (tax / profit * 100) if profit else 0.0


def analyse(data: dict[str, float], metric: str | None = None):
    print("── Analysis Summary ─────────────────────")
    for key, val in sorted(data.items()):
        print(f"  {key}: RM {val:,.0f}")

    # Try to detect YoY pairs
    yoy_pairs = {}
    for key in data:
        base = re.sub(r"\s*\d{4}$", "", key).strip()
        year_match = re.search(r"(\d{4})$", key)
        if year_match:
            yoy_pairs.setdefault(base, {})[year_match.group(1)] = data[key]

    for label, years in yoy_pairs.items():
        if len(years) >= 2:
            sorted_years = sorted(years)
            old, new = years[sorted_years[0]], years[sorted_years[1]]
            change = ((new - old) / old) * 100
            print(f"\n  📈 {label}: {change:+.1f}% YoY (RM {old:,.0f} → RM {new:,.0f})")

    if metric == "etr":
        for key, val in data.items():
            if "profit" in key.lower():
                tax_key = [k for k in data if "tax" in k.lower()]
                if tax_key:
                    tax_val = data[tax_key[0]]
                    print(f"\n  Effective Tax Rate: {compute_etr(tax_val, val):.1f}%")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyse financial data")
    parser.add_argument("file", nargs="?", help="JSON or text file with data")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--metric", choices=["yoy", "etr", "margin", "share"], help="Analysis metric")

    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.file:
        text = Path(args.file).read_text()
    else:
        print("Provide a file or use --stdin")
        sys.exit(1)

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = parse_key_values(text)

    analyse(data, args.metric)
