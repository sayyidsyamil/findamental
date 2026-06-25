import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

years = ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
values = [45959, 49416, 63515, 68943, 66369]
colors = ["#2563eb", "#2563eb", "#2563eb", "#2563eb", "#2563eb"]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(years, values, color=colors)

for bar, val in zip(bars, values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 800,
        f"{val:,.0f}",
        ha="center", va="bottom", fontsize=10, fontweight="bold",
    )

ax.set_ylabel("RM million", fontsize=12)
ax.set_title("Maybank Group — Operating Revenue FY2021–FY2025", fontsize=14, fontweight="bold", pad=20)
ax.tick_params(axis="x", rotation=0)
ax.set_ylim(0, max(values) * 1.15)

plt.tight_layout()
plt.savefig("/home/amaniskandar04/projects/findamental/data/revenue_bar_fixed.png", dpi=150)
plt.close()
print("OK")
