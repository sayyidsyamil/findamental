import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_UV = Path.home() / ".local" / "bin" / "uv"


def parse_number(s: str) -> float:
    s = re.sub(r"<[^>]+>", "", s)
    s = (
        s.strip()
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .replace("RM", "")
        .replace("million", "")
        .replace("sen", "")
        .replace("%", "")
        .replace("x", "")
        .strip()
    )
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


def fetch_from_findamental(query: str) -> dict[str, float]:
    uv = Path(os.environ.get("FINDAMENTAL_UV", DEFAULT_UV))
    command = [str(uv), "run", "findamental-query", query] if uv.exists() else ["findamental-query", query]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if not output:
        print("No data returned from findamental-query. Check the query or cache.")
        sys.exit(1)

    value_match = re.search(r":\s*<b>(.+?)</b>", output)
    metric_match = re.search(r"</b>\n(.+?):", output)
    period_match = re.search(r"\(.*?\)\s*-\s*(.+?)</b>", output)

    label = "Value"
    if metric_match:
        label = metric_match.group(1).strip()
    if period_match:
        label = f"{label} ({period_match.group(1).strip()})"

    if value_match:
        raw = value_match.group(1).strip()
        num = parse_number(raw)
        return {label: num}

    return parse_key_values(output)


def infer_unit(data: dict) -> str:
    keys = " ".join(data.keys()).lower()
    if any(t in keys for t in ["%", "ratio", "roe", "roa", "margin", "return on"]):
        return "%"
    if any(t in keys for t in ["eps", "sen", "per share"]):
        return "sen"
    return "RM million"


def chart_bar(ax, labels, values, colors, unit):
    bars = ax.bar(labels, values, color=colors[:len(labels)])
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.01,
            f"{val:,.1f}",
            ha="center", va="bottom", fontsize=9,
        )
    ax.set_ylabel(unit)
    ax.tick_params(axis="x", rotation=35)


def chart_line(ax, labels, values, unit):
    ax.plot(labels, values, marker="o", linewidth=2, color="#2563eb")
    for x, y in zip(labels, values):
        ax.text(x, y + max(values) * 0.01, f"{y:,.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel(unit)
    ax.tick_params(axis="x", rotation=35)


def chart_pie(fig, ax, labels, values, colors):
    fig.set_size_inches(8, 8)
    _, _, autotexts = ax.pie(
        values, labels=labels, autopct="%.1f%%",
        colors=colors[:len(labels)], startangle=90,
    )
    for t in autotexts:
        t.set_fontsize(9)


def chart_grouped(ax, data: dict, colors, unit):
    import numpy as np

    periods = list(data.keys())
    metrics = list(next(iter(data.values())).keys())
    x = np.arange(len(periods))
    width = 0.8 / len(metrics)

    for i, metric in enumerate(metrics):
        vals = [data[p].get(metric, 0) for p in periods]
        offset = (i - len(metrics) / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=metric, color=colors[i % len(colors)])
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(max(v.values()) for v in data.values()) * 0.01,
                f"{val:,.1f}",
                ha="center", va="bottom", fontsize=8,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(periods, rotation=35)
    ax.set_ylabel(unit)
    ax.legend()


def chart_waterfall(ax, data: dict[str, float], unit):
    labels = list(data.keys())
    values = list(data.values())
    running = 0.0
    bottoms = []
    bar_colors = []

    for val in values:
        bottoms.append(running if val >= 0 else running + val)
        bar_colors.append("#059669" if val >= 0 else "#dc2626")
        running += val

    bar_colors[-1] = "#2563eb"
    bottoms[-1] = 0
    values[-1] = running

    bars = ax.bar(labels, [abs(v) for v in values], bottom=bottoms, color=bar_colors)
    for bar, val, bottom in zip(bars, values, bottoms):
        y = bottom + abs(val) + max(abs(v) for v in values) * 0.01
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{val:,.1f}", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel(unit)
    ax.tick_params(axis="x", rotation=35)
    ax.axhline(0, color="black", linewidth=0.8)


def visualise(
    data,
    chart_type: str = "bar",
    title: str = "Financial Data",
    output: str = "data/chart.png",
):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib")
        sys.exit(1)

    colors = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#0891b2"]

    if chart_type == "grouped":
        if not isinstance(data, dict) or not isinstance(next(iter(data.values()), None), dict):
            print("grouped chart requires nested JSON: {\"Period\": {\"Metric\": value}}")
            sys.exit(1)
        flat = {k: v for period in data.values() for k, v in period.items()}
        unit = infer_unit(flat)
        fig, ax = plt.subplots(figsize=(10, 5))
        chart_grouped(ax, data, colors, unit)
    else:
        if not isinstance(data, dict) or isinstance(next(iter(data.values()), None), dict):
            print(f"{chart_type} chart requires flat JSON: {{\"Label\": value}}")
            sys.exit(1)
        unit = infer_unit(data)
        labels = list(data.keys())
        values = list(data.values())

        if chart_type == "pie":
            fig, ax = plt.subplots(figsize=(8, 8))
            chart_pie(fig, ax, labels, values, colors)
        elif chart_type == "waterfall":
            fig, ax = plt.subplots(figsize=(10, 5))
            chart_waterfall(ax, data, unit)
        elif chart_type == "line":
            fig, ax = plt.subplots(figsize=(10, 5))
            chart_line(ax, labels, values, unit)
        elif chart_type == "bar":
            fig, ax = plt.subplots(figsize=(10, 5))
            chart_bar(ax, labels, values, colors, unit)
        else:
            print(f"Unknown chart type: {chart_type}. Use bar, line, pie, grouped, or waterfall.")
            sys.exit(1)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"Chart saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualise financial data as a chart")
    parser.add_argument("file", nargs="?", help="JSON or text file with data")
    parser.add_argument("--query", help="Natural language query (calls findamental-query)")
    parser.add_argument("--data", help="Inline JSON string with chart data")
    parser.add_argument("--stdin", action="store_true", help="Read data from stdin")
    parser.add_argument(
        "--type", default="bar",
        choices=["bar", "line", "pie", "grouped", "waterfall"],
        help="Chart type",
    )
    parser.add_argument("--title", default=None, help="Chart title")
    parser.add_argument("--output", default="data/chart.png", help="Output PNG path")
    args = parser.parse_args()

    if args.query:
        data = fetch_from_findamental(args.query)
        title = args.title or args.query.title()
    elif args.data:
        data = json.loads(args.data)
        title = args.title or "Financial Data"
    elif args.stdin:
        text = sys.stdin.read()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = parse_key_values(text)
        title = args.title or "Financial Data"
    elif args.file:
        text = Path(args.file).read_text()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = parse_key_values(text)
        title = args.title or Path(args.file).stem.replace("_", " ").title()
    else:
        print("Provide --query, --data, --stdin, or a file path.")
        sys.exit(1)

    visualise(data, args.type, title, args.output)
