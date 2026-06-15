from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TaskModel:
    id: int
    title: str
    description: str
    priority: str
    status: str
    due_date: str | None
    source_email_id: str | None
    project_id: int | None
    assigned_worker_id: int | None
    worker_ids: list[int]
    estimated_hours: float | None
    completed_at: str | None
    completed_by_user_id: int | None
    created_at: str


@dataclass(slots=True)
class ReminderModel:
    id: int
    title: str
    remind_at: str
    notes: str
    related_type: str
    related_id: str
    status: str
    created_at: str


@dataclass(slots=True)
class EmailModel:
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    received_at: str
    category: str
    priority: str
    status: str
    attachments: list[str]
    summary: str
    project_id: int | None
    ai_payload: dict[str, Any]


@dataclass(slots=True)
class InvoiceModel:
    id: int
    supplier: str
    invoice_number: str
    amount: float | None
    currency: str
    due_date: str | None
    status: str
    source_email_id: str | None
    attachment_path: str
    project_id: int | None
    created_at: str


@dataclass(slots=True)
class ProjectModel:
    id: int
    name: str
    description: str
    status: str
    code: str
    customer_name: str
    contact_person: str
    contact_email: str
    contact_phone: str
    address: str
    priority: str
    planned_start_at: str | None
    planned_end_at: str | None
    actual_start_at: str | None
    actual_end_at: str | None
    budget_amount: float | None
    notes: str
    internal_notes: str
    created_at: str


@dataclass(slots=True)
class WorkerModel:
    id: int
    full_name: str
    role: str
    email: str
    phone: str
    hourly_rate: float | None
    payout_rate: float | None
    status: str
    created_at: str


@dataclass(slots=True)
class ProjectWorkerRateModel:
    project_id: int
    worker_id: int
    payout_rate: float | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class UserModel:
    id: int
    email: str
    password_hash: str
    full_name: str
    role: str
    worker_id: int | None
    status: str
    created_at: str


@dataclass(slots=True)
class WorkLogModel:
    id: int
    project_id: int
    worker_id: int
    work_date: str
    hours: float
    notes: str
    starts_at: str | None
    ends_at: str | None
    travel_km: float
    material_cost: float
    payout_amount: float | None
    billable_amount: float | None
    payment_status: str
    paid_at: str | None
    created_at: str


@dataclass(slots=True)
class ProjectTimelineEventModel:
    id: int
    project_id: int
    event_type: str
    title: str
    details: str
    created_at: str


@dataclass(slots=True)
class ProjectDocumentModel:
    id: int
    project_id: int
    title: str
    file_path: str
    document_type: str
    source_email_id: str | None
    worker_id: int | None
    work_date: str | None
    created_at: str


@dataclass(slots=True)
class CalendarEventModel:
    id: int
    title: str
    starts_at: str
    ends_at: str
    description: str
    location: str
    status: str
    source_email_id: str | None
    task_id: int | None
    project_id: int | None
    assigned_worker_id: int | None
    attendee_emails: list[str]
    calendar_id: str
    external_event_id: str
    created_at: str


@dataclass(slots=True)
class ApprovalItemModel:
    id: int
    action_type: str
    title: str
    payload: dict[str, Any]
    status: str
    source_email_id: str | None
    reason: str
    created_at: str
