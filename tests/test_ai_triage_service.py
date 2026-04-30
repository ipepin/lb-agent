import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.schemas.entities import Email
from app.services.ai_triage_service import AITriageService
from app.services.openai_service import OpenAIService


class FakeOpenAIService(OpenAIService):
    def __init__(self, config: AppConfig, payload: dict | None) -> None:
        super().__init__(config)
        self.payload = payload
        self.calls = 0

    def triage_email(self, email: Email) -> dict | None:
        self.calls += 1
        return self.payload


class TestAITriageService(unittest.TestCase):
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
            gmail_query="is:unread in:inbox",
            openai_api_key="test-key",
            openai_model="gpt-5.4-mini",
            openai_reasoning_effort="low",
            google_calendar_id="",
            idoklad_client_id="",
            idoklad_client_secret="",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ai_output_overrides_fallback(self) -> None:
        service = AITriageService(
            config=self.config,
            openai_service=FakeOpenAIService(
                self.config,
                payload={
                    "category": "task",
                    "action": "create_task",
                    "priority": "high",
                    "needs_reply": True,
                    "confidence": 0.91,
                    "summary": "Customer wants a response and a weekly report.",
                    "requested_action": "prepare_report",
                    "requested_deadline": "2026-04-20",
                    "suggested_actions": ["create task", "draft reply"],
                    "draft_reply": "Thanks, I will prepare the report and get back to you.",
                },
            ),
        )
        email = Email(
            id="1",
            sender="Client <client@example.com>",
            subject="Need weekly report",
            body="Please prepare the weekly report and let me know by Monday.",
            received_at="2026-04-16T10:00:00+00:00",
        )

        classification, parsed_email = service.analyze_email(email)

        self.assertEqual(classification.category, "task")
        self.assertTrue(classification.needs_reply)
        self.assertEqual(parsed_email.requested_deadline, "2026-04-20")
        self.assertEqual(parsed_email.draft_reply, "Thanks, I will prepare the report and get back to you.")

    def test_newsletter_skips_ai_call(self) -> None:
        fake_openai = FakeOpenAIService(
            self.config,
            payload={
                "category": "task",
                "action": "create_task",
                "priority": "high",
                "needs_reply": True,
                "confidence": 0.9,
                "summary": "Should not be used.",
            },
        )
        service = AITriageService(
            config=self.config,
            openai_service=fake_openai,
        )
        email = Email(
            id="newsletter-1",
            sender="newsletter@example.com",
            subject="Weekly newsletter",
            body="Read our newsletter and unsubscribe here.",
            received_at="2026-04-16T10:00:00+00:00",
        )

        classification, parsed_email = service.analyze_email(email)

        self.assertEqual(fake_openai.calls, 0)
        self.assertEqual(classification.category, "newsletter")
        self.assertEqual(parsed_email.draft_reply, "")

    def test_banking_notification_skips_ai_call(self) -> None:
        fake_openai = FakeOpenAIService(
            self.config,
            payload={"category": "task"},
        )
        service = AITriageService(
            config=self.config,
            openai_service=fake_openai,
        )
        email = Email(
            id="bank-1",
            sender="kontakt@mbank.cz",
            subject="mBank - Email Push",
            body="Na uctu probehla transakce kartou.",
            received_at="2026-04-16T10:00:00+00:00",
        )

        classification, _ = service.analyze_email(email)

        self.assertEqual(fake_openai.calls, 0)
        self.assertEqual(classification.category, "banking")


if __name__ == "__main__":
    unittest.main()
