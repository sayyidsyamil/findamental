from pathlib import Path

from findamental.output.chart_builder import ChartBuilder


def demo_chart(output_path: str = "data/extracted_cache/demo_chart.png") -> Path:
    return ChartBuilder().trend_bar_chart(
        "Demo Revenue Trend",
        ["2022", "2023", "2024"],
        [100.0, 112.0, 125.0],
        "RM million",
        Path(output_path),
    )
