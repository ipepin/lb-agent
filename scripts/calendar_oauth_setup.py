from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.services.calendar_service import CalendarService


def main() -> None:
    config = load_config()
    calendar_service = CalendarService(config)

    authorized = calendar_service.authorize()
    if not authorized:
        print("OAuth nastavení kalendáře selhalo. Zkontroluj credentials.json a Google knihovny.")
        return

    print(f"OAuth token kalendáře byl vytvořen: {config.google_calendar_token_path}")


if __name__ == "__main__":
    main()
