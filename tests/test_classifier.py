import unittest

from app.schemas.entities import Email
from app.services.classifier_service import ClassifierService


class TestClassifierService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ClassifierService()

    def test_invoice_classification(self) -> None:
        result = self.service.classify_text("Please review this invoice for April.")
        self.assertEqual(result, "invoice")

    def test_task_classification(self) -> None:
        result = self.service.classify_text("New task: prepare weekly report.")
        self.assertEqual(result, "task")

    def test_calendar_classification_from_context(self) -> None:
        email = Email(
            id="1",
            sender="Client <client@example.com>",
            subject="Request to reschedule meeting",
            body="Can we move the meeting to Friday at 10:00?",
            received_at="2026-04-15T10:00:00+00:00",
        )
        result = self.service.classify_email(email)
        self.assertEqual(result.category, "calendar")
        self.assertEqual(result.action, "create_calendar_event")

    def test_newsletter_classification(self) -> None:
        email = Email(
            id="2",
            sender="newsletter@example.com",
            subject="Specialni nabidka pro vas",
            body="View in browser\nUnsubscribe here\nVelka sleva tento tyden.",
            received_at="2026-04-16T10:00:00+00:00",
        )
        result = self.service.classify_email(email)
        self.assertEqual(result.category, "newsletter")
        self.assertEqual(result.action, "monitor_only")
        self.assertFalse(result.needs_reply)

    def test_banking_classification(self) -> None:
        email = Email(
            id="bank-1",
            sender="kontakt@mbank.cz",
            subject="mBank - Email Push",
            body="Na uctu probehla transakce kartou.",
            received_at="2026-04-16T10:00:00+00:00",
        )
        result = self.service.classify_email(email)
        self.assertEqual(result.category, "banking")
        self.assertEqual(result.action, "monitor_only")

    def test_marketing_classification(self) -> None:
        email = Email(
            id="promo-1",
            sender="akce@example.com",
            subject="Specialni nabidka pro vas",
            body="Velka sleva, postovne zdarma a akce jen dnes.",
            received_at="2026-04-16T10:00:00+00:00",
        )
        result = self.service.classify_email(email)
        self.assertEqual(result.category, "marketing")
        self.assertEqual(result.action, "monitor_only")

    def test_uncategorized_fallback(self) -> None:
        email = Email(
            id="3",
            sender="hello@example.com",
            subject="Ahoj",
            body="Jen se ozyvam bez dalsiho pozadavku.",
            received_at="2026-04-16T10:00:00+00:00",
        )
        result = self.service.classify_email(email)
        self.assertEqual(result.category, "uncategorized")
        self.assertEqual(result.action, "monitor_only")


if __name__ == "__main__":
    unittest.main()
