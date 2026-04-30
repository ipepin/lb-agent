import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import Email, Invoice
from app.services.invoice_service import InvoiceService


class TestInvoiceService(unittest.TestCase):
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
        self.config.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.service = InvoiceService(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_backfill_attachment_paths_from_source_email(self) -> None:
        pdf_path = self.config.attachments_dir / "invoice.pdf"
        pdf_path.write_bytes(b"pdf")

        crud.create_email(
            self.config,
            Email(
                id="email-1",
                thread_id="thread-1",
                sender="billing@example.com",
                subject="Faktura 2026-001",
                body="Viz priloha",
                received_at="2026-04-16T10:00:00+00:00",
                category="invoice",
                priority="high",
                attachments=[str(pdf_path)],
            ),
            summary="Faktura v PDF",
        )
        crud.create_invoice(
            self.config,
            Invoice(
                supplier="ACME s.r.o.",
                invoice_number="2026-001",
                amount=1000.0,
                currency="CZK",
                due_date="2026-04-30",
                source_email_id="email-1",
                attachment_path="",
            ),
        )

        updated = self.service.backfill_attachment_paths()
        invoices = list(self.service.list_invoices())

        self.assertEqual(updated, 1)
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].attachment_path, str(pdf_path))


if __name__ == "__main__":
    unittest.main()
