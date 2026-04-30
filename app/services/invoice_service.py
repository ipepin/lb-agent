from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import InvoiceModel
from app.integrations.idoklad_api import IDokladApiClient
from app.schemas.entities import Invoice


class InvoiceService:
    def __init__(
        self,
        config: AppConfig,
        client: IDokladApiClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or IDokladApiClient()

    def sync(self) -> None:
        self.client.sync()

    def create_invoice(
        self,
        supplier: str,
        invoice_number: str = "",
        amount: float | None = None,
        currency: str = "CZK",
        due_date: str | None = None,
        source_email_id: str | None = None,
        attachment_path: str = "",
        project_id: int | None = None,
    ) -> int:
        invoice = Invoice(
            supplier=supplier,
            invoice_number=invoice_number,
            amount=amount,
            currency=currency,
            due_date=due_date,
            source_email_id=source_email_id,
            attachment_path=attachment_path,
            project_id=project_id,
        )
        return crud.create_invoice(self.config, invoice)

    def list_invoices(self) -> Sequence[InvoiceModel]:
        return crud.list_invoices(self.config)

    def backfill_attachment_paths(self) -> int:
        updated_count = 0

        for invoice in crud.list_invoices(self.config):
            if invoice.attachment_path or not invoice.source_email_id:
                continue

            email = crud.get_email(self.config, invoice.source_email_id)
            if email is None:
                continue

            pdf_attachment = next(
                (
                    attachment
                    for attachment in email.attachments
                    if attachment.lower().endswith(".pdf")
                ),
                "",
            )
            if not pdf_attachment:
                continue

            updated = crud.update_invoice_attachment_path(
                self.config,
                invoice.id,
                pdf_attachment,
            )
            if updated:
                updated_count += 1

        return updated_count
