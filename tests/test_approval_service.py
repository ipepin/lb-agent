import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import ApprovalItem, Email
from app.services.project_service import ProjectService
from app.services.approval_service import ApprovalService
from app.services.invoice_service import InvoiceService
from app.services.task_service import TaskService


class TestApprovalService(unittest.TestCase):
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
        self.service = ApprovalService(self.config)
        self.invoice_service = InvoiceService(self.config)
        self.project_service = ProjectService(self.config)
        self.task_service = TaskService(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_approve_task_item_creates_task(self) -> None:
        project = self.project_service.get_or_create_project("Zakazka Alfa")
        self.assertIsNotNone(project)
        crud.create_email(
            self.config,
            Email(
                id="email-1",
                thread_id="thread-1",
                sender="client@example.com",
                subject="Need report",
                body="Prepare weekly report",
                received_at="2026-04-16T10:00:00+00:00",
                project_id=project.id,
            ),
            summary="Prepare weekly report",
        )
        item_id = self.service.save_items(
            [
                ApprovalItem(
                    action_type="create_task",
                    title="Create task from email: Need report",
                    payload={
                        "title": "Need report",
                        "description": "Prepare weekly report",
                        "priority": "high",
                        "due_date": "2026-04-20",
                    },
                    source_email_id="email-1",
                    reason="Requested by sender.",
                )
            ]
        )[0]

        approved = self.service.approve_item(item_id)
        tasks = self.task_service.list_tasks()
        item = self.service.get_item(item_id)

        self.assertTrue(approved)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Need report")
        self.assertEqual(tasks[0].project_id, project.id)
        self.assertIsNotNone(item)
        self.assertEqual(item.status, "approved")

    def test_reject_item_updates_status(self) -> None:
        item_id = self.service.save_items(
            [
                ApprovalItem(
                    action_type="draft_email_reply",
                    title="Draft reply",
                    payload={"draft_reply": "Hello"},
                )
            ]
        )[0]

        rejected = self.service.reject_item(item_id)
        item = self.service.get_item(item_id)

        self.assertTrue(rejected)
        self.assertIsNotNone(item)
        self.assertEqual(item.status, "rejected")

    def test_complete_task_updates_status(self) -> None:
        task_id = self.task_service.create_task(title="Dokoncit me")

        completed = self.task_service.complete_task(task_id)
        tasks = self.task_service.list_tasks()

        self.assertTrue(completed)
        self.assertEqual(tasks[0].status, "done")

    def test_approve_invoice_item_creates_invoice_with_attachment(self) -> None:
        item_id = self.service.save_items(
            [
                ApprovalItem(
                    action_type="create_invoice",
                    title="Register invoice",
                    payload={
                        "supplier": "ACME s.r.o.",
                        "invoice_number": "2026-001",
                        "amount": 12500,
                        "currency": "CZK",
                        "due_date": "2026-04-30",
                        "attachment_path": str(
                            self.config.attachments_dir / "faktura-2026-001.pdf"
                        ),
                    },
                    source_email_id="email-2",
                    reason="Invoice detected.",
                )
            ]
        )[0]

        approved = self.service.approve_item(item_id)
        invoices = self.invoice_service.list_invoices()
        item = self.service.get_item(item_id)

        self.assertTrue(approved)
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].supplier, "ACME s.r.o.")
        self.assertEqual(invoices[0].invoice_number, "2026-001")
        self.assertEqual(
            invoices[0].attachment_path,
            str(self.config.attachments_dir / "faktura-2026-001.pdf"),
        )
        self.assertIsNotNone(item)
        self.assertEqual(item.status, "approved")


if __name__ == "__main__":
    unittest.main()
