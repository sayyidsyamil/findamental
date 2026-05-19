---
description: Search and extract specific data points from markdown-converted financial documents
agent: explore
---

You have a markdown document in the `data/` directory (converted from PDF via `data/convert.py`).

The user wants to find a specific figure or data point (e.g. "how much tax did they pay in 2024?").

Use grep to locate the relevant section heading — financial documents use numbered sections like "47. TAXATION AND ZAKAT". Then read ~60 lines around the match to capture the full table with headers.

Columns are typically year-pairs (2025/2024) and entity-pairs (Group/Bank), with values in RM'000.

Return the extracted figures as clean key-value pairs with the line numbers so the user can verify.
