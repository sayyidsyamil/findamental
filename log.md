# Findamental Log

## 2026-05-21

- Built the Findamental repo inside `/Users/sayyid/Documents/CV/findamental`.
- Wired Hermes Telegram to the local Findamental skill.
- Added allowed Telegram users `1018271548`, `1112081098`, and `6362756699`.
- Indexed the real Maybank FY2025 financial statements PDF.
- Added document-pack output:
  - `report.txt`
  - `report.md`
  - `tables.json`
  - `layout.json`
- Improved lookup so a query can return multiple matching rows across pages.
- Added exact-value response style. No rounding.
- Added source screenshots with highlighted rows.
- Added calculated metrics:
  - revenue growth
  - asset growth
  - net profit margin
  - operating margin
  - debt to equity
  - equity ratio
  - loan to deposit
  - price to earnings
  - price to book
  - dividend yield
  - dividend payout
- Added visualisation scripts for bar, line, pie, grouped, and waterfall charts.
- Fixed visualisation so it runs through the project `uv` environment instead
  of depending on shell PATH.
- Fixed chart number parsing for values like `12.03x`, `11.7%`, and `87.1 sen`.
- Added the clean `/findamental` Hermes quick command runner.
- Turned off Telegram tool progress clutter for the local Hermes gateway.
- Set Hermes approvals to `mode: "off"` for smoother Telegram use.
- Added missing-report workflow to the skill:
  - browse for official annual report PDF
  - download into `data/demo_filings/`
  - run OCR/indexing
  - re-run the original query
  - answer only with verified source-backed results

## Current Limits

- The clean `/findamental` quick command is fast and quiet, but it cannot browse.
- Missing annual report ingest requires full Hermes skill mode because browsing
  and downloading need the agent tool loop.
- Generic non-Maybank annual report extraction may need manual tuning if the PDF
  layout is unusual or OCR quality is poor.
