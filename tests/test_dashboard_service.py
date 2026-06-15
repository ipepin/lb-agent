import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import Email
from app.services.dashboard_service import DashboardService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


class TestDashboardService(unittest.TestCase):
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
            gmail_query="-in:spam -in:trash -in:sent",
            openai_api_key="",
            openai_model="gpt-5.4-mini",
            openai_reasoning_effort="low",
            google_calendar_id="",
            idoklad_client_id="",
            idoklad_client_secret="",
        )
        initialize_database(self.config)
        self.dashboard_service = DashboardService(self.config)
        self.project_service = ProjectService(self.config)
        self.task_service = TaskService(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_snapshot_counts(self) -> None:
        self.project_service.create_project("Zakazka Omega")
        self.task_service.create_task("Zavolat klientovi")
        crud.create_email(
            self.config,
            Email(
                id="email-1",
                thread_id="thread-1",
                sender="client@example.com",
                subject="Nova poptavka",
                body="Dobry den, prosim o nabidku.",
                received_at="2026-04-17T08:00:00+00:00",
                category="uncategorized",
            ),
            summary="Poptavka",
        )

        snapshot = self.dashboard_service.get_snapshot()

        self.assertEqual(snapshot["counts"]["emails"], 1)
        self.assertEqual(snapshot["counts"]["unprocessed_emails"], 1)
        self.assertEqual(snapshot["counts"]["open_tasks"], 1)
        self.assertEqual(snapshot["counts"]["active_projects"], 1)

    def test_snapshot_includes_ai_triage_stats(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-ai-1",
                thread_id="thread-ai-1",
                sender="client@example.com",
                subject="Nova poptavka",
                body="Prosim pripravit nabidku.",
                received_at="2026-04-17T08:00:00+00:00",
            ),
            summary="Poptavka",
            ai_payload={
                "classification": {"action": "create_task"},
                "user_decision": {"action": "create_task", "matches_ai_suggestion": True},
            },
        )
        crud.create_email(
            self.config,
            Email(
                id="email-ai-2",
                thread_id="thread-ai-2",
                sender="supplier@example.com",
                subject="Faktura",
                body="Zasilam fakturu.",
                received_at="2026-04-17T09:00:00+00:00",
            ),
            summary="Faktura",
            ai_payload={
                "classification": {"action": "create_invoice"},
                "user_decision": {"action": "ignore", "matches_ai_suggestion": False},
            },
        )
        crud.create_email(
            self.config,
            Email(
                id="email-ai-3",
                thread_id="thread-ai-3",
                sender="calendar@example.com",
                subject="Termin schuzky",
                body="Muzeme zitra v 10?",
                received_at="2026-04-17T10:00:00+00:00",
            ),
            summary="Termin",
            ai_payload={
                "classification": {"action": "create_calendar_event"},
            },
        )

        snapshot = self.dashboard_service.get_snapshot()
        triage = snapshot["triage"]

        self.assertEqual(triage["suggested_total"], 3)
        self.assertEqual(triage["confirmed_total"], 2)
        self.assertEqual(triage["matched_total"], 1)
        self.assertEqual(triage["mismatched_total"], 1)
        self.assertEqual(triage["pending_review_total"], 1)
        self.assertEqual(len(triage["top_suggested_actions"]), 3)
        self.assertEqual(
            {item["action"] for item in triage["top_suggested_actions"]},
            {"create_task", "create_invoice", "create_calendar_event"},
        )


if __name__ == "__main__":
    unittest.main()
