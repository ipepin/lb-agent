from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import AppConfig
from app.utils.file_utils import ensure_directory


TASKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'pending',
    due_date TEXT,
    source_email_id TEXT,
    project_id INTEGER,
    assigned_worker_id INTEGER,
    estimated_hours REAL,
    completed_at TEXT,
    completed_by_user_id INTEGER,
    created_at TEXT NOT NULL
);
"""


TASK_WORKERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS task_workers (
    task_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (task_id, worker_id)
);
"""


REMINDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    related_type TEXT NOT NULL DEFAULT '',
    related_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
"""


EMAILS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL DEFAULT '',
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    received_at TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'uncategorized',
    priority TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'new',
    attachments_json TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '',
    project_id INTEGER
);
"""


EMAIL_PROJECT_LINKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS email_project_links (
    email_id TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (email_id, project_id)
);
"""


INVOICES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT NOT NULL,
    invoice_number TEXT NOT NULL DEFAULT '',
    amount REAL,
    currency TEXT NOT NULL DEFAULT 'CZK',
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'detected',
    source_email_id TEXT,
    attachment_path TEXT NOT NULL DEFAULT '',
    project_id INTEGER,
    created_at TEXT NOT NULL
);
"""


PROJECTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    code TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL DEFAULT '',
    contact_person TEXT NOT NULL DEFAULT '',
    contact_email TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'normal',
    planned_start_at TEXT,
    planned_end_at TEXT,
    actual_start_at TEXT,
    actual_end_at TEXT,
    budget_amount REAL,
    notes TEXT NOT NULL DEFAULT '',
    internal_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


WORKERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    hourly_rate REAL,
    payout_rate REAL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);
"""


WORK_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS work_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    work_date TEXT NOT NULL,
    hours REAL NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    starts_at TEXT,
    ends_at TEXT,
    travel_km REAL NOT NULL DEFAULT 0,
    material_cost REAL NOT NULL DEFAULT 0,
    payout_amount REAL,
    billable_amount REAL,
    payment_status TEXT NOT NULL DEFAULT 'unpaid',
    paid_at TEXT,
    created_at TEXT NOT NULL
);
"""


PROJECT_DOCUMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'general',
    source_email_id TEXT,
    worker_id INTEGER,
    work_date TEXT,
    created_at TEXT NOT NULL
);
"""


PROJECT_TIMELINE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS project_timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'system',
    title TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


CALENDAR_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed',
    source_email_id TEXT,
    task_id INTEGER,
    project_id INTEGER,
    assigned_worker_id INTEGER,
    attendee_emails_json TEXT NOT NULL DEFAULT '[]',
    calendar_id TEXT NOT NULL DEFAULT '',
    external_event_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


APPROVAL_ITEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS approval_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    source_email_id TEXT,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""


USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'worker',
    worker_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);
"""


@contextmanager
def get_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {row["name"] for row in rows}

    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def _repair_calendar_event_links(connection: sqlite3.Connection) -> None:
    events = connection.execute(
        """
        SELECT id, title, starts_at, project_id, assigned_worker_id
        FROM calendar_events
        WHERE task_id IS NULL OR task_id = ''
        """
    ).fetchall()
    if not events:
        return

    tasks = connection.execute(
        """
        SELECT id, title, due_date, project_id, assigned_worker_id
        FROM tasks
        """
    ).fetchall()
    projects = {
        row["id"]: row["name"]
        for row in connection.execute("SELECT id, name FROM projects").fetchall()
    }

    used_task_ids: set[int] = set()
    for event in events:
        title = (event["title"] or "").strip()
        starts_at = (event["starts_at"] or "").strip()
        event_project_id = event["project_id"]
        event_worker_id = event["assigned_worker_id"]
        normalized_title = title
        prefixed_project_id = None

        if " – " in title:
            project_name, task_title = title.split(" – ", 1)
            normalized_title = task_title.strip()
            for project_id, project_name_value in projects.items():
                if (project_name_value or "").strip() == project_name.strip():
                    prefixed_project_id = project_id
                    break

        candidates = []
        for task in tasks:
            if task["id"] in used_task_ids:
                continue
            if (task["title"] or "").strip() != normalized_title:
                continue
            score = 0
            if (task["due_date"] or "").strip() == starts_at:
                score += 5
            if prefixed_project_id is not None and task["project_id"] == prefixed_project_id:
                score += 4
            if event_project_id is not None and task["project_id"] == event_project_id:
                score += 3
            if event_worker_id is not None and task["assigned_worker_id"] == event_worker_id:
                score += 1
            candidates.append((score, task))

        if not candidates:
            continue

        candidates.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
        best_task = candidates[0][1]
        used_task_ids.add(best_task["id"])
        connection.execute(
            """
            UPDATE calendar_events
            SET task_id = ?, project_id = COALESCE(project_id, ?), assigned_worker_id = COALESCE(assigned_worker_id, ?)
            WHERE id = ?
            """,
            (
                best_task["id"],
                best_task["project_id"],
                best_task["assigned_worker_id"],
                event["id"],
            ),
        )


