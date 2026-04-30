from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import ReminderModel
from app.schemas.entities import Reminder


class ReminderService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def create_reminder(
        self,
        title: str,
        remind_at: str,
        notes: str = "",
        related_type: str = "",
        related_id: str = "",
        status: str = "pending",
    ) -> int:
        reminder = Reminder(
            title=title,
            remind_at=remind_at,
            notes=notes,
            related_type=related_type,
            related_id=related_id,
            status=status,
        )
        return crud.create_reminder(self.config, reminder)

    def list_reminders(self) -> Sequence[ReminderModel]:
        return crud.list_reminders(self.config)
