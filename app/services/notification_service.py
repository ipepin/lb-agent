from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db.models import ApprovalItemModel, ReminderModel
from app.utils.logger import get_logger


logger = get_logger(__name__)


class NotificationService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def notify_due_reminders(self, reminders: Sequence[ReminderModel]) -> int:
        count = 0
        for reminder in reminders:
            self._publish(
                title=f"Reminder due: {reminder.title}",
                message=reminder.notes or f"Scheduled for {reminder.remind_at}",
            )
            count += 1
        return count

    def notify_pending_approvals(self, approvals: Sequence[ApprovalItemModel]) -> int:
        if not approvals:
            return 0

        self._publish(
            title="Pending approvals",
            message=f"{len(approvals)} approval item(s) waiting for review.",
        )
        return 1

    def _publish(self, title: str, message: str) -> None:
        channel = self.config.notification_channel.lower()

        if channel == "log":
            logger.info("%s | %s", title, message)
            return

        logger.info("[%s] %s | %s", channel, title, message)

