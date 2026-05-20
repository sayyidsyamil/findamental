---
description: Analyse financial data — compute YoY changes, effective tax rates, trends, and summaries
---

The user has structured financial data (key-value pairs from a `find` command, a JSON file, or text) and wants analysis.

Run the analyse script at `.opencode/skills/analyse/scripts/analyse.py` on the data file.

If the data is inline, save it as a JSON file in `data/` first, then run the script.

The script supports `--metric yoy` (year-over-year change) and `--metric etr` (effective tax rate).

Return the output as formatted text to the user. If the data came from a `/find` result, include the source context.
