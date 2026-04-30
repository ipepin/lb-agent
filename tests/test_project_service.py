import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import Email
from app.services.project_service import ProjectService


class TestProjectService(unittest.TestCase):
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
            openai_api_key="",
            openai_model="gpt-5.4-mini",
            openai_reasoning_effort="low",
            google_calendar_id="",
            idoklad_client_id="",
            idoklad_client_secret="",
        )
        initialize_database(self.config)
        self.service = ProjectService(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_assign_email_to_project(self) -> None:
        project = self.service.get_or_create_project("Zakazka Alfa")
        self.assertIsNotNone(project)

        crud.create_email(
            self.config,
            Email(
                id="email-1",
                thread_id="thread-1",
                sender="client@example.com",
                subject="Nova poptavka",
                body="Potrebujeme cenovou nabidku.",
                received_at="2026-04-16T10:00:00+00:00",
            ),
            summary="Poptavka",
        )

        updated = self.service.assign_email("email-1", project.id)
        email = crud.get_email(self.config, "email-1")

        self.assertTrue(updated)
        self.assertIsNotNone(email)
        self.assertEqual(email.project_id, project.id)

    def test_update_project_status(self) -> None:
        project = self.service.get_or_create_project("Zakazka Beta")
        self.assertIsNotNone(project)

        updated = self.service.update_status(project.id, "done")
        refreshed = self.service.get_project(project.id)

        self.assertTrue(updated)
        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed.status, "done")

    def test_update_project_description(self) -> None:
        project = self.service.get_or_create_project("Zakazka Gamma")
        self.assertIsNotNone(project)

        updated = self.service.update_description(project.id, "Rucni poznamka")
        refreshed = self.service.get_project(project.id)

        self.assertTrue(updated)
        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed.description, "Rucni poznamka")


if __name__ == "__main__":
    unittest.main()
