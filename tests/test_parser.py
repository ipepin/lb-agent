import unittest
from unittest.mock import patch

from app.schemas.entities import Email, EmailClassification
from app.services.parser_service import ParserService


class TestParserService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ParserService()

    def test_parse_invoice_fields(self) -> None:
        email = Email(
            id="mail-1",
            sender="ACME s.r.o. <billing@acme.cz>",
            subject="Invoice 2024-001",
            body=(
                "Company: ACME s.r.o.\n"
                "Splatnost: 2026-04-30\n"
                "Invoice No: 2024-001\n"
                "Amount: 12500 CZK\n"
            ),
            received_at="2026-04-15T10:00:00+00:00",
            attachments=["invoice.pdf"],
        )
        classification = EmailClassification(
            category="invoice",
            action="create_invoice",
            priority="high",
            needs_reply=False,
            confidence=0.9,
        )

        result = self.service.parse_message(email, classification)

        self.assertEqual(result.company_name, "ACME s.r.o.")
        self.assertEqual(result.invoice_number, "2024-001")
        self.assertEqual(result.invoice_due_date, "2026-04-30")
        self.assertEqual(result.invoice_amount, 12500.0)

    def test_parse_invoice_fields_from_pdf_text(self) -> None:
        email = Email(
            id="mail-2",
            sender="Dodavatel <billing@example.com>",
            subject="Faktura v priloze",
            body="Viz prilozene PDF.",
            received_at="2026-04-15T10:00:00+00:00",
            attachments=["invoice.pdf"],
        )
        classification = EmailClassification(
            category="invoice",
            action="create_invoice",
            priority="high",
            needs_reply=False,
            confidence=0.9,
        )

        with patch.object(
            self.service,
            "_extract_attachment_text",
            return_value=(
                "Dodavatel: ACME s.r.o.\n"
                "Cislo faktury: 2026-991\n"
                "Datum splatnosti: 2026-05-10\n"
                "Celkova castka: 14990 CZK\n"
            ),
        ):
            result = self.service.parse_message(email, classification)

        self.assertEqual(result.company_name, "ACME s.r.o.")
        self.assertEqual(result.invoice_number, "2026-991")
        self.assertEqual(result.invoice_due_date, "2026-05-10")
        self.assertEqual(result.invoice_amount, 14990.0)


if __name__ == "__main__":
    unittest.main()
