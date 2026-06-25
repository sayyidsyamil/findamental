import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

years = ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
values = [10700, 11741, 12291, 13465, 14060]

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(years, values, marker="o", linewidth=2.5, color="#2563eb", markersize=8)

for x, y in zip(years, values):
    ax.text(x, y + 250, f"{y:,.0f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

ax.set_ylabel("RM million", fontsize=12)
ax.set_title("Maybank Group — Net Operating Profit FY2021–FY2025", fontsize=14, fontweight="bold", pad=20)
ax.tick_params(axis="x", rotation=0)
ax.set_ylim(0, max(values) * 1.15)
ax.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("/home/amaniskandar04/projects/findamental/data/opprofit_line.png", dpi=150)
plt.close()
print("OK")
