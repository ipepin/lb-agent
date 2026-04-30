from __future__ import annotations

import html
import re


def html_to_text(value: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</p\s*>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</div\s*>", "\n", cleaned)
    cleaned = re.sub(r"(?is)<.*?>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return normalize_email_text(cleaned)


def normalize_email_text(value: str) -> str:
    text = value.replace("\r", "\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def cleanup_email_text(value: str) -> str:
    text = normalize_email_text(value)
    lines = [line.strip() for line in text.splitlines()]
    filtered_lines: list[str] = []

    noise_patterns = (
        "unsubscribe",
        "odhlasit",
        "odhlášení",
        "zobrazit online verzi",
        "view in browser",
        "open in browser",
        "pokud si nepřejete",
        "tento e-mail byl odeslán",
        "copyright",
        "vsechna prava vyhrazena",
        "all rights reserved",
    )

    for line in lines:
        if not line:
            filtered_lines.append("")
            continue

        normalized = line.lower()
        if any(pattern in normalized for pattern in noise_patterns):
            continue
        if normalized.startswith("http") and len(normalized) > 80:
            continue
        filtered_lines.append(line)

    cleaned = "\n".join(filtered_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
