from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import ApprovalItemModel
from app.services.calendar_service import CalendarService
from app.services.invoice_service import InvoiceService
from app.services.task_service import TaskService
from app.schemas.entities import ApprovalItem, Email, EmailClassification, ParsedEmail


class ApprovalService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.task_service = TaskService(config)
        self.invoice_service = InvoiceService(config)
        self.calendar_service = CalendarService(config)

    def requires_manual_approval(self, action_name: str) -> bool:
        sensitive_actions = {
            "send_email",
            "create_invoice",
            "delete_task",
            "create_calendar_event",
        }
        return action_name in sensitive_actions

    def build_approval_items(
        self,
        email: Email,
        classification: EmailClassification,
        parsed_email: ParsedEmail,
    ) -> list[ApprovalItem]:
        items: list[ApprovalItem] = []

        if classification.action == "create_task":
            items.append(
                ApprovalItem(
                    action_type="create_task",
                    title=f"Create task from email: {email.subject}",
                    payload={
                        "title": email.subject,
                        "description": parsed_email.summary,
                        "priority": classification.priority,
                        "due_date": parsed_email.requested_deadline or "",
                        "deadline_at": parsed_email.requested_deadline or "",
                        "suggested_actions": parsed_email.suggested_actions,
                    },
                    source_email_id=email.id,
                    reason="Email contains a request that should become a tracked task.",
                )
            )

        if classification.action == "create_invoice":
            pdf_attachment = next(
                (
                    attachment
                    for attachment in parsed_email.attachments
                    if attachment.lower().endswith(".pdf")
                ),
                "",
            )
            items.append(
                ApprovalItem(
                    action_type="create_invoice",
                    title=f"Register invoice: {parsed_email.invoice_number or email.subject}",
                    payload={
                        "supplier": parsed_email.company_name or parsed_email.contact,
                        "invoice_number": parsed_email.invoice_number,
                        "amount": parsed_email.invoice_amount,
                        "currency": parsed_email.invoice_currency,
                        "due_date": parsed_email.invoice_due_date or "",
                        "attachment_path": pdf_attachment,
                    },
                    source_email_id=email.id,
                    reason="Invoice-like email was detected and should be reviewed first.",
                )
            )

        if classification.action == "create_calendar_event":
            items.append(
                ApprovalItem(
                    action_type="create_calendar_event",
                    title=f"Create calendar proposal: {email.subject}",
                    payload={
                        "title": email.subject,
                        "starts_at": parsed_email.requested_deadline or "",
                        "ends_at": parsed_email.requested_deadline or "",
                        "description": parsed_email.summary,
                        "location": parsed_email.address,
                        "suggested_actions": parsed_email.suggested_actions,
                    },
                    source_email_id=email.id,
                    reason="Email indicates scheduling or a date change.",
                )
            )

        if classification.needs_reply:
            items.append(
                ApprovalItem(
                    action_type="draft_email_reply",
                    title=f"Draft reply for: {email.subject}",
                    payload={
                        "tone": "professional",
                        "summary": parsed_email.summary,
                        "category": classification.category,
                        "draft_reply": parsed_email.draft_reply,
                        "suggested_actions": parsed_email.suggested_actions,
                    },
                    source_email_id=email.id,
                    reason="The sender likely expects a reply.",
                )
            )

        return items

    def save_items(self, items: Sequence[ApprovalItem]) -> list[int]:
        return [crud.create_approval_item(self.config, item) for item in items]

    def list_items(self) -> Sequence[ApprovalItemModel]:
        return crud.list_approval_items(self.config)

    def get_item(self, item_id: int) -> ApprovalItemModel | None:
        return crud.get_approval_item(self.config, item_id)

    def approve_item(self, item_id: int) -> bool:
        item = self.get_item(item_id)
        if item is None or item.status != "pending":
            return False

        self._apply_item(item)
        updated = crud.update_approval_item_status(self.config, item_id, "approved")
        if updated and item.source_email_id:
            crud.update_email_status(self.config, item.source_email_id, "confirmed")
        return updated

    def reject_item(self, item_id: int) -> bool:
        item = self.get_item(item_id)
        if item is None or item.status != "pending":
            return False
        updated = crud.update_approval_item_status(self.config, item_id, "rejected")
        if updated and item.source_email_id:
            crud.update_email_status(self.config, item.source_email_id, "archived")
        return updated

    def _apply_item(self, item: ApprovalItemModel) -> None:
        payload = item.payload
        source_email = crud.get_email(self.config, item.source_email_id) if item.source_email_id else None
        project_id = source_email.project_id if source_email else None

        if item.action_type == "create_task":
            self.task_service.create_task(
                title=str(payload.get("title", item.title)),
                description=str(payload.get("description", "")),
                priority=str(payload.get("priority", "normal")),
                due_date=self._none_if_blank(payload.get("due_date")),
                deadline_at=self._none_if_blank(payload.get("deadline_at")) or self._none_if_blank(payload.get("due_date")),
                source_email_id=item.source_email_id,
                project_id=project_id,
            )
            return

        if item.action_type == "create_invoice":
            amount = self._float_or_none(payload.get("amount"))
            self.invoice_service.create_invoice(
                supplier=str(payload.get("supplier", "")),
                invoice_number=str(payload.get("invoice_number", "")),
                amount=amount,
                currency=str(payload.get("currency", "CZK")),
                due_date=self._none_if_blank(payload.get("due_date")),
                source_email_id=item.source_email_id,
                attachment_path=str(payload.get("attachment_path", "")),
                project_id=project_id,
            )
            return

        if item.action_type == "create_calendar_event":
            starts_at = self._none_if_blank(payload.get("starts_at")) or ""
            ends_at = self._none_if_blank(payload.get("ends_at")) or starts_at
            self.calendar_service.create_event_proposal(
                title=str(payload.get("title", item.title)),
                starts_at=starts_at,
                ends_at=ends_at,
                description=str(payload.get("description", "")),
                location=str(payload.get("location", "")),
                source_email_id=item.source_email_id,
            )
            return

        if item.action_type == "draft_email_reply":
            return

    def _none_if_blank(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _float_or_none(self, value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
