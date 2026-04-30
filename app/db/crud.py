from __future__ import annotations

import json
import sqlite3
from typing import Sequence

from app.config import AppConfig
from app.db.database import get_connection
from app.db.models import (
    ApprovalItemModel,
    CalendarEventModel,
    EmailModel,
    InvoiceModel,
    ProjectModel,
    ProjectDocumentModel,
    ProjectTimelineEventModel,
    ReminderModel,
    TaskModel,
    UserModel,
    WorkerModel,
    WorkLogModel,
)
from app.schemas.entities import (
    ApprovalItem,
    CalendarEvent,
    Email,
    Invoice,
    Project,
    ProjectDocument,
    Reminder,
    Task,
    User,
    Worker,
    WorkLog,
)
from app.utils.dates import utc_now_iso


def create_task(config: AppConfig, task: Task) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (
                title, description, priority, status, due_date, source_email_id, project_id,
                assigned_worker_id, estimated_hours, completed_at, completed_by_user_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.title,
                task.description,
                task.priority,
                task.status,
                task.due_date,
                task.source_email_id,
                task.project_id,
                task.assigned_worker_id,
                task.estimated_hours,
                task.completed_at,
                task.completed_by_user_id,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def set_task_worker_ids(config: AppConfig, task_id: int, worker_ids: list[int]) -> None:
    unique_worker_ids = list(dict.fromkeys(worker_ids))
    with get_connection(config.db_path) as connection:
        connection.execute(
            """
            DELETE FROM task_workers
            WHERE task_id = ?
            """,
            (task_id,),
        )
        connection.executemany(
            """
            INSERT INTO task_workers (task_id, worker_id, created_at)
            VALUES (?, ?, ?)
            """,
            [(task_id, worker_id, utc_now_iso()) for worker_id in unique_worker_ids],
        )
        connection.commit()


def list_task_worker_ids(config: AppConfig) -> dict[int, list[int]]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT task_id, worker_id
            FROM task_workers
            ORDER BY task_id, rowid
            """
        ).fetchall()

    grouped: dict[int, list[int]] = {}
    for row in rows:
        grouped.setdefault(int(row["task_id"]), []).append(int(row["worker_id"]))
    return grouped


def list_tasks(config: AppConfig) -> Sequence[TaskModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, description, priority, status, due_date, source_email_id,
                   project_id, assigned_worker_id, estimated_hours, completed_at, completed_by_user_id, created_at
            FROM tasks
            ORDER BY created_at DESC
            """
        ).fetchall()

    task_worker_ids = list_task_worker_ids(config)

    return [
        TaskModel(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            status=row["status"],
            due_date=row["due_date"],
            source_email_id=row["source_email_id"],
            project_id=row["project_id"],
            assigned_worker_id=row["assigned_worker_id"],
            worker_ids=task_worker_ids.get(
                row["id"],
                [row["assigned_worker_id"]] if row["assigned_worker_id"] is not None else [],
            ),
            estimated_hours=row["estimated_hours"],
            completed_at=row["completed_at"],
            completed_by_user_id=row["completed_by_user_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def create_reminder(config: AppConfig, reminder: Reminder) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO reminders (
                title, remind_at, notes, related_type, related_id, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reminder.title,
                reminder.remind_at,
                reminder.notes,
                reminder.related_type,
                reminder.related_id,
                reminder.status,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_reminders(config: AppConfig) -> Sequence[ReminderModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, remind_at, notes, related_type, related_id, status, created_at
            FROM reminders
            ORDER BY remind_at ASC
            """
        ).fetchall()

    return [
        ReminderModel(
            id=row["id"],
            title=row["title"],
            remind_at=row["remind_at"],
            notes=row["notes"],
            related_type=row["related_type"],
            related_id=row["related_id"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def create_email(config: AppConfig, email: Email, summary: str = "") -> str:
    with get_connection(config.db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO emails (
                id, thread_id, sender, subject, body, received_at,
                category, priority, status, attachments_json, summary, project_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email.id,
                email.thread_id,
                email.sender,
                email.subject,
                email.body,
                email.received_at,
                email.category,
                email.priority,
                "processed",
                json.dumps(email.attachments, ensure_ascii=True),
                summary,
                email.project_id,
            ),
        )
        if email.project_id is not None:
            connection.execute(
                """
                INSERT OR IGNORE INTO email_project_links (email_id, project_id, created_at)
                VALUES (?, ?, ?)
                """,
                (email.id, email.project_id, utc_now_iso()),
            )
        connection.commit()
        return email.id


def list_emails(config: AppConfig) -> Sequence[EmailModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, thread_id, sender, subject, body, received_at,
                   category, priority, status, attachments_json, summary, project_id
            FROM emails
            ORDER BY received_at DESC
            """
        ).fetchall()

    return [
        EmailModel(
            id=row["id"],
            thread_id=row["thread_id"],
            sender=row["sender"],
            subject=row["subject"],
            body=row["body"],
            received_at=row["received_at"],
            category=row["category"],
            priority=row["priority"],
            status=row["status"],
            attachments=json.loads(row["attachments_json"] or "[]"),
            summary=row["summary"],
            project_id=row["project_id"],
        )
        for row in rows
    ]


def get_email(config: AppConfig, email_id: str) -> EmailModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, thread_id, sender, subject, body, received_at,
                   category, priority, status, attachments_json, summary, project_id
            FROM emails
            WHERE id = ?
            """,
            (email_id,),
        ).fetchone()

    if row is None:
        return None

    return EmailModel(
        id=row["id"],
        thread_id=row["thread_id"],
        sender=row["sender"],
        subject=row["subject"],
        body=row["body"],
        received_at=row["received_at"],
        category=row["category"],
        priority=row["priority"],
        status=row["status"],
        attachments=json.loads(row["attachments_json"] or "[]"),
        summary=row["summary"],
        project_id=row["project_id"],
    )


def create_invoice(config: AppConfig, invoice: Invoice) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO invoices (
                supplier, invoice_number, amount, currency, due_date, status,
                source_email_id, attachment_path, project_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice.supplier,
                invoice.invoice_number,
                invoice.amount,
                invoice.currency,
                invoice.due_date,
                invoice.status,
                invoice.source_email_id,
                invoice.attachment_path,
                invoice.project_id,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_invoices(config: AppConfig) -> Sequence[InvoiceModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, supplier, invoice_number, amount, currency, due_date, status,
                   source_email_id, attachment_path, project_id, created_at
            FROM invoices
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        InvoiceModel(
            id=row["id"],
            supplier=row["supplier"],
            invoice_number=row["invoice_number"],
            amount=row["amount"],
            currency=row["currency"],
            due_date=row["due_date"],
            status=row["status"],
            source_email_id=row["source_email_id"],
            attachment_path=row["attachment_path"],
            project_id=row["project_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def create_project(config: AppConfig, project: Project) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO projects (
                name, description, status, code, customer_name, contact_person, contact_email,
                contact_phone, address, priority, planned_start_at, planned_end_at,
                actual_start_at, actual_end_at, budget_amount, notes, internal_notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.name,
                project.description,
                project.status,
                project.code,
                project.customer_name,
                project.contact_person,
                project.contact_email,
                project.contact_phone,
                project.address,
                project.priority,
                project.planned_start_at,
                project.planned_end_at,
                project.actual_start_at,
                project.actual_end_at,
                project.budget_amount,
                project.notes,
                project.internal_notes,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_projects(config: AppConfig) -> Sequence[ProjectModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, name, description, status, code, customer_name, contact_person,
                   contact_email, contact_phone, address, priority, planned_start_at,
                   planned_end_at, actual_start_at, actual_end_at, budget_amount,
                   notes, internal_notes, created_at
            FROM projects
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        ProjectModel(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            code=row["code"],
            customer_name=row["customer_name"],
            contact_person=row["contact_person"],
            contact_email=row["contact_email"],
            contact_phone=row["contact_phone"],
            address=row["address"],
            priority=row["priority"],
            planned_start_at=row["planned_start_at"],
            planned_end_at=row["planned_end_at"],
            actual_start_at=row["actual_start_at"],
            actual_end_at=row["actual_end_at"],
            budget_amount=row["budget_amount"],
            notes=row["notes"],
            internal_notes=row["internal_notes"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_project(config: AppConfig, project_id: int) -> ProjectModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, name, description, status, code, customer_name, contact_person,
                   contact_email, contact_phone, address, priority, planned_start_at,
                   planned_end_at, actual_start_at, actual_end_at, budget_amount,
                   notes, internal_notes, created_at
            FROM projects
            WHERE id = ?
            """,
            (project_id,),
        ).fetchone()

    if row is None:
        return None

    return ProjectModel(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        status=row["status"],
        code=row["code"],
        customer_name=row["customer_name"],
        contact_person=row["contact_person"],
        contact_email=row["contact_email"],
        contact_phone=row["contact_phone"],
        address=row["address"],
        priority=row["priority"],
        planned_start_at=row["planned_start_at"],
        planned_end_at=row["planned_end_at"],
        actual_start_at=row["actual_start_at"],
        actual_end_at=row["actual_end_at"],
        budget_amount=row["budget_amount"],
        notes=row["notes"],
        internal_notes=row["internal_notes"],
        created_at=row["created_at"],
    )


def find_project_by_name(config: AppConfig, name: str) -> ProjectModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, name, description, status, code, customer_name, contact_person,
                   contact_email, contact_phone, address, priority, planned_start_at,
                   planned_end_at, actual_start_at, actual_end_at, budget_amount,
                   notes, internal_notes, created_at
            FROM projects
            WHERE lower(name) = lower(?)
            """,
            (name,),
        ).fetchone()

    if row is None:
        return None

    return ProjectModel(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        status=row["status"],
        code=row["code"],
        customer_name=row["customer_name"],
        contact_person=row["contact_person"],
        contact_email=row["contact_email"],
        contact_phone=row["contact_phone"],
        address=row["address"],
        priority=row["priority"],
        planned_start_at=row["planned_start_at"],
        planned_end_at=row["planned_end_at"],
        actual_start_at=row["actual_start_at"],
        actual_end_at=row["actual_end_at"],
        budget_amount=row["budget_amount"],
        notes=row["notes"],
        internal_notes=row["internal_notes"],
        created_at=row["created_at"],
    )


def update_invoice_attachment_path(
    config: AppConfig,
    invoice_id: int,
    attachment_path: str,
) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE invoices
            SET attachment_path = ?
            WHERE id = ?
            """,
            (attachment_path, invoice_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_email_project_id(config: AppConfig, email_id: str, project_id: int | None) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE emails
            SET project_id = ?
            WHERE id = ?
            """,
            (project_id, email_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def add_email_project_link(config: AppConfig, email_id: str, project_id: int) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO email_project_links (email_id, project_id, created_at)
            VALUES (?, ?, ?)
            """,
            (email_id, project_id, utc_now_iso()),
        )
        connection.execute(
            """
            UPDATE emails
            SET project_id = COALESCE(project_id, ?)
            WHERE id = ?
            """,
            (project_id, email_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def list_email_project_ids(config: AppConfig, email_id: str) -> list[int]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT project_id
            FROM email_project_links
            WHERE email_id = ?
            ORDER BY created_at ASC
            """,
            (email_id,),
        ).fetchall()
    return [int(row["project_id"]) for row in rows]


def list_project_email_ids(config: AppConfig, project_id: int) -> list[str]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT email_id
            FROM email_project_links
            WHERE project_id = ?
            ORDER BY created_at ASC
            """,
            (project_id,),
        ).fetchall()
    return [str(row["email_id"]) for row in rows]


def clear_email_project_links(config: AppConfig, email_id: str) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM email_project_links
            WHERE email_id = ?
            """,
            (email_id,),
        )
        connection.execute(
            """
            UPDATE emails
            SET project_id = NULL
            WHERE id = ?
            """,
            (email_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_email_category(config: AppConfig, email_id: str, category: str) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE emails
            SET category = ?
            WHERE id = ?
            """,
            (category, email_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_email_status(config: AppConfig, email_id: str, status: str) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE emails
            SET status = ?
            WHERE id = ?
            """,
            (status, email_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_task_project_id(config: AppConfig, task_id: int, project_id: int | None) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET project_id = ?
            WHERE id = ?
            """,
            (project_id, task_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_task(
    config: AppConfig,
    task_id: int,
    *,
    title: str,
    description: str,
    priority: str,
    status: str,
    due_date: str | None,
    project_id: int | None,
    assigned_worker_id: int | None,
    estimated_hours: float | None,
    completed_by_user_id: int | None = None,
) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, priority = ?, status = ?, due_date = ?, project_id = ?,
                assigned_worker_id = ?, estimated_hours = ?,
                completed_at = CASE
                    WHEN ? = 'done' THEN ?
                    WHEN ? IN ('pending', 'waiting', 'planned', 'in_progress', 'scheduled') THEN NULL
                    ELSE completed_at
                END,
                completed_by_user_id = CASE
                    WHEN ? = 'done' THEN ?
                    WHEN ? IN ('pending', 'waiting', 'planned', 'in_progress', 'scheduled') THEN NULL
                    ELSE completed_by_user_id
                END
            WHERE id = ?
            """,
            (
                title,
                description,
                priority,
                status,
                due_date,
                project_id,
                assigned_worker_id,
                estimated_hours,
                status,
                utc_now_iso(),
                status,
                status,
                completed_by_user_id,
                status,
                task_id,
            ),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_task_status(
    config: AppConfig,
    task_id: int,
    status: str,
    completed_by_user_id: int | None = None,
) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = ?,
                completed_at = CASE
                    WHEN ? = 'done' THEN ?
                    WHEN ? IN ('pending', 'waiting', 'planned', 'in_progress', 'scheduled') THEN NULL
                    ELSE completed_at
                END,
                completed_by_user_id = CASE
                    WHEN ? = 'done' THEN ?
                    WHEN ? IN ('pending', 'waiting', 'planned', 'in_progress', 'scheduled') THEN NULL
                    ELSE completed_by_user_id
                END
            WHERE id = ?
            """,
            (
                status,
                status,
                utc_now_iso(),
                status,
                status,
                completed_by_user_id,
                status,
                task_id,
            ),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_invoice_project_id(config: AppConfig, invoice_id: int, project_id: int | None) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE invoices
            SET project_id = ?
            WHERE id = ?
            """,
            (project_id, invoice_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_project_status(config: AppConfig, project_id: int, status: str) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE projects
            SET status = ?
            WHERE id = ?
            """,
            (status, project_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_project_description(config: AppConfig, project_id: int, description: str) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE projects
            SET description = ?
            WHERE id = ?
            """,
            (description, project_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_project_details(
    config: AppConfig,
    project_id: int,
    *,
    name: str,
    description: str,
    status: str,
    code: str,
    customer_name: str,
    contact_person: str,
    contact_email: str,
    contact_phone: str,
    address: str,
    priority: str,
    planned_start_at: str | None,
    planned_end_at: str | None,
    actual_start_at: str | None,
    actual_end_at: str | None,
    budget_amount: float | None,
    notes: str,
    internal_notes: str,
) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE projects
            SET
                name = ?,
                description = ?,
                status = ?,
                code = ?,
                customer_name = ?,
                contact_person = ?,
                contact_email = ?,
                contact_phone = ?,
                address = ?,
                priority = ?,
                planned_start_at = ?,
                planned_end_at = ?,
                actual_start_at = ?,
                actual_end_at = ?,
                budget_amount = ?,
                notes = ?,
                internal_notes = ?
            WHERE id = ?
            """,
            (
                name,
                description,
                status,
                code,
                customer_name,
                contact_person,
                contact_email,
                contact_phone,
                address,
                priority,
                planned_start_at,
                planned_end_at,
                actual_start_at,
                actual_end_at,
                budget_amount,
                notes,
                internal_notes,
                project_id,
            ),
        )
        connection.commit()
        return cursor.rowcount > 0


def create_calendar_event(config: AppConfig, event: CalendarEvent) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO calendar_events (
                title, starts_at, ends_at, description, location, status,
                source_email_id, task_id, project_id, assigned_worker_id, attendee_emails_json,
                calendar_id, external_event_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.title,
                event.starts_at,
                event.ends_at,
                event.description,
                event.location,
                event.status,
                event.source_email_id,
                event.task_id,
                event.project_id,
                event.assigned_worker_id,
                json.dumps(event.attendee_emails, ensure_ascii=True),
                event.calendar_id,
                event.external_event_id,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_calendar_events(config: AppConfig) -> Sequence[CalendarEventModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, starts_at, ends_at, description, location, status,
                   source_email_id, task_id, project_id, assigned_worker_id, attendee_emails_json,
                   calendar_id, external_event_id, created_at
            FROM calendar_events
            ORDER BY starts_at ASC
            """
        ).fetchall()

    return [
        CalendarEventModel(
            id=row["id"],
            title=row["title"],
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            description=row["description"],
            location=row["location"],
            status=row["status"],
            source_email_id=row["source_email_id"],
            task_id=row["task_id"],
            project_id=row["project_id"],
            assigned_worker_id=row["assigned_worker_id"],
            attendee_emails=json.loads(row["attendee_emails_json"] or "[]"),
            calendar_id=row["calendar_id"],
            external_event_id=row["external_event_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_calendar_event(config: AppConfig, event_id: int) -> CalendarEventModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, title, starts_at, ends_at, description, location, status,
                   source_email_id, task_id, project_id, assigned_worker_id, attendee_emails_json,
                   calendar_id, external_event_id, created_at
            FROM calendar_events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

    if row is None:
        return None

    return CalendarEventModel(
        id=row["id"],
        title=row["title"],
        starts_at=row["starts_at"],
        ends_at=row["ends_at"],
        description=row["description"],
        location=row["location"],
        status=row["status"],
        source_email_id=row["source_email_id"],
        task_id=row["task_id"],
        project_id=row["project_id"],
        assigned_worker_id=row["assigned_worker_id"],
        attendee_emails=json.loads(row["attendee_emails_json"] or "[]"),
        calendar_id=row["calendar_id"],
        external_event_id=row["external_event_id"],
        created_at=row["created_at"],
    )


def create_worker(config: AppConfig, worker: Worker) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO workers (
                full_name, role, email, phone, hourly_rate, payout_rate, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                worker.full_name,
                worker.role,
                worker.email,
                worker.phone,
                worker.hourly_rate,
                worker.payout_rate,
                worker.status,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_workers(config: AppConfig) -> Sequence[WorkerModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, full_name, role, email, phone, hourly_rate, payout_rate, status, created_at
            FROM workers
            ORDER BY full_name COLLATE NOCASE ASC
            """
        ).fetchall()

    return [
        WorkerModel(
            id=row["id"],
            full_name=row["full_name"],
            role=row["role"],
            email=row["email"],
            phone=row["phone"],
            hourly_rate=row["hourly_rate"],
            payout_rate=row["payout_rate"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_worker(config: AppConfig, worker_id: int) -> WorkerModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, full_name, role, email, phone, hourly_rate, payout_rate, status, created_at
            FROM workers
            WHERE id = ?
            """,
            (worker_id,),
        ).fetchone()

    if row is None:
        return None

    return WorkerModel(
        id=row["id"],
        full_name=row["full_name"],
        role=row["role"],
        email=row["email"],
        phone=row["phone"],
        hourly_rate=row["hourly_rate"],
        payout_rate=row["payout_rate"],
        status=row["status"],
        created_at=row["created_at"],
    )


def update_worker(config: AppConfig, worker_id: int, worker: Worker) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE workers
            SET full_name = ?, role = ?, email = ?, phone = ?, hourly_rate = ?, payout_rate = ?, status = ?
            WHERE id = ?
            """,
            (
                worker.full_name,
                worker.role,
                worker.email,
                worker.phone,
                worker.hourly_rate,
                worker.payout_rate,
                worker.status,
                worker_id,
            ),
        )
        connection.commit()
        return cursor.rowcount > 0


def create_user(config: AppConfig, user: User) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                email, password_hash, full_name, role, worker_id, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.email.strip().lower(),
                user.password_hash,
                user.full_name,
                user.role,
                user.worker_id,
                user.status,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_users(config: AppConfig) -> Sequence[UserModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, email, password_hash, full_name, role, worker_id, status, created_at
            FROM users
            ORDER BY full_name COLLATE NOCASE ASC, email COLLATE NOCASE ASC
            """
        ).fetchall()

    return [
        UserModel(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            worker_id=row["worker_id"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_user(config: AppConfig, user_id: int) -> UserModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash, full_name, role, worker_id, status, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return UserModel(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
        role=row["role"],
        worker_id=row["worker_id"],
        status=row["status"],
        created_at=row["created_at"],
    )


def get_user_by_email(config: AppConfig, email: str) -> UserModel | None:
    normalized_email = email.strip().lower()
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash, full_name, role, worker_id, status, created_at
            FROM users
            WHERE lower(email) = ?
            """,
            (normalized_email,),
        ).fetchone()

    if row is None:
        return None

    return UserModel(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
        role=row["role"],
        worker_id=row["worker_id"],
        status=row["status"],
        created_at=row["created_at"],
    )


def update_user(
    config: AppConfig,
    user_id: int,
    *,
    email: str,
    full_name: str,
    role: str,
    worker_id: int | None,
    status: str,
    password_hash: str | None = None,
) -> bool:
    with get_connection(config.db_path) as connection:
        if password_hash:
            cursor = connection.execute(
                """
                UPDATE users
                SET email = ?, password_hash = ?, full_name = ?, role = ?, worker_id = ?, status = ?
                WHERE id = ?
                """,
                (email.strip().lower(), password_hash, full_name, role, worker_id, status, user_id),
            )
        else:
            cursor = connection.execute(
                """
                UPDATE users
                SET email = ?, full_name = ?, role = ?, worker_id = ?, status = ?
                WHERE id = ?
                """,
                (email.strip().lower(), full_name, role, worker_id, status, user_id),
            )
        connection.commit()
        return cursor.rowcount > 0


def delete_user(config: AppConfig, user_id: int) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def create_work_log(config: AppConfig, work_log: WorkLog) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO work_logs (
                project_id, worker_id, work_date, hours, notes, starts_at, ends_at,
                travel_km, material_cost, payout_amount, billable_amount,
                payment_status, paid_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_log.project_id,
                work_log.worker_id,
                work_log.work_date,
                work_log.hours,
                work_log.notes,
                work_log.starts_at,
                work_log.ends_at,
                work_log.travel_km,
                work_log.material_cost,
                work_log.payout_amount,
                work_log.billable_amount,
                work_log.payment_status,
                work_log.paid_at,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def create_project_timeline_event(
    config: AppConfig,
    *,
    project_id: int,
    event_type: str,
    title: str,
    details: str = "",
) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO project_timeline_events (
                project_id, event_type, title, details, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, event_type, title, details, utc_now_iso()),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_project_timeline_events(config: AppConfig, project_id: int) -> Sequence[ProjectTimelineEventModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, project_id, event_type, title, details, created_at
            FROM project_timeline_events
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            (project_id,),
        ).fetchall()

    return [
        ProjectTimelineEventModel(
            id=row["id"],
            project_id=row["project_id"],
            event_type=row["event_type"],
            title=row["title"],
            details=row["details"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def list_work_logs(
    config: AppConfig,
    *,
    project_id: int | None = None,
    worker_id: int | None = None,
) -> Sequence[WorkLogModel]:
    query = """
        SELECT id, project_id, worker_id, work_date, hours, notes, starts_at, ends_at,
               travel_km, material_cost, payout_amount, billable_amount,
               payment_status, paid_at, created_at
        FROM work_logs
    """
    conditions: list[str] = []
    params: list[object] = []

    if project_id is not None:
        conditions.append("project_id = ?")
        params.append(project_id)
    if worker_id is not None:
        conditions.append("worker_id = ?")
        params.append(worker_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY work_date DESC, created_at DESC"

    with get_connection(config.db_path) as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        WorkLogModel(
            id=row["id"],
            project_id=row["project_id"],
            worker_id=row["worker_id"],
            work_date=row["work_date"],
            hours=row["hours"],
            notes=row["notes"],
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            travel_km=row["travel_km"],
            material_cost=row["material_cost"],
            payout_amount=row["payout_amount"],
            billable_amount=row["billable_amount"],
            payment_status=row["payment_status"],
            paid_at=row["paid_at"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def update_work_log_payment_status(
    config: AppConfig,
    work_log_id: int,
    *,
    payment_status: str,
    paid_at: str | None,
) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE work_logs
            SET payment_status = ?, paid_at = ?
            WHERE id = ?
            """,
            (payment_status, paid_at, work_log_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_work_logs_payment_status(
    config: AppConfig,
    *,
    project_id: int,
    worker_id: int,
    payment_status: str,
    paid_at: str | None,
) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE work_logs
            SET payment_status = ?, paid_at = ?
            WHERE project_id = ? AND worker_id = ?
            """,
            (payment_status, paid_at, project_id, worker_id),
        )
        connection.commit()
        return cursor.rowcount


def create_project_document(config: AppConfig, document: ProjectDocument) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO project_documents (
                project_id, title, file_path, document_type, source_email_id, worker_id, work_date, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.project_id,
                document.title,
                document.file_path,
                document.document_type,
                document.source_email_id,
                document.worker_id,
                document.work_date,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_project_documents(
    config: AppConfig,
    *,
    project_id: int | None = None,
) -> Sequence[ProjectDocumentModel]:
    with get_connection(config.db_path) as connection:
        rows_info = connection.execute("PRAGMA table_info(project_documents)").fetchall()
        columns = {row["name"] for row in rows_info}
        has_source_email_id = "source_email_id" in columns
        has_worker_id = "worker_id" in columns
        has_work_date = "work_date" in columns
        select_columns = [
            "id",
            "project_id",
            "title",
            "file_path",
            "document_type",
            "source_email_id" if has_source_email_id else "NULL AS source_email_id",
            "worker_id" if has_worker_id else "NULL AS worker_id",
            "work_date" if has_work_date else "NULL AS work_date",
            "created_at",
        ]
        query = f"""
            SELECT {", ".join(select_columns)}
            FROM project_documents
        """
        params: list[object] = []
        if project_id is not None:
            query += " WHERE project_id = ?"
            params.append(project_id)
        query += " ORDER BY created_at DESC"
        rows = connection.execute(query, params).fetchall()

    return [
        ProjectDocumentModel(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            file_path=row["file_path"],
            document_type=row["document_type"],
            source_email_id=row["source_email_id"],
            worker_id=row["worker_id"],
            work_date=row["work_date"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_project_document(config: AppConfig, document_id: int) -> ProjectDocumentModel | None:
    with get_connection(config.db_path) as connection:
        rows_info = connection.execute("PRAGMA table_info(project_documents)").fetchall()
        columns = {item["name"] for item in rows_info}
        has_source_email_id = "source_email_id" in columns
        has_worker_id = "worker_id" in columns
        has_work_date = "work_date" in columns
        row = connection.execute(
            f"""
            SELECT id, project_id, title, file_path, document_type,
                   {"source_email_id" if has_source_email_id else "NULL AS source_email_id"},
                   {"worker_id" if has_worker_id else "NULL AS worker_id"},
                   {"work_date" if has_work_date else "NULL AS work_date"},
                   created_at
            FROM project_documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    if row is None:
        return None

    return ProjectDocumentModel(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        file_path=row["file_path"],
        document_type=row["document_type"],
        source_email_id=row["source_email_id"],
        worker_id=row["worker_id"],
        work_date=row["work_date"],
        created_at=row["created_at"],
    )


def create_approval_item(config: AppConfig, item: ApprovalItem) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO approval_items (
                action_type, title, payload_json, status, source_email_id, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.action_type,
                item.title,
                json.dumps(item.payload, ensure_ascii=True),
                item.status,
                item.source_email_id,
                item.reason,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_approval_items(config: AppConfig) -> Sequence[ApprovalItemModel]:
    with get_connection(config.db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, action_type, title, payload_json, status, source_email_id, reason, created_at
            FROM approval_items
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        ApprovalItemModel(
            id=row["id"],
            action_type=row["action_type"],
            title=row["title"],
            payload=json.loads(row["payload_json"] or "{}"),
            status=row["status"],
            source_email_id=row["source_email_id"],
            reason=row["reason"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_approval_item(config: AppConfig, item_id: int) -> ApprovalItemModel | None:
    with get_connection(config.db_path) as connection:
        row = connection.execute(
            """
            SELECT id, action_type, title, payload_json, status, source_email_id, reason, created_at
            FROM approval_items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

    if row is None:
        return None

    return ApprovalItemModel(
        id=row["id"],
        action_type=row["action_type"],
        title=row["title"],
        payload=json.loads(row["payload_json"] or "{}"),
        status=row["status"],
        source_email_id=row["source_email_id"],
        reason=row["reason"],
        created_at=row["created_at"],
    )


def update_approval_item_status(
    config: AppConfig,
    item_id: int,
    status: str,
) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE approval_items
            SET status = ?
            WHERE id = ?
            """,
            (status, item_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_task(config: AppConfig, task_id: int) -> bool:
    with get_connection(config.db_path) as connection:
        connection.execute(
            """
            DELETE FROM task_workers
            WHERE task_id = ?
            """,
            (task_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_email(config: AppConfig, email_id: str) -> bool:
    with get_connection(config.db_path) as connection:
        connection.execute(
            """
            DELETE FROM email_project_links
            WHERE email_id = ?
            """,
            (email_id,),
        )
        connection.execute(
            """
            UPDATE tasks
            SET source_email_id = NULL
            WHERE source_email_id = ?
            """,
            (email_id,),
        )
        connection.execute(
            """
            UPDATE invoices
            SET source_email_id = NULL
            WHERE source_email_id = ?
            """,
            (email_id,),
        )
        connection.execute(
            """
            UPDATE calendar_events
            SET source_email_id = NULL
            WHERE source_email_id = ?
            """,
            (email_id,),
        )
        connection.execute(
            """
            UPDATE project_documents
            SET source_email_id = NULL
            WHERE source_email_id = ?
            """,
            (email_id,),
        )
        connection.execute(
            """
            UPDATE approval_items
            SET source_email_id = NULL
            WHERE source_email_id = ?
            """,
            (email_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM emails
            WHERE id = ?
            """,
            (email_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_project_documents_by_project(config: AppConfig, project_id: int) -> int:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM project_documents
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.commit()
        return cursor.rowcount


def delete_project(config: AppConfig, project_id: int) -> bool:
    with get_connection(config.db_path) as connection:
        connection.execute(
            """
            DELETE FROM email_project_links
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            UPDATE emails
            SET project_id = NULL
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            DELETE FROM tasks
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            DELETE FROM invoices
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            DELETE FROM work_logs
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            DELETE FROM project_documents
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            DELETE FROM calendar_events
            WHERE project_id = ?
            """,
            (project_id,),
        )
        connection.execute(
            """
            DELETE FROM project_timeline_events
            WHERE project_id = ?
            """,
            (project_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM projects
            WHERE id = ?
            """,
            (project_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_worker(config: AppConfig, worker_id: int) -> bool:
    with get_connection(config.db_path) as connection:
        connection.execute(
            """
            UPDATE users
            SET worker_id = NULL
            WHERE worker_id = ?
            """,
            (worker_id,),
        )
        connection.execute(
            """
            DELETE FROM task_workers
            WHERE worker_id = ?
            """,
            (worker_id,),
        )
        connection.execute(
            """
            DELETE FROM work_logs
            WHERE worker_id = ?
            """,
            (worker_id,),
        )
        connection.execute(
            """
            UPDATE tasks
            SET assigned_worker_id = NULL
            WHERE assigned_worker_id = ?
            """,
            (worker_id,),
        )
        connection.execute(
            """
            UPDATE calendar_events
            SET assigned_worker_id = NULL
            WHERE assigned_worker_id = ?
            """,
            (worker_id,),
        )
        connection.execute(
            """
            UPDATE project_documents
            SET worker_id = NULL
            WHERE worker_id = ?
            """,
            (worker_id,),
        )
        cursor = connection.execute(
            """
            DELETE FROM workers
            WHERE id = ?
            """,
            (worker_id,),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_work_log(config: AppConfig, work_log_id: int) -> bool:
    with get_connection(config.db_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM work_logs
            WHERE id = ?
            """,
            (work_log_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
