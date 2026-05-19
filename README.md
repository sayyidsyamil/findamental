# findamental

**Find** + **Analyse** + **Visualise** financial data from annual reports.

---

## What is this?

You have a PDF annual report. This project turns it into markdown, then lets you ask questions like:

- "How much tax did they pay in 2024?"
- "What is the revenue trend?"
- "Show me a chart of profit vs tax"

All from your phone via Telegram.

---

## How to use

### 1. Convert a PDF report

Put your PDF in `data/` and run:

```
python data/convert.py data/your-report.pdf
```

This creates `data/your-report.md`.

### 2. Find numbers

```
opencode run "find maybank revenue 2024"
```

Or in Telegram: `/find maybank revenue 2024`

### 3. Analyse trends

```
opencode run "analyse revenue and profit 2024 vs 2025"
```

### 4. Visualise

```
opencode run "visualise revenue as bar chart"
```

### 5. From Telegram

Install the bot (see below), then send any command above as a message.

---

## Skills

| Skill     | What it does                                      |
|-----------|---------------------------------------------------|
| `find`    | Search markdown reports for specific numbers      |
| `analyse` | Compute YoY changes, ratios, tax rates            |
| `visualise` | Draw bar/line/pie charts, save as PNG            |
| `summarise` | Summarise long documents into bullet points      |

---

## Telegram Bot Setup

1. Start the OpenCode server:
   ```
   opencode serve
   ```
2. Install and run the bot:
   ```
   npx @grinev/opencode-telegram-bot@latest
   ```
3. Follow the setup wizard (bot token + your user ID).
4. Open Telegram and message your bot. Send `/commands` to see available skills.

---

## Project structure

```
data/              -- PDFs converted to markdown
.opencode/skills/  -- find, analyse, visualise, summarise
.opencode/commands/ -- command definitions
```

---

## What's included

- Maybank Annual Report 2025 (FY ending Dec 2025, with 2024 comparatives) already converted as an example
- Skills for searching, analysing, and charting financial data
- Telegram bot integration ready
