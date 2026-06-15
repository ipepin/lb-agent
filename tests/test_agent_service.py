import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import Email
from app.services.agent_service import AgentService
from app.services.gmail_service import GmailService


class FakeGmailService(GmailService):
    def __init__(self, config: AppConfig, messages: list[Email]) -> None:
        self.config = config
        self._messages = messages

    def fetch_new_messages(
        self,
        processed_email_ids: set[str],
        max_results: int = 0,
        received_after: str | None = None,
        progress_callback: object | None = None,
    ) -> list[Email]:
        source_messages = self._messages[:max_results] if max_results and max_results > 0 else self._messages
        return [
            message
            for message in source_messages
            if message.id not in processed_email_ids
        ]


class TestAgentService(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.config = AppConfig(
            project_root=root,
            data_dir=root / "data",
            attachments_dir=root / "data" / "attachments",
            db_path=root / "data" / "app.db",
            sync_state_path=root / "data" / "last_sync.txt",
            agent_poll_interval_seconds=60,
            notification_channel="log",
            gmail_credentials_path=root / "credentials.json",
            gmail_token_path=root / "data" / "gmail_token.json",
            gmail_query="-in:spam -in:trash",
            openai_api_key="",
            openai_model="gpt-5.4-mini",
            openai_reasoning_effort="low",
            google_calendar_id="",
            idoklad_client_id="",
            idoklad_client_secret="",
        )
        initialize_database(self.config)
        self.agent_service = AgentService(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_process_email_stores_mail_as_uncategorized(self) -> None:
        email = Email(
            id="mail-1",
            sender="ACME s.r.o. <billing@acme.cz>",
            subject="Faktura 2024-001",
            body=(
                "Company: ACME s.r.o.\n"
                "Splatnost: 2026-04-30\n"
                "Invoice No: 2024-001\n"
                "Amount: 12500 CZK\n"
            ),
            received_at="2026-04-16T09:00:00+00:00",
            attachments=["invoice.pdf"],
        )

        result = self.agent_service.process_email(email)

        stored_emails = list(crud.list_emails(self.config))
        self.assertEqual(len(stored_emails), 1)
        self.assertEqual(stored_emails[0].category, "uncategorized")
        self.assertEqual(stored_emails[0].summary, "Company: ACME s.r.o. Splatnost: 2026-04-30")
        self.assertEqual(stored_emails[0].ai_payload["classification"]["action"], "create_invoice")
        self.assertIn("parsed_email", stored_emails[0].ai_payload)
        self.assertEqual(result.approval_ids, [])
        self.assertEqual(result.reminder_ids, [])

    def test_run_cycle_fetches_new_gmail_messages(self) -> None:
        gmail_service = FakeGmailService(
            self.config,
            messages=[
                Email(
                    id="gmail-1",
                    sender="Client <client@example.com>",
                    subject="New task request",
                    body="New task: prepare weekly report.\nDeadline: 2026-04-20",
                    received_at="2026-04-16T10:00:00+00:00",
                )
            ],
        )
        agent_service = AgentService(self.config, gmail_service=gmail_service)

        result = agent_service.run_cycle()

        self.assertEqual(result.checked_emails, 1)
        self.assertEqual(len(crud.list_emails(self.config)), 1)
        self.assertEqual(result.pending_approvals, 0)
        self.assertTrue(self.config.sync_state_path.exists())

    def test_run_cycle_writes_last_sync_from_latest_email_not_current_time(self) -> None:
        gmail_service = FakeGmailService(
            self.config,
            messages=[
                Email(
                    id="gmail-2",
                    sender="Client <client@example.com>",
                    subject="Druhy mail",
                    body="Obsah",
                    received_at="2026-04-16T11:00:00+00:00",
                )
            ],
        )
        agent_service = AgentService(self.config, gmail_service=gmail_service)

        agent_service.run_cycle()

        written = self.config.sync_state_path.read_text(encoding="utf-8").strip()
        self.assertEqual(written, "2026-04-16T11:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
