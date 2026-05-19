---
name: visualise
description: Generate charts and plots from financial data extracted via find/analyse
---

## What I do

- Take structured numeric data and render it as charts (bar, line, pie, waterfall)
- Save output as PNG files in the `data/` directory
- Support multi-series and year-over-year comparisons

## When to use me

Use this skill when you want to visualise financial trends, comparisons, or breakdowns from document data. Works best after `find` and `analyse` have extracted and structured the numbers.

## Usage

```bash
python .opencode/skills/visualise/scripts/visualise.py <json-data-file> [--type bar|line|pie] [--title "..."] [--output filename.png]
```

Example:
```bash
python .opencode/skills/visualise/scripts/visualise.py \
  --data '{"Taxation 2024": 3095704, "Taxation 2025": 3391161, "Zakat 2024": 99475, "Zakat 2025": 111285}' \
  --type bar --title "Maybank Taxation & Zakat" --output data/tax-viz.png
```

Or pipe from analyse:
```bash
python .opencode/skills/analyse/scripts/analyse.py ... | \
  python .opencode/skills/visualise/scripts/visualise.py --stdin --type bar
```

## Output

Saves a PNG chart to the specified path and prints the file location.
