---
name: findamental
description: Look up financial figures from Bursa Malaysia-listed company filings via natural language. Returns the figure, annotated source page, and optional chart or valuation.
version: 0.1.0
metadata:
  hermes:
    tags: [finance, ocr, document-extraction]
    category: research
---

# Findamental - Financial Statement Lookup Skill

## Target user

Finance students and retail investors in Malaysia who need to look up specific
figures from Bursa-listed company annual or quarterly reports without scrolling
through 200-page PDFs.

## Real-world problem

Bursa filings are long, layout-inconsistent PDFs. Existing AI tools either
hallucinate numbers without provenance, or require finance domain expertise to
navigate. Findamental returns verified figures with the exact source page
highlighted.

## Input format

Natural language query, e.g.
  - "Maybank Q3 2024 revenue"
  - "Tenaga net income last quarter"
  - "Show me Public Bank ROE trend"
  - "What's Hartalega P/E vs healthcare median"

## CV method

Primary: Docling + Granite-Docling-258M-MLX (IBM open-source vision-language
model, Apache 2.0, runs on Apple Silicon via MLX). Performs end-to-end document
understanding: layout analysis, OCR, table structure recognition, chart
extraction, all in a single 258M-parameter pass.

Preprocessing: PDF rasterised at 200 DPI via PyMuPDF.

Visual reasoning output: bounding box overlay on the matched row, page crop
saved as PNG.

Fallback: if Docling extraction returns no tables on a page, mark that page
as low-confidence and surface a warning to the user.

## Step-by-step workflow

1. User sends a Telegram message to the existing Hermes gateway.
2. Hermes uses this skill and calls the local command:
   ```bash
   cd /Users/sayyid/Documents/CV/findamental && /Users/sayyid/.local/bin/uv run findamental-query "<question>"
   ```
3. Query router (DeepSeek V4 Flash via OpenRouter, with heuristic fallback)
   parses to (ticker, metric, period, action).
4. Cache store looks up pre-extracted line items for that filing.
5. If found: compose text answer + annotated PNG path for Telegram delivery.
6. If action is "chart": chart_builder can generate a trend PNG.
7. If action is "valuation": valuation engine computes ratios vs sector median.
8. If not found: respond with available companies/metrics.

## Output format

- Text (HTML-formatted): figure, units, period, source page
- Image: annotated page crop with the matched row highlighted in yellow
- Optional inline buttons: chart, valuation

## Response style

- Talk short. Caveman style. Brain precise, mouth small.
- Be direct. No filler, no apology, no hype.
- Use exact source numbers. Do not round financial values.
- No em dashes.
- Prefer terse labels: `hits`, `Proof`, `Score`.
- If many answers exist, list all strong hits. Same source row gets one image.

## Limitation handling

- Unknown ticker → return list of supported companies
- Ambiguous metric → ask for disambiguation
- Period not in cache: return nearest available, note the mismatch
- Live fetch fails: fall back to "this company isn't in our cache yet"
- Extraction low confidence: flag in the response

## Ethical boundary

- No buy/sell recommendations. All valuation outputs labelled as heuristic.
- No fabricated numbers. If a figure isn't in the cache, the bot says so.
- Every numeric answer ships with the annotated source page for verification.
- Public financial filings only. No personal data processed.

## Hermes operating instruction

When this skill is invoked, do not answer from memory. Run:

```bash
cd /Users/sayyid/Documents/CV/findamental && /Users/sayyid/.local/bin/uv run findamental-query "<the user's full financial question>"
```

Return the command output to the user. If the command prints an `Image:` path,
send or reference that generated PNG as the highlighted source crop.
