from __future__ import annotations

from app.config import AppConfig
from app.schemas.entities import Email, EmailClassification, ParsedEmail
from app.services.classifier_service import ClassifierService
from app.services.openai_service import OpenAIService
from app.services.parser_service import ParserService


class AITriageService:
    def __init__(
        self,
        config: AppConfig,
        classifier_service: ClassifierService | None = None,
        parser_service: ParserService | None = None,
        openai_service: OpenAIService | None = None,
    ) -> None:
        self.config = config
        self.classifier_service = classifier_service or ClassifierService()
        self.parser_service = parser_service or ParserService()
        self.openai_service = openai_service or OpenAIService(config)

    def analyze_email(self, email: Email) -> tuple[EmailClassification, ParsedEmail]:
        fallback_classification = self.classifier_service.classify_email(email)
        fallback_parsed = self.parser_service.parse_message(email, fallback_classification)

        if not self._should_use_ai(email, fallback_classification):
            return fallback_classification, fallback_parsed

        ai_result = self.openai_service.triage_email(email)
        if ai_result is None:
            return fallback_classification, fallback_parsed

        classification = EmailClassification(
            category=self._string_or_default(
                ai_result.get("category"),
                fallback_classification.category,
            ),
            action=self._string_or_default(
                ai_result.get("action"),
                fallback_classification.action,
            ),
            priority=self._string_or_default(
                ai_result.get("priority"),
                fallback_classification.priority,
            ),
            needs_reply=self._bool_or_default(
                ai_result.get("needs_reply"),
                fallback_classification.needs_reply,
            ),
            confidence=self._float_or_default(
                ai_result.get("confidence"),
                fallback_classification.confidence,
            ),
        )

        parsed_email = ParsedEmail(
            subject=email.subject,
            sender=email.sender,
            summary=self._string_or_default(ai_result.get("summary"), fallback_parsed.summary),
            category=classification.category,
            customer_name=self._string_or_default(
                ai_result.get("customer_name"),
                fallback_parsed.customer_name,
            ),
            company_name=self._string_or_default(
                ai_result.get("company_name"),
                fallback_parsed.company_name,
            ),
            contact=self._string_or_default(ai_result.get("contact"), fallback_parsed.contact),
            address=self._string_or_default(ai_result.get("address"), fallback_parsed.address),
            requested_deadline=self._string_or_none(
                ai_result.get("requested_deadline"),
                fallback_parsed.requested_deadline,
            ),
            requested_action=self._string_or_default(
                ai_result.get("requested_action"),
                fallback_parsed.requested_action,
            ),
            invoice_number=self._string_or_default(
                ai_result.get("invoice_number"),
                fallback_parsed.invoice_number,
            ),
            invoice_amount=self._float_or_none(
                ai_result.get("invoice_amount"),
                fallback_parsed.invoice_amount,
            ),
            invoice_currency=self._string_or_default(
                ai_result.get("invoice_currency"),
                fallback_parsed.invoice_currency,
            ),
            invoice_due_date=self._string_or_none(
                ai_result.get("invoice_due_date"),
                fallback_parsed.invoice_due_date,
            ),
            attachments=list(email.attachments),
            suggested_actions=self._string_list_or_default(
                ai_result.get("suggested_actions"),
                fallback_parsed.suggested_actions,
            ),
            draft_reply=self._string_or_default(
                ai_result.get("draft_reply"),
                fallback_parsed.draft_reply,
            ),
        )
        return classification, parsed_email

    def _should_use_ai(
        self,
        email: Email,
        fallback_classification: EmailClassification,
    ) -> bool:
        if not self.openai_service.is_configured():
            return False

        normalized_sender = email.sender.lower()
        normalized_subject = email.subject.lower()
        normalized_body = email.body.lower()

        marketing_markers = (
            "newsletter",
            "unsubscribe",
            "noreply",
            "no-reply",
            "notifikace@",
            "mailing@",
            "update.strava.com",
            "discover.pinterest.com",
        )
        actionable_markers = (
            "?",
            "reply",
            "odpovezte",
            "dejte vedet",
            "deadline",
            "termin",
            "invoice",
            "faktura",
            "task",
            "ukol",
            "nabid",
            "objednav",
            "schuz",
            "meeting",
            "payment",
            "splatnost",
        )

        combined = f"{normalized_sender}\n{normalized_subject}\n{normalized_body}"
        if any(marker in combined for marker in actionable_markers):
            return True

        if any(marker in combined for marker in marketing_markers):
            return False

        if fallback_classification.category in {"invoice", "calendar", "new_order", "task"}:
            return True

        if fallback_classification.category in {"newsletter", "marketing", "notification", "banking"}:
            return False

        if fallback_classification.category == "uncategorized":
            return True

        return fallback_classification.needs_reply

    def _string_or_default(self, value: object, default: str) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else default

    def _string_or_none(self, value: object, default: str | None) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    def _bool_or_default(self, value: object, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _float_or_default(self, value: object, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _float_or_none(self, value: object, default: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _string_list_or_default(self, value: object, default: list[str]) -> list[str]:
        if isinstance(value, list):
            normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            if normalized:
                return normalized
        return default
