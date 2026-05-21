.PHONY: install extract query test lint reset-memory

UV := $(HOME)/.local/bin/uv

install:
	$(UV) venv --python 3.12
	$(UV) pip install -e ".[dev]"

extract:
	$(UV) run python scripts/extract_all_demo_filings.py

query:
	$(UV) run findamental-query "$(q)"

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check src/ tests/ scripts/
	$(UV) run mypy src/

reset-memory:
	bash scripts/reset_findamental_memory.sh
