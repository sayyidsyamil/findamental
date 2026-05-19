---
name: find
description: Search and extract specific data points from markdown-converted financial documents
---

## What I do

- Search markdown files (converted from PDFs via `data/convert.py`) for specific financial data points
- Extract structured data using regex patterns and section-aware searching
- Return clean key-value pairs or table data for downstream analysis

## When to use me

Use this skill when you have a markdown-converted document (annual report, financial statement, etc.) and need to extract specific figures — e.g. "how much tax did they pay?", "what was revenue in 2024?", "find the zakat figure".

## Strategy

Use Grep tool with targeted patterns to locate sections of interest. Since financial documents use consistent numbering (e.g. "47. TAXATION AND ZAKAT") and labelled tables, start broad then narrow in:

1. **Find the section** — e.g. `(?i)taxation.*zakat` or `(?i)47\.\s*TAXATION`
2. **Read around the match** — use Read with offset/limit to get table context (~60 lines)
3. **Parse the table** — markitdown output preserves table structure with columns for year pairs (2025/2024) and entity pairs (Group/Bank). Look for RM'000 headers to locate the correct column block.

## Example workflow

```
grep  →  "TAXATION AND ZAKAT"       # locate section
read  →  line N, limit 80           # capture table with headers
grep  →  "Zakat" near that section   # extract specific line item
```

## Output format

Key-value pairs with line numbers and surrounding context so the caller can verify accuracy. Always include the unit (RM'000 unless otherwise noted).
