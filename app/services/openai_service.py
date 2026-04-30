from __future__ import annotations

import json
from typing import Any

from app.config import AppConfig
from app.schemas.entities import Email
from app.utils.logger import get_logger


logger = get_logger(__name__)


class OpenAIService:
    MAX_BODY_CHARS = 4000

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def is_configured(self) -> bool:
        return bool(self.config.openai_api_key)

    def triage_email(self, email: Email) -> dict[str, Any] | None:
        if not self.is_configured():
            return None

        client_cls = self._import_openai_client()
        if client_cls is None:
            return None

        openai_error_types = self._import_openai_errors()
        client = client_cls(api_key=self.config.openai_api_key, max_retries=0)

        try:
            response = client.responses.create(
                model=self.config.openai_model,
                reasoning={"effort": self.config.openai_reasoning_effort},
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": self._system_prompt(),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": self._build_user_prompt(email),
                            }
                        ],
                    },
                ],
            )
        except openai_error_types as exc:
            logger.warning("OpenAI triage unavailable, using fallback: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Unexpected OpenAI triage failure, using fallback: %s", exc)
            return None

        return self._parse_json_response(response.output_text)

    def _system_prompt(self) -> str:
        return (
            "You are an AI email triage assistant for a local work agent. "
            "Read the email and return one valid JSON object only. "
            "Never recommend deleting an email. "
            "Choose a primary action from: monitor_only, create_task, create_invoice, "
            "create_calendar_event, draft_email_reply. "
            "Choose a category from: uncategorized, task, new_order, invoice, calendar, "
            "newsletter, marketing, notification, banking. "
            "Choose a priority from: low, normal, high. "
            "Return concise, practical outputs for business workflow automation."
        )

    def _build_user_prompt(self, email: Email) -> str:
        attachment_names = ", ".join(email.attachments) if email.attachments else "none"
        body_preview = email.body[: self.MAX_BODY_CHARS]
        return (
            "Analyze this email and return JSON with exactly these keys:\n"
            "{\n"
            '  "category": string,\n'
            '  "action": string,\n'
            '  "priority": string,\n'
            '  "needs_reply": boolean,\n'
            '  "confidence": number,\n'
            '  "summary": string,\n'
            '  "customer_name": string,\n'
            '  "company_name": string,\n'
            '  "contact": string,\n'
            '  "address": string,\n'
            '  "requested_deadline": string,\n'
            '  "requested_action": string,\n'
            '  "invoice_number": string,\n'
            '  "invoice_amount": number,\n'
            '  "invoice_currency": string,\n'
            '  "invoice_due_date": string,\n'
            '  "suggested_actions": array of strings,\n'
            '  "draft_reply": string\n'
            "}\n\n"
            f"Sender: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Received at: {email.received_at}\n"
            f"Attachments: {attachment_names}\n"
            f"Body:\n{body_preview}\n"
        )

    def _parse_json_response(self, raw_text: str) -> dict[str, Any] | None:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, dict) else None

    def _import_openai_client(self) -> object | None:
        try:
            from openai import OpenAI
        except ImportError:
            return None

        return OpenAI

    def _import_openai_errors(self) -> tuple[type[BaseException], ...]:
        try:
            from openai import APIConnectionError, APIError, RateLimitError
        except ImportError:
            return (Exception,)

        return (APIConnectionError, APIError, RateLimitError)
