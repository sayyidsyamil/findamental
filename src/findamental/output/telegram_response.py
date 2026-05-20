from dataclasses import dataclass
from pathlib import Path


@dataclass
class TelegramResponse:
    text: str
    image_path: Path | None = None
    image_paths: list[Path] | None = None
    inline_buttons: list[tuple[str, str]] | None = None
