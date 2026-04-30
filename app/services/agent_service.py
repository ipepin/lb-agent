from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from app.config import AppConfig
from app.db import crud
from app.schemas.entities import AgentCycleResult, Email, EmailProcessingResult
from app.services.ai_triage_service import AITriageService
from app.services.approval_service import ApprovalService
from app.services.gmail_service import GmailService
from app.services.notification_service import NotificationService
from app.services.reminder_service import ReminderService
from app.utils.dates import is_due_timestamp, utc_now_iso


class AgentService:
    def __init__(
        self,
        config: AppConfig,
        ai_triage_service: AITriageService | None = None,
        approval_service: ApprovalService | None = None,
        reminder_service: ReminderService | None = None,
        notification_service: NotificationService | None = None,
        gmail_service: GmailService | None = None,
    ) -> None:
        self.config = config
        self.ai_triage_service = ai_triage_service or AITriageService(config)
        self.approval_service = approval_service or ApprovalService(config)
        self.reminder_service = reminder_service or ReminderService(config)
        self.notification_service = notification_service or NotificationService(config)
        self.gmail_service = gmail_service or GmailService(config)

    def process_email(self, email: Email) -> EmailProcessingResult:
        classification, parsed_email = self.ai_triage_service.analyze_email(email)
        email.category = "uncategorized"
        email.priority = "normal"
        crud.create_email(self.config, email, summary="")

        return EmailProcessingResult(
            email=email,
            classification=classification,
            parsed_email=parsed_email,
            approval_ids=[],
            reminder_ids=[],
        )

    def run_cycle(
        self,
        progress_callback: Callable[[str, int | None, int | None], None] | None = None,
    ) -> AgentCycleResult:
        existing_emails = list(crud.list_emails(self.config))
        existing_email_ids = {email.id for email in existing_emails}
        last_sync_at = self._read_last_sync_at(existing_emails)
        max_results = 200 if not existing_emails else 0
        new_messages = self.gmail_service.fetch_new_messages(
            existing_email_ids,
            max_results=max_results,
            received_after=last_sync_at,
            progress_callback=progress_callback,
        )
        total_messages = len(new_messages)
        for index, message in enumerate(new_messages, start=1):
            if progress_callback is not None:
                progress_callback("Analyzuji e-maily...", index, total_messages)
            self.process_email(message)

        approvals = [
            item for item in self.approval_service.list_items() if item.status == "pending"
        ]
        reminders = [
            reminder
            for reminder in self.reminder_service.list_reminders()
            if reminder.status == "pending"
        ]

        now = datetime.now(tz=timezone.utc)
        due_reminders = [
            reminder for reminder in reminders if is_due_timestamp(reminder.remind_at, now)
        ]

        notifications_sent = 0
        if progress_callback is not None:
            progress_callback("Dokoncuji synchronizaci...", None, None)
        notifications_sent += self.notification_service.notify_due_reminders(due_reminders)
        notifications_sent += self.notification_service.notify_pending_approvals(approvals)
        self._write_last_sync_at(self._resolve_next_sync_at(last_sync_at, new_messages, existing_emails))

        return AgentCycleResult(
            checked_emails=len(crud.list_emails(self.config)),
            pending_approvals=len(approvals),
            due_reminders=len(due_reminders),
            notifications_sent=notifications_sent,
        )

    def _read_last_sync_at(self, existing_emails: list[object]) -> str | None:
        if not existing_emails:
            return (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
        if self.config.sync_state_path.exists():
            value = self.config.sync_state_path.read_text(encoding="utf-8").strip().lstrip("\ufeff")
            if value:
                return value
        latest_email = max(existing_emails, key=lambda item: item.received_at or "")
        return latest_email.received_at or None

    def _write_last_sync_at(self, value: str) -> None:
        self.config.sync_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.sync_state_path.write_text(value, encoding="utf-8")

    def _resolve_next_sync_at(
        self,
        last_sync_at: str | None,
        new_messages: list[Email],
        existing_emails: list[object],
    ) -> str:
        timestamps: list[str] = []
        if last_sync_at:
            timestamps.append(last_sync_at)
        timestamps.extend(
            message.received_at
            for message in new_messages
            if message.received_at
        )
        timestamps.extend(
            getattr(email, "received_at", "")
            for email in existing_emails
            if getattr(email, "received_at", "")
        )
        valid_timestamps = [value for value in timestamps if value]
        if not valid_timestamps:
            return utc_now_iso()
        return max(valid_timestamps)
