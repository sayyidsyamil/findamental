---
name: analyse
description: Analyse financial data extracted from markdown documents — compute trends, ratios, and summaries
---

## What I do

- Take structured financial data (numbers, tables) from the `find` skill or directly from markdown
- Compute period-over-period changes, percentages, totals, and financial ratios
- Produce a concise analysis summary

## When to use me

Use this skill after extracting data with `find` to understand what the numbers mean — year-on-year changes, effective tax rates, profit breakdowns, or any comparative analysis.

## Usage

```bash
python .opencode/skills/analyse/scripts/analyse.py <data-file-or-json> [--metric <name>]
```

Or pipe from find:

```bash
python .opencode/skills/find/scripts/extract.py data/maybank-ar2025.md "TAXATION AND ZAKAT" --table | \
  python .opencode/skills/analyse/scripts/analyse.py --stdin
```

## Input format

The script accepts:
1. A JSON file with labelled numeric values (e.g. `{"revenue_2024": 1000, "revenue_2025": 1200}`)
2. A text file with key-value pairs (e.g. `Taxation 2024: 3,095,704`)
3. Piped data via `--stdin`

## Output format

```
— Analysis Summary —
Revenue: RM 1,200M (+20.0% YoY)
Taxation: RM 3,096M (effective rate: 22.6%)
Zakat: RM 99M
Total tax & zakat: RM 3,195M
```

## Metrics supported

- YoY change (`--metric yoy`)
- Effective tax rate (`--metric etr`)
- Profit margin (`--metric margin`)
- Share of total (`--metric share`)
