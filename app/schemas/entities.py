from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Email:
    id: str
    subject: str
    sender: str
    body: str
    received_at: str
    thread_id: str = ""
    attachments: list[str] = field(default_factory=list)
    category: str = "uncategorized"
    priority: str = "normal"
    project_id: int | None = None


@dataclass(slots=True)
class ParsedEmail:
    subject: str
    sender: str
    summary: str
    category: str
    customer_name: str = ""
    company_name: str = ""
    contact: str = ""
    address: str = ""
    requested_deadline: str | None = None
    requested_action: str = ""
    invoice_number: str = ""
    invoice_amount: float | None = None
    invoice_currency: str = "CZK"
    invoice_due_date: str | None = None
    attachments: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    draft_reply: str = ""


@dataclass(slots=True)
class EmailClassification:
    category: str
    action: str
    priority: str
    needs_reply: bool
    confidence: float


@dataclass(slots=True)
class Task:
    title: str
    description: str = ""
    priority: str = "normal"
    status: str = "pending"
    due_date: str | None = None
    deadline_at: str | None = None
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    source_email_id: str | None = None
    project_id: int | None = None
    assigned_worker_id: int | None = None
    estimated_hours: float | None = None
    completed_at: str | None = None
    completed_by_user_id: int | None = None


@dataclass(slots=True)
class CalendarEvent:
    title: str
    starts_at: str
    ends_at: str
    description: str = ""
    location: str = ""
    status: str = "proposed"
    source_email_id: str | None = None
    task_id: int | None = None
    project_id: int | None = None
    assigned_worker_id: int | None = None
    attendee_emails: list[str] = field(default_factory=list)
    calendar_id: str = ""
    external_event_id: str = ""


@dataclass(slots=True)
class Invoice:
    supplier: str
    invoice_number: str = ""
    amount: float | None = None
    currency: str = "CZK"
    due_date: str | None = None
    status: str = "detected"
    source_email_id: str | None = None
    attachment_path: str = ""
    project_id: int | None = None


@dataclass(slots=True)
class Project:
    name: str
    description: str = ""
    status: str = "new"
    code: str = ""
    customer_name: str = ""
    contact_person: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    address: str = ""
    priority: str = "normal"
    planned_start_at: str | None = None
    planned_end_at: str | None = None
    actual_start_at: str | None = None
    actual_end_at: str | None = None
    budget_amount: float | None = None
    notes: str = ""
    internal_notes: str = ""


@dataclass(slots=True)
class Worker:
    full_name: str
    role: str = ""
    email: str = ""
    phone: str = ""
    hourly_rate: float | None = None
    payout_rate: float | None = None
    status: str = "active"


@dataclass(slots=True)
class ProjectWorkerRate:
    project_id: int
    worker_id: int
    payout_rate: float | None = None


@dataclass(slots=True)
class User:
    email: str
    password_hash: str
    full_name: str
    role: str = "worker"
    worker_id: int | None = None
    status: str = "active"


@dataclass(slots=True)
class WorkLog:
    project_id: int
    worker_id: int
    work_date: str
    hours: float
    notes: str = ""
    starts_at: str | None = None
    ends_at: str | None = None
    travel_km: float = 0.0
    material_cost: float = 0.0
    payout_amount: float | None = None
    billable_amount: float | None = None
    payment_status: str = "unpaid"
    paid_at: str | None = None


@dataclass(slots=True)
class ProjectDocument:
    project_id: int
    title: str
    file_path: str
    document_type: str = "general"
    source_email_id: str | None = None
    worker_id: int | None = None
    work_date: str | None = None


@dataclass(slots=True)
class Reminder:
    title: str
    remind_at: str
    notes: str = ""
    related_type: str = ""
    related_id: str = ""
    status: str = "pending"


@dataclass(slots=True)
class ApprovalItem:
    action_type: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    source_email_id: str | None = None
    reason: str = ""


@dataclass(slots=True)
class EmailProcessingResult:
    email: Email
    classification: EmailClassification
    parsed_email: ParsedEmail
    approval_ids: list[int] = field(default_factory=list)
    reminder_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class AgentCycleResult:
    checked_emails: int = 0
    pending_approvals: int = 0
    due_reminders: int = 0
    notifications_sent: int = 0


EmailMessage = Email
TaskEntity = Task
ReminderEntity = Reminder
