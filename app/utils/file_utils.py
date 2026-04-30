from __future__ import annotations

from pathlib import Path
import re


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", value).strip()
    return sanitized or "attachment"
