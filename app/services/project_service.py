from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import EmailModel, InvoiceModel, ProjectModel, ProjectTimelineEventModel, TaskModel, WorkLogModel
from app.schemas.entities import Project


class ProjectService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def create_project(
        self,
        name: str,
        description: str = "",
        *,
        status: str = "new",
        code: str = "",
        customer_name: str = "",
        contact_person: str = "",
        contact_email: str = "",
        contact_phone: str = "",
        address: str = "",
        priority: str = "normal",
        planned_start_at: str | None = None,
        planned_end_at: str | None = None,
        actual_start_at: str | None = None,
        actual_end_at: str | None = None,
        budget_amount: float | None = None,
        notes: str = "",
        internal_notes: str = "",
    ) -> int:
        project = Project(
            name=name.strip(),
            description=description.strip(),
            status=status,
            code=code.strip(),
            customer_name=customer_name.strip(),
            contact_person=contact_person.strip(),
            contact_email=contact_email.strip(),
            contact_phone=contact_phone.strip(),
            address=address.strip(),
            priority=priority,
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
            actual_start_at=actual_start_at,
            actual_end_at=actual_end_at,
            budget_amount=budget_amount,
            notes=notes.strip(),
            internal_notes=internal_notes.strip(),
        )
        return crud.create_project(self.config, project)

    def list_projects(self) -> Sequence[ProjectModel]:
        return crud.list_projects(self.config)

    def get_project(self, project_id: int) -> ProjectModel | None:
        return crud.get_project(self.config, project_id)

    def get_or_create_project(self, name: str) -> ProjectModel | None:
        normalized_name = name.strip()
        if not normalized_name:
            return None

        existing = crud.find_project_by_name(self.config, normalized_name)
        if existing is not None:
            return existing

        project_id = self.create_project(normalized_name)
        return crud.get_project(self.config, project_id)

    def assign_email(self, email_id: str, project_id: int | None) -> bool:
        if project_id is None:
            return crud.update_email_project_id(self.config, email_id, None)
        return crud.add_email_project_link(self.config, email_id, project_id)

    def clear_email_assignments(self, email_id: str) -> bool:
        return crud.clear_email_project_links(self.config, email_id)

    def delete_project(self, project_id: int) -> bool:
        return crud.delete_project(self.config, project_id)

    def assign_task(self, task_id: int, project_id: int | None) -> bool:
        return crud.update_task_project_id(self.config, task_id, project_id)

    def assign_invoice(self, invoice_id: int, project_id: int | None) -> bool:
        return crud.update_invoice_project_id(self.config, invoice_id, project_id)

    def update_status(self, project_id: int, status: str) -> bool:
        return crud.update_project_status(self.config, project_id, status)

    def update_description(self, project_id: int, description: str) -> bool:
        return crud.update_project_description(self.config, project_id, description)

    def update_project(
        self,
        project_id: int,
        *,
        name: str,
        description: str,
        status: str,
        code: str = "",
        customer_name: str = "",
        contact_person: str = "",
        contact_email: str = "",
        contact_phone: str = "",
        address: str = "",
        priority: str = "normal",
        planned_start_at: str | None = None,
        planned_end_at: str | None = None,
        actual_start_at: str | None = None,
        actual_end_at: str | None = None,
        budget_amount: float | None = None,
        notes: str = "",
        internal_notes: str = "",
    ) -> bool:
        existing = crud.get_project(self.config, project_id)
        updated = crud.update_project_details(
            self.config,
            project_id,
            name=name.strip(),
            description=description.strip(),
            status=status,
            code=code.strip(),
            customer_name=customer_name.strip(),
            contact_person=contact_person.strip(),
            contact_email=contact_email.strip(),
            contact_phone=contact_phone.strip(),
            address=address.strip(),
            priority=priority,
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
            actual_start_at=actual_start_at,
            actual_end_at=actual_end_at,
            budget_amount=budget_amount,
            notes=notes.strip(),
            internal_notes=internal_notes.strip(),
        )
        if updated and existing is not None and existing.status != status:
            crud.create_project_timeline_event(
                self.config,
                project_id=project_id,
                event_type="project_status",
                title="Změna stavu zakázky",
                details=f"{existing.status} -> {status}",
            )
        return updated

    def get_project_summary(
        self,
        project_id: int,
    ) -> tuple[list[EmailModel], list[TaskModel], list[InvoiceModel], list[WorkLogModel], list[ProjectTimelineEventModel]]:
        project_email_ids = set(crud.list_project_email_ids(self.config, project_id))
        emails = [item for item in crud.list_emails(self.config) if item.id in project_email_ids]
        tasks = [item for item in crud.list_tasks(self.config) if item.project_id == project_id]
        invoices = [
            item for item in crud.list_invoices(self.config) if item.project_id == project_id
        ]
        work_logs = list(crud.list_work_logs(self.config, project_id=project_id))
        timeline_events = list(crud.list_project_timeline_events(self.config, project_id))
        return emails, tasks, invoices, work_logs, timeline_events

    def get_project_finance_summary(self, project_id: int) -> dict[str, float]:
        _, _, invoices, work_logs, _ = self.get_project_summary(project_id)
        workers = {item.id: item for item in crud.list_workers(self.config)}

        def resolve_payout_amount(work_log: WorkLogModel) -> float:
            if work_log.payout_amount is not None:
                return float(work_log.payout_amount)
            worker = workers.get(work_log.worker_id)
            if worker is None:
                return 0.0
            rate = None
            if worker.payout_rate is not None and float(worker.payout_rate) > 0:
                rate = float(worker.payout_rate)
            elif worker.hourly_rate is not None and float(worker.hourly_rate) > 0:
                rate = float(worker.hourly_rate)
            if rate is None:
                return 0.0
            return float(work_log.hours or 0) * float(rate) + float(work_log.material_cost or 0)

        invoice_total = sum(item.amount or 0 for item in invoices)
        payout_total = sum(resolve_payout_amount(item) for item in work_logs)
        payout_paid_total = sum(
            resolve_payout_amount(item) for item in work_logs if item.payment_status == "paid"
        )
        payout_unpaid_total = sum(
            resolve_payout_amount(item) for item in work_logs if item.payment_status != "paid"
        )
        material_total = sum(item.material_cost or 0 for item in work_logs)
        labor_hours = sum(item.hours for item in work_logs)

        return {
            "invoice_total": round(invoice_total, 2),
            "payout_total": round(payout_total, 2),
            "payout_paid_total": round(payout_paid_total, 2),
            "payout_unpaid_total": round(payout_unpaid_total, 2),
            "material_total": round(material_total, 2),
            "labor_hours": round(labor_hours, 2),
            "balance": round(invoice_total - payout_total - material_total, 2),
        }
