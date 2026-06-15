from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import AppConfig, load_config
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import Email
from app.services.ai_triage_service import AITriageService
from app.utils.dates import utc_now_iso


def _to_email_entity(item: object) -> Email:
    return Email(
        id=getattr(item, "id"),
        thread_id=getattr(item, "thread_id"),
        sender=getattr(item, "sender"),
        subject=getattr(item, "subject"),
        body=getattr(item, "body"),
        received_at=getattr(item, "received_at"),
        attachments=list(getattr(item, "attachments", []) or []),
        category=getattr(item, "category", "uncategorized"),
        priority=getattr(item, "priority", "normal"),
        project_id=getattr(item, "project_id", None),
    )


def backfill(config: AppConfig, limit: int | None = None) -> tuple[int, int]:
    initialize_database(config)
    triage_service = AITriageService(config)
    emails = list(crud.list_emails(config))
    processed = 0
    updated = 0

    for item in emails:
        if getattr(item, "ai_payload", None):
            continue
        email = _to_email_entity(item)
        classification, parsed_email = triage_service.analyze_email(email)
        payload = {
            "classification": asdict(classification),
            "parsed_email": asdict(parsed_email),
            "generated_at": utc_now_iso(),
            "backfilled": True,
        }
        if crud.update_email_ai_payload(config, email.id, payload):
            updated += 1
        processed += 1
        if limit is not None and processed >= limit:
            break

    return processed, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill AI triage payload for stored emails.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of missing emails to backfill.")
    args = parser.parse_args()

    config = load_config()
    processed, updated = backfill(config, limit=args.limit)
    print(f"processed={processed} updated={updated}")


if __name__ == "__main__":
    main()
