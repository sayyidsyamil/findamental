from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


class ChartBuilder:
    def trend_bar_chart(
        self,
        title: str,
        labels: list[str],
        values: list[float],
        unit: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(labels, values, color="#1f77b4")
        ax.set_title(title)
        ax.set_ylabel(unit)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return output_path

    def peer_comparison_chart(
        self,
        title: str,
        company_value: float,
        sector_median: float,
        metric_name: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(["Company", "Sector median"], [company_value, sector_median], color=["#2ca02c", "#7f7f7f"])
        ax.set_title(title)
        ax.set_ylabel(metric_name)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return output_path
