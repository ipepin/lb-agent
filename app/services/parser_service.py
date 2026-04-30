from __future__ import annotations

import re
import unicodedata

from app.schemas.entities import Email, EmailClassification, ParsedEmail
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.text_utils import cleanup_email_text


class ParserService:
    def parse_message(
        self,
        message: Email,
        classification: EmailClassification | None = None,
    ) -> ParsedEmail:
        cleaned_body = cleanup_email_text(message.body)
        attachment_text = self._extract_attachment_text(message.attachments)
        parse_source = cleaned_body
        if attachment_text:
            parse_source = f"{cleaned_body}\n{attachment_text}".strip()

        summary = self._build_summary(cleaned_body)
        contact = self._extract_contact_name(message.sender)
        company_name = self._extract_company_name(message.sender, parse_source)
        customer_name = self._extract_labeled_value(
            parse_source, ("customer", "zakaznik", "client")
        )
        address = self._extract_labeled_value(
            parse_source, ("address", "adresa", "misto realizace")
        )
        requested_deadline = self._extract_labeled_value(
            parse_source, ("deadline", "termin", "pozadovany termin", "due date")
        )
        invoice_due_date = self._extract_labeled_value(
            parse_source, ("splatnost", "due date", "payment due", "datum splatnosti")
        )
        invoice_number = self._extract_invoice_number(parse_source)
        invoice_amount, invoice_currency = self._extract_amount(parse_source)
        category = classification.category if classification else "unknown"

        return ParsedEmail(
            subject=message.subject,
            sender=message.sender,
            summary=summary[:200],
            category=category,
            customer_name=customer_name or "",
            company_name=company_name,
            contact=contact,
            address=address or "",
            requested_deadline=requested_deadline,
            requested_action=self._resolve_requested_action(category, message.body),
            invoice_number=invoice_number,
            invoice_amount=invoice_amount,
            invoice_currency=invoice_currency,
            invoice_due_date=invoice_due_date,
            attachments=list(message.attachments),
        )

    def _build_summary(self, body: str) -> str:
        cleaned_body = cleanup_email_text(body)
        non_empty_lines = [line.strip() for line in cleaned_body.splitlines() if line.strip()]
        return " ".join(non_empty_lines[:2]) if non_empty_lines else ""

    def _extract_labeled_value(self, body: str, labels: tuple[str, ...]) -> str | None:
        for raw_line in body.splitlines():
            if ":" not in raw_line:
                continue
            key, value = raw_line.split(":", 1)
            if self._normalize(key).strip() in labels and value.strip():
                return value.strip()
        return None

    def _extract_contact_name(self, sender: str) -> str:
        match = re.match(r"\s*([^<]+)", sender)
        if not match:
            return sender.strip()
        return match.group(1).strip().strip('"')

    def _extract_company_name(self, sender: str, body: str) -> str:
        explicit_company = self._extract_labeled_value(
            body, ("company", "firma", "dodavatel")
        )
        if explicit_company:
            return explicit_company

        email_match = re.search(r"@([A-Za-z0-9.-]+)", sender)
        if not email_match:
            return ""

        domain = email_match.group(1).split(".")[0]
        return domain.replace("-", " ").replace("_", " ").title()

    def _extract_invoice_number(self, body: str) -> str:
        patterns = (
            r"(?:invoice|faktura)\s*(?:no|number|cislo|c)?\.?\s*[:#]?\s*([A-Za-z0-9/-]+)",
            r"(?:cislo faktury|invoice no|invoice number)\s*[:#]?\s*([A-Za-z0-9/-]+)",
            r"(?:vs|variabilni symbol)\s*[:#]?\s*([A-Za-z0-9/-]+)",
            r"(?:evidencni cislo|doklad)\s*[:#]?\s*([A-Za-z0-9/-]+)",
        )
        normalized_body = self._normalize(body)
        for pattern in patterns:
            match = re.search(pattern, normalized_body, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_amount(self, body: str) -> tuple[float | None, str]:
        normalized_body = self._normalize(body)
        prioritized_patterns = (
            r"(?:celkem k uhrade|castka k uhrade|k uhrade|celkova castka|celkem|total due|amount due|grand total|invoice total)\s*[:=]?\s*(\d[\d\s.,]*)\s*(kc|czk|eur|usd)",
            r"(?:amount|castka|price)\s*[:=]?\s*(\d[\d\s.,]*)\s*(kc|czk|eur|usd)",
            r"(\d[\d\s.,]*)\s*(kc|czk|eur|usd)",
        )
        match = None
        for pattern in prioritized_patterns:
            match = re.search(pattern, normalized_body, flags=re.IGNORECASE)
            if match:
                break
        if match is None:
            return None, "CZK"

        raw_amount = match.group(1).replace(" ", "")
        if "," in raw_amount and "." in raw_amount:
            if raw_amount.rfind(",") > raw_amount.rfind("."):
                raw_amount = raw_amount.replace(".", "").replace(",", ".")
            else:
                raw_amount = raw_amount.replace(",", "")
        else:
            raw_amount = raw_amount.replace(",", ".")

        try:
            amount = float(raw_amount)
        except ValueError:
            return None, match.group(2).upper()

        currency = "CZK" if match.group(2).lower() == "kc" else match.group(2).upper()
        return amount, currency

    def _extract_attachment_text(self, attachments: list[str]) -> str:
        parts: list[str] = []
        for attachment in attachments:
            if not attachment.lower().endswith(".pdf"):
                continue
            pdf_text = extract_text_from_pdf(attachment)
            cleaned_pdf_text = cleanup_email_text(pdf_text)
            if cleaned_pdf_text:
                parts.append(cleaned_pdf_text)
        return "\n".join(parts).strip()

    def _resolve_requested_action(self, category: str, body: str) -> str:
        normalized = self._normalize(body)
        if category == "invoice":
            return "review_invoice"
        if category == "calendar":
            return "schedule_meeting"
        if category == "new_order":
            return "prepare_offer"
        if "zavolat" in normalized or "call" in normalized:
            return "call_back"
        if "odpoved" in normalized or "reply" in normalized:
            return "draft_reply"
        if "poslat" in normalized or "send" in normalized:
            return "send_documents"
        return "review"

    def _normalize(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode(
            "ascii", "ignore"
        ).decode("ascii")
        return normalized.lower()
