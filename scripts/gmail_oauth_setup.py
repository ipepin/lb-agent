from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.services.gmail_service import GmailService


def main() -> None:
    config = load_config()
    gmail_service = GmailService(config)

    authorized = gmail_service.authorize()
    if not authorized:
        print("OAuth setup failed. Check Google client libraries and credentials.json path.")
        return

    print(f"OAuth token created: {config.gmail_token_path}")


if __name__ == "__main__":
    main()
