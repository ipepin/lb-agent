from __future__ import annotations

import unicodedata

from app.schemas.entities import Email, EmailClassification


class ClassifierService:
    def classify_email(self, email: Email) -> EmailClassification:
        normalized = self._normalize(f"{email.subject}\n{email.body}\n{email.sender}")
        scores = {
            "banking": self._score_banking(normalized),
            "notification": self._score_notification(normalized),
            "marketing": self._score_marketing(normalized),
            "newsletter": self._score_newsletter(normalized),
            "invoice": self._score_invoice(normalized),
            "calendar": self._score_calendar(normalized),
            "new_order": self._score_new_order(normalized),
            "task": self._score_task(normalized),
            "uncategorized": 1,
        }

        category = max(scores, key=scores.get)
        needs_reply = self._needs_reply(normalized)
        priority = self._resolve_priority(normalized, category)
        action = self._resolve_action(category=category, needs_reply=needs_reply)
        confidence = min(0.95, scores[category] / 6.0)

        return EmailClassification(
            category=category,
            action=action,
            priority=priority,
            needs_reply=needs_reply,
            confidence=round(confidence, 2),
        )

    def classify_text(self, text: str) -> str:
        email = Email(
            id="preview",
            subject="",
            sender="",
            body=text,
            received_at="",
        )
        return self.classify_email(email).category

    def _score_invoice(self, text: str) -> int:
        score = 0
        for keyword in ("invoice", "faktura", "billing", "payment", "splatnost", "iban"):
            if keyword in text:
                score += 2
        if any(token in text for token in ("kc", "czk", "eur", "usd")):
            score += 1
        return score

    def _score_banking(self, text: str) -> int:
        score = 0
        for keyword in (
            "mbank",
            "banka",
            "bank",
            "bankovni",
            "payment card",
            "platba kartou",
            "transakce",
            "zustatek",
            "email push",
            "ucet",
        ):
            if keyword in text:
                score += 2
        return score

    def _score_notification(self, text: str) -> int:
        score = 0
        for keyword in (
            "notification",
            "upozorneni",
            "alert",
            "account",
            "scheduled",
            "status update",
            "reminder",
            "system message",
            "security notice",
            "activity",
        ):
            if keyword in text:
                score += 2
        return score

    def _score_marketing(self, text: str) -> int:
        score = 0
        for keyword in (
            "specialni nabidka",
            "nabidka",
            "sleva",
            "akce",
            "akcni",
            "discount",
            "sale",
            "promo",
            "promotion",
            "coupon",
            "poštovne zdarma",
            "postovne zdarma",
        ):
            if keyword in text:
                score += 2
        return score

    def _score_newsletter(self, text: str) -> int:
        score = 0
        for keyword in (
            "newsletter",
            "unsubscribe",
            "odhlasit",
            "odhlaseni",
            "mailing",
            "noreply",
            "no-reply",
            "view in browser",
            "zobrazit online verzi",
            "specialni nabidka",
            "akcni",
            "sleva",
            "discount",
            "sale",
        ):
            if keyword in text:
                score += 2
        return score

    def _score_calendar(self, text: str) -> int:
        score = 0
        for keyword in (
            "meeting",
            "schuzka",
            "call",
            "calendar",
            "termin",
            "reschedule",
            "prelozit",
        ):
            if keyword in text:
                score += 2
        return score

    def _score_new_order(self, text: str) -> int:
        score = 0
        for keyword in (
            "zakazka",
            "objednavka",
            "poptavka",
            "nabidka",
            "cenova nabidka",
        ):
            if keyword in text:
                score += 2
        return score

    def _score_task(self, text: str) -> int:
        score = 0
        for keyword in (
            "task",
            "todo",
            "ukol",
            "follow up",
            "zavolat",
            "odeslat",
            "pripravit",
            "reply",
            "odpovedet",
        ):
            if keyword in text:
                score += 2
        return score

    def _needs_reply(self, text: str) -> bool:
        if any(
            marker in text
            for marker in (
                "newsletter",
                "unsubscribe",
                "odhlasit",
                "email push",
                "notification",
                "upozorneni",
            )
        ):
            return False
        reply_markers = (
            "?",
            "reply",
            "odpovezte",
            "prosim o odpoved",
            "dejte vedet",
            "let me know",
        )
        return any(marker in text for marker in reply_markers)

    def _resolve_priority(self, text: str, category: str) -> str:
        if category in {"newsletter", "marketing"}:
            return "low"
        if any(keyword in text for keyword in ("urgent", "asap", "hned", "dnes", "zitrek")):
            return "high"
        if category == "invoice" and "splatnost" in text:
            return "high"
        if category in {"banking", "notification"}:
            return "normal"
        if category in {"new_order", "calendar"}:
            return "normal"
        return "low" if "fyi" in text else "normal"

    def _resolve_action(self, category: str, needs_reply: bool) -> str:
        if category in {"newsletter", "marketing", "banking", "notification"}:
            return "monitor_only"
        if category == "invoice":
            return "create_invoice"
        if category == "calendar":
            return "create_calendar_event"
        if category in {"new_order", "task"}:
            return "create_task"
        if needs_reply:
            return "draft_email_reply"
        return "monitor_only"

    def _normalize(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode(
            "ascii", "ignore"
        ).decode("ascii")
        return normalized.lower()
