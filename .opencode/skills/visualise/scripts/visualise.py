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


def visualise(
    data: dict[str, float],
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

    labels = list(data.keys())
    values = list(data.values())
    colors = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#0891b2"]

    fig, ax = plt.subplots(figsize=(10, 5))

    if chart_type == "bar":
        bars = ax.bar(labels, values, color=colors[:len(labels)])
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"RM {val:,.0f}",
                ha="center", va="bottom", fontsize=9, rotation=45,
            )
    elif chart_type == "line":
        ax.plot(labels, values, marker="o", linewidth=2, color="#2563eb")
        for x, y in zip(labels, values):
            ax.text(x, y, f"RM {y:,.0f}", ha="center", va="bottom", fontsize=9)
    elif chart_type == "pie":
        fig, ax = plt.subplots(figsize=(8, 8))
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%.1f%%",
            colors=colors[:len(labels)], startangle=90,
        )
        for t in autotexts:
            t.set_fontsize(9)
    else:
        print(f"Unknown chart type: {chart_type}. Use bar, line, or pie.")
        sys.exit(1)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    if chart_type != "pie":
        ax.set_ylabel("RM (thousands)")
        ax.tick_params(axis="x", rotation=35)

    plt.tight_layout()
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=150)
    print(f"Chart saved: {output}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visualise financial data")
    parser.add_argument("file", nargs="?", help="JSON or text file with data")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--type", default="bar", choices=["bar", "line", "pie"], help="Chart type")
    parser.add_argument("--title", default="Financial Data", help="Chart title")
    parser.add_argument("--output", default="data/chart.png", help="Output path")

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

    visualise(data, args.type, args.title, args.output)
