# Findamental

Findamental is a Hermes skill for asking questions about Bursa Malaysia
financial statements from Telegram.

Current tested report:

```text
maybank-ar2025-financial-statements.pdf
```

Example Telegram message:

```text
/findamental Maybank FY 2025 revenue
```

Example answer:

```text
14 hits.

1. Malayan Banking Berhad (1155) - Group FY_2025
Operating revenue: RM 66,369 million
Proof: FY 2025 FINANCIAL STATEMENTS, page 5 | Score: 100%
```

Findamental also returns a highlighted screenshot of the source row.

## What You Are Setting Up

Full flow:

```text
Telegram message
-> Hermes Telegram gateway
-> Findamental Hermes skill
-> local PDF index
-> answer + highlighted source image
```

Findamental does not guess numbers. It reads the PDF index and gives page proof.

## Requirements

- Python 3.12
- Git
- `uv`
- Hermes Agent
- Telegram account
- Telegram bot token from BotFather
- OpenRouter API key if your Hermes model uses OpenRouter

Windows note: WSL2 is the safer path. Native Windows Hermes works, but is still
early beta.

## Step 1: Install Hermes

macOS, Linux, or WSL2:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Reload your shell:

```bash
source ~/.zshrc
```

or:

```bash
source ~/.bashrc
```

Windows native PowerShell:

```powershell
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

Check Hermes works:

```bash
hermes --version
hermes doctor
```

## Step 2: Configure Hermes Model

Run:

```bash
hermes setup
```

or only model setup:

```bash
hermes model
```

Use your normal provider. For this project we used OpenRouter with:

```text
deepseek/deepseek-v4-flash
```

If using OpenRouter, set this in Hermes when prompted:

```text
OPENROUTER_API_KEY=your_key_here
```

Do not paste real API keys into Git.

## Step 3: Create Telegram Bot

1. Open Telegram.
2. Search for `@BotFather`.
3. Send:

```text
/newbot
```

4. Pick a bot name.
5. Pick a username ending in `bot`.
6. Copy the API token.

Token format looks like:

```text
123456789:ABCdef_your_token_here
```

Keep it secret. If leaked, go to BotFather and revoke it.

## Step 4: Get Your Telegram User ID

Use one of these:

- Message `@userinfobot`
- Message `@RawDataBot`

Copy your numeric Telegram user ID.

Example:

```text
1018271548
```

## Step 5: Configure Hermes Telegram Gateway

Run:

```bash
hermes gateway setup
```

Choose Telegram.

When prompted, enter:

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=your_telegram_user_id
```

Manual fallback:

```bash
nano ~/.hermes/.env
```

Add:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=your_telegram_user_id
```

Windows native Hermes usually stores this under:

```text
%LOCALAPPDATA%\hermes\.env
```

## Step 6: Install Findamental

Clone or open this project folder.

macOS or WSL2:

```bash
cd /Users/sayyid/Documents/CV/findamental
make install
```

Generic macOS/Linux path:

```bash
cd /path/to/findamental
uv venv --python 3.12
uv pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
cd path\to\findamental
uv venv --python 3.12
uv pip install -e ".[dev]"
```

If `uv` is missing:

macOS:

```bash
brew install uv
```

Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Step 7: Add The Maybank PDF

Make sure this file is in the Findamental project root:

```text
maybank-ar2025-financial-statements.pdf
```

Project root means same folder as:

```text
pyproject.toml
README.md
Makefile
```

## Step 8: Build The PDF Index

macOS or WSL2:

```bash
cd /path/to/findamental
make extract
```

Windows:

```powershell
cd path\to\findamental
uv run python scripts/extract_all_demo_filings.py
```

This creates:

```text
data/document_index/
data/document_pack/
data/extracted_cache/
```

Main useful files:

```text
data/document_pack/1155_FY_2025_FINANCIAL_STATEMENTS/report.txt
data/document_pack/1155_FY_2025_FINANCIAL_STATEMENTS/tables.json
data/document_pack/1155_FY_2025_FINANCIAL_STATEMENTS/layout.json
```

## Step 9: Test Findamental Locally

Run this before Telegram. If local fails, Telegram will fail too.

macOS or WSL2:

```bash
cd /path/to/findamental
uv run findamental-query "Maybank 2025 ROE"
```

Windows:

```powershell
cd path\to\findamental
uv run findamental-query "Maybank 2025 ROE"
```

Expected shape:

```text
2 hits.

1. Malayan Banking Berhad (1155) - Group FY_2025
Return on equity: 11.7%
Proof: FY 2025 FINANCIAL STATEMENTS, page 5 | Score: 100%

2. Malayan Banking Berhad (1155) - Bank FY_2025
Return on equity: 13.5%
Proof: FY 2025 FINANCIAL STATEMENTS, page 5 | Score: 100%
```

## Step 10: Link Findamental Skill Into Hermes

Hermes loads skills from its skills folder.

macOS or WSL2:

```bash
mkdir -p ~/.hermes/skills
ln -s /path/to/findamental/skills/findamental ~/.hermes/skills/findamental
```

For this machine:

```bash
mkdir -p ~/.hermes/skills
ln -s /Users/sayyid/Documents/CV/findamental/skills/findamental ~/.hermes/skills/findamental
```

If the link already exists:

```bash
rm ~/.hermes/skills/findamental
ln -s /path/to/findamental/skills/findamental ~/.hermes/skills/findamental
```

Windows native PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\hermes\skills"
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\hermes\skills\findamental" -ErrorAction SilentlyContinue
Copy-Item -Recurse ".\skills\findamental" "$env:LOCALAPPDATA\hermes\skills\findamental"
```

