from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.main import bootstrap
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService


def main() -> None:
    config = load_config()
    bootstrap(config)

    task_service = TaskService(config)
    reminder_service = ReminderService(config)

    if not task_service.list_tasks():
        task_service.create_task(
            title="Zkontrolovat nové e-maily",
            description="Projdi inbox a označ důležité zprávy.",
        )

    if not reminder_service.list_reminders():
        reminder_service.create_reminder(
            title="Denní kontrola úkolů",
            remind_at="09:00",
            notes="Ranní přehled dne.",
        )

    print("Seed data created.")


if __name__ == "__main__":
    main()
