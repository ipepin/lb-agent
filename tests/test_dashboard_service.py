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


if __name__ == "__main__":
    unittest.main()