WSL2 uses the macOS/Linux command with `~/.hermes/skills`.

## Step 11: Start Hermes Gateway

Start:

```bash
hermes gateway start
```

Check:

```bash
hermes gateway status
```

If already running, restart:

```bash
hermes gateway stop
hermes gateway start
```

Log file:

```bash
tail -f ~/.hermes/logs/gateway.log
```

Windows native log folder is usually:

```text
%LOCALAPPDATA%\hermes\logs
```

## Step 12: Test In Telegram

Open your bot chat in Telegram.

Send:

```text
/start
```

Then:

```text
/findamental Maybank 2025 ROE
```

More examples:

```text
/findamental Maybank FY 2025 revenue
/findamental Maybank FY 2021 diluted earning
/findamental Maybank 2025 total assets
/findamental Maybank 2024 cost to income ratio
/findamental Maybank 2025 PE ratio
/findamental calculate Maybank revenue growth 2025
/findamental calculate Maybank net profit margin 2025
```

Expected:

- Text answer
- Exact number
- Page proof
- Highlighted source screenshot

Calculated answers also show:

- Formula
- Input rows
- Source pages for each input

## Normal Workflow After Setup

Day to day:

```bash
cd /path/to/findamental
uv run findamental-query "Maybank FY 2025 revenue"
```

Telegram:

```text
/findamental Maybank FY 2025 revenue
```

If the PDF changes:

```bash
cd /path/to/findamental
make extract
hermes gateway stop
hermes gateway start
```

Windows:

```powershell
cd path\to\findamental
uv run python scripts/extract_all_demo_filings.py
hermes gateway stop
hermes gateway start
```

## Reset Demo Memory

Use this before teammate demos if existing Telegram users do not get the clean
Findamental intro.

macOS or WSL2:

```bash
cd /path/to/findamental
make reset-memory
```

Direct command:

```bash
bash scripts/reset_findamental_memory.sh
```

This backs up and clears:

```text
~/.hermes/state.db Telegram sessions
~/.hermes/sessions Telegram session files
~/.hermes/memories/USER.md
```

It keeps:

```text
Telegram bot token
Telegram allowed users
Findamental PDF index/cache
```

After reset, ask users to send:

```text
/findamental
```

## Run Tests

macOS or WSL2:

```bash
make test
make lint
```

Windows:

```powershell
uv run pytest
uv run ruff check src/ tests/ scripts/
uv run mypy src/
```

Expected:

```text
pytest passes
ruff clean
mypy clean
```

## Project Layout

```text
findamental/
├── maybank-ar2025-financial-statements.pdf
├── data/
│   ├── company_index.json
│   ├── line_items_dict.json
│   ├── sector_medians.json
│   ├── document_index/
│   ├── document_pack/
│   └── extracted_cache/
├── skills/findamental/
│   ├── SKILL.md
│   └── scripts/
├── src/findamental/
│   ├── cache/
│   ├── cv/
│   ├── index/
│   ├── output/
│   ├── valuation/
│   ├── cli.py
│   ├── query_router.py
│   └── service.py
├── scripts/
├── tests/
├── Makefile
└── pyproject.toml
```

## Troubleshooting

### Local query fails

Run:

```bash
cd /path/to/findamental
uv run findamental-query "Maybank 2025 ROE"
```

Fix local first. Telegram comes after.

### Bot does not reply

Check gateway:

```bash
hermes gateway status
tail -f ~/.hermes/logs/gateway.log
```

Common causes:

- Wrong Telegram bot token
- Wrong allowed user ID
- Gateway not restarted after config change
- Skill not copied or linked into Hermes skills folder

### `/findamental` not found

Check skill exists:

```bash
ls ~/.hermes/skills/findamental
```

Expected:

```text
SKILL.md
scripts/
```

Then restart:

```bash
hermes gateway stop
hermes gateway start
```

### Telegram says nothing but local command works

Problem is Hermes or Telegram, not Findamental.

Check:

```bash
hermes gateway setup
hermes gateway status
tail -f ~/.hermes/logs/gateway.log
```

### Query returns many answers

Broad query means many valid rows.

Example:

```text
Maybank FY 2025 revenue
```

Better:

```text
Maybank FY 2025 group operating revenue
Maybank FY 2025 bank operating revenue
Maybank FY 2025 insurance revenue
```

### Screenshot repeats

Same visual source row gets one screenshot. If you see duplicates, restart the
gateway so Hermes uses the latest code.

## Current Limitations

- Current tested filing is Maybank FY2025.
- Live Bursa fetch is stubbed.
- Other company PDFs need indexing before use.
- Telegram delivery depends on Hermes gateway setup.
- Windows native Hermes may have rough edges. WSL2 is safer.

## Security

Never commit:

```text
.env
Telegram bot token
OpenRouter API key
```

If a token was pasted in chat or committed, rotate it.