def initialize_database(config: AppConfig) -> None:
    ensure_directory(config.data_dir)
    ensure_directory(config.attachments_dir)
    ensure_directory(config.data_dir / "project_documents")

    with get_connection(config.db_path) as connection:
        connection.execute(TASKS_TABLE_SQL)
        connection.execute(TASK_WORKERS_TABLE_SQL)
        connection.execute(REMINDERS_TABLE_SQL)
        connection.execute(EMAILS_TABLE_SQL)
        connection.execute(EMAIL_PROJECT_LINKS_TABLE_SQL)
        connection.execute(INVOICES_TABLE_SQL)
        connection.execute(CALENDAR_EVENTS_TABLE_SQL)
        connection.execute(APPROVAL_ITEMS_TABLE_SQL)
        connection.execute(USERS_TABLE_SQL)
        connection.execute(PROJECTS_TABLE_SQL)
        connection.execute(WORKERS_TABLE_SQL)
        connection.execute(WORK_LOGS_TABLE_SQL)
        connection.execute(PROJECT_DOCUMENTS_TABLE_SQL)
        connection.execute(PROJECT_TIMELINE_EVENTS_TABLE_SQL)
        _ensure_column(connection, "tasks", "priority", "TEXT NOT NULL DEFAULT 'normal'")
        _ensure_column(connection, "tasks", "source_email_id", "TEXT")
        _ensure_column(connection, "tasks", "project_id", "INTEGER")
        _ensure_column(connection, "tasks", "assigned_worker_id", "INTEGER")
        _ensure_column(connection, "tasks", "estimated_hours", "REAL")
        _ensure_column(connection, "tasks", "completed_at", "TEXT")
        _ensure_column(connection, "tasks", "completed_by_user_id", "INTEGER")
        _ensure_column(connection, "emails", "project_id", "INTEGER")
        _ensure_column(
            connection,
            "invoices",
            "attachment_path",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(connection, "invoices", "project_id", "INTEGER")
        _ensure_column(connection, "projects", "code", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "customer_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "contact_person", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "contact_email", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "contact_phone", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "address", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "priority", "TEXT NOT NULL DEFAULT 'normal'")
        _ensure_column(connection, "projects", "planned_start_at", "TEXT")
        _ensure_column(connection, "projects", "planned_end_at", "TEXT")
        _ensure_column(connection, "projects", "actual_start_at", "TEXT")
        _ensure_column(connection, "projects", "actual_end_at", "TEXT")
        _ensure_column(connection, "projects", "budget_amount", "REAL")
        _ensure_column(connection, "projects", "notes", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "projects", "internal_notes", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(
            connection,
            "reminders",
            "related_type",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            "reminders",
            "related_id",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            "reminders",
            "status",
            "TEXT NOT NULL DEFAULT 'pending'",
        )
        _ensure_column(connection, "calendar_events", "project_id", "INTEGER")
        _ensure_column(connection, "calendar_events", "assigned_worker_id", "INTEGER")
        _ensure_column(connection, "calendar_events", "task_id", "INTEGER")
        _ensure_column(
            connection,
            "calendar_events",
            "attendee_emails_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            "calendar_events",
            "calendar_id",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            "calendar_events",
            "external_event_id",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(
            connection,
            "work_logs",
            "payment_status",
            "TEXT NOT NULL DEFAULT 'unpaid'",
        )
        _ensure_column(connection, "work_logs", "paid_at", "TEXT")
        _ensure_column(connection, "project_documents", "source_email_id", "TEXT")
        _ensure_column(connection, "project_documents", "worker_id", "INTEGER")
        _ensure_column(connection, "project_documents", "work_date", "TEXT")
        _repair_calendar_event_links(connection)
        connection.commit()
