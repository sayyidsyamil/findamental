from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UV = Path.home() / ".local" / "bin" / "uv"
CHART_WORDS = {
    "chart",
    "graph",
    "plot",
    "visualise",
    "visualize",
    "trend",
    "bar",
    "line",
    "pie",
    "waterfall",
}


WELCOME = """Hi. I am Findamental.
Ask me Bursa filing questions. I answer with number, page proof, screenshot.

Try:
- Maybank operating revenue 2021
- Maybank 2025 ROE
- Maybank 2025 PE ratio
- calculate Maybank revenue growth 2025
- chart Maybank 2025 PE ratio
- pie chart Maybank group revenue breakdown 2025"""


def _run(command: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _clean_query(text: str) -> str:
    words = []
    for token in text.split():
        lowered = re.sub(r"[^a-z0-9]", "", token.lower())
        if lowered in CHART_WORDS:
            continue
        words.append(token)
    return " ".join(words).strip()


def _chart_type(text: str) -> str:
    lowered = text.lower()
    if "pie" in lowered or "breakdown" in lowered:
        return "pie"
    if "line" in lowered or "trend" in lowered:
        return "line"
    if "waterfall" in lowered:
        return "waterfall"
    return "bar"


def _media_path_from_output(output: str) -> str | None:
    image_match = re.search(r"Image:\s*(.+)", output)
    if image_match:
        path = Path(image_match.group(1).strip()).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            return str(path)
    return None


def query(text: str) -> int:
    result = _run([str(UV), "run", "findamental-query", text])
    output = (result.stdout or result.stderr).strip()
    if not output:
        print("No result.")
        return result.returncode or 1

    if "Need new PDF index" in output or "Cached metrics: none yet" in output:
        print("Report not indexed yet.")
        print("Use full ingest mode so I can browse, download the annual report, OCR it, then answer.")
        print(f"Ask without the slash command: findamental ingest {text}")
        return 1

    media_path = _media_path_from_output(output)
    clean = re.sub(r"\n?Image:\s*.+", "", output).strip()
    print(clean)
    if media_path:
        print(f"MEDIA:{media_path}")
    return result.returncode


def chart(text: str) -> int:
    financial_query = _clean_query(text)
    if not financial_query:
        print("Ask like: /findamental chart Maybank 2025 PE ratio")
        return 1

    chart_kind = _chart_type(text)
    stamp = int(time.time())
    output_path = ROOT / "data" / f"findamental_chart_{stamp}.png"
    result = _run(
        [
            str(UV),
            "run",
            "python",
            "skills/findamental/scripts/visualise.py",
            "--query",
            financial_query,
            "--type",
            chart_kind,
            "--title",
            financial_query.title(),
            "--output",
            str(output_path),
        ],
        timeout=60,
    )
    if result.returncode != 0 or not output_path.exists():
        print((result.stderr or result.stdout or "Chart failed.").strip())
        return result.returncode or 1

    print(f"{financial_query.title()}")
    print(f"Chart: {chart_kind}")
    print(f"MEDIA:{output_path}")
    return 0


def main() -> int:
    text = os.environ.get("HERMES_QUICK_COMMAND_ARGS", "").strip()
    if not text:
        text = " ".join(sys.argv[1:]).strip()
    if not text:
        print(WELCOME)
        return 0

    lowered = text.lower()
    if any(word in lowered for word in CHART_WORDS):
        return chart(text)
    return query(text)


if __name__ == "__main__":
    raise SystemExit(main())
