from __future__ import annotations

import json
import sys
from typing import Sequence

from app.config import AppConfig
from app.db.models import ApprovalItemModel, EmailModel, ReminderModel, TaskModel
from app.schemas.entities import EmailClassification, ParsedEmail


def _safe_console_text(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding)


def print_startup_message(
    config: AppConfig,
    tasks: Sequence[TaskModel],
    reminders: Sequence[ReminderModel],
    approvals: Sequence[ApprovalItemModel],
    emails: Sequence[EmailModel],
) -> None:
    print("\nLocal Assistant")
    print(f"Database: {config.db_path}")
    print(f"Tasks loaded: {len(tasks)}")
    print(f"Reminders loaded: {len(reminders)}")
    print(f"Emails processed: {len(emails)}")
    print(f"Pending approvals: {len([item for item in approvals if item.status == 'pending'])}")


def prompt_main_menu() -> str:
    print("\nMenu")
    print("1. Dashboard")
    print("2. Process email")
    print("3. List approvals")
    print("4. List tasks")
    print("5. List reminders")
    print("6. List emails")
    print("7. Review approval")
    print("8. View email detail")
    print("0. Exit")
    return input("Select action: ").strip()


def prompt_email_input() -> tuple[str, str, str, list[str]]:
    sender = input("Sender: ").strip()
    subject = input("Subject: ").strip()
    print("Body (finish with empty line):")

    lines: list[str] = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)

    attachments_raw = input("Attachments (comma separated, optional): ").strip()
    attachments = [item.strip() for item in attachments_raw.split(",") if item.strip()]
    return sender, subject, "\n".join(lines), attachments


def print_dashboard(
    tasks: Sequence[TaskModel],
    reminders: Sequence[ReminderModel],
    approvals: Sequence[ApprovalItemModel],
    emails: Sequence[EmailModel],
) -> None:
    print("\nDashboard")
    print(f"Tasks: {len(tasks)}")
    print(f"Reminders: {len(reminders)}")
    print(f"Processed emails: {len(emails)}")
    print(f"Approvals: {len(approvals)}")


def print_email_analysis(
    classification: EmailClassification,
    parsed_email: ParsedEmail,
    approval_count: int,
) -> None:
    print("\nEmail analysis")
    print(f"Category: {classification.category}")
    print(f"Action: {classification.action}")
    print(f"Priority: {classification.priority}")
    print(f"Needs reply: {classification.needs_reply}")
    print(f"Summary: {parsed_email.summary}")
    print(f"Company: {parsed_email.company_name or '-'}")
    print(f"Contact: {parsed_email.contact or '-'}")
    print(f"Deadline: {parsed_email.requested_deadline or '-'}")
    print(f"Invoice number: {parsed_email.invoice_number or '-'}")
    amount_text = (
        f"{parsed_email.invoice_amount} {parsed_email.invoice_currency}"
        if parsed_email.invoice_amount is not None
        else "-"
    )
    print(f"Invoice amount: {amount_text}")
    print(f"Approvals created: {approval_count}")


def print_approvals(items: Sequence[ApprovalItemModel]) -> None:
    print("\nApproval items")
    if not items:
        print("No approval items.")
        return

    for item in items:
        print(f"- [{item.status}] #{item.id} {item.action_type}: {item.title}")


def print_approval_detail(item: ApprovalItemModel | None) -> None:
    print("\nApproval detail")
    if item is None:
        print("Approval item not found.")
        return

    print(_safe_console_text(f"Id: {item.id}"))
    print(_safe_console_text(f"Status: {item.status}"))
    print(_safe_console_text(f"Action: {item.action_type}"))
    print(_safe_console_text(f"Title: {item.title}"))
    print(_safe_console_text(f"Source email: {item.source_email_id or '-'}"))
    print(_safe_console_text(f"Reason: {item.reason or '-'}"))
    print("Payload:")
    print(_safe_console_text(json.dumps(item.payload, ensure_ascii=False, indent=2)))


def prompt_approval_review() -> tuple[int | None, str]:
    raw_id = input("Approval id: ").strip()
    if not raw_id.isdigit():
        return None, ""

    print("Action: [v]iew  [a]pprove  [r]eject")
    action = input("Choose action: ").strip().lower()
    return int(raw_id), action


def print_tasks(tasks: Sequence[TaskModel]) -> None:
    print("\nTasks")
    if not tasks:
        print("No tasks.")
        return

    for task in tasks:
        print(
            f"- [{task.status}] {task.title} | priority={task.priority} | due={task.due_date or '-'}"
        )


def print_reminders(reminders: Sequence[ReminderModel]) -> None:
    print("\nReminders")
    if not reminders:
        print("No reminders.")
        return

    for reminder in reminders:
        print(f"- [{reminder.status}] {reminder.title} | at={reminder.remind_at}")


def print_emails(emails: Sequence[EmailModel]) -> None:
    print("\nEmails")
    if not emails:
        print("No emails.")
        return

    for email in emails:
        summary = email.summary or email.body[:120].replace("\n", " ").strip()
        print(
            _safe_console_text(
                f"- {email.received_at} | {email.sender} | {email.subject} | "
                f"category={email.category} | summary={summary or '-'}"
            )
        )


def prompt_email_detail() -> str:
    return input("Email id: ").strip()


def print_email_detail(email: EmailModel | None) -> None:
    print("\nEmail detail")
    if email is None:
        print("Email not found.")
        return

    print(_safe_console_text(f"Id: {email.id}"))
    print(_safe_console_text(f"Received: {email.received_at}"))
    print(_safe_console_text(f"Sender: {email.sender}"))
    print(_safe_console_text(f"Subject: {email.subject}"))
    print(_safe_console_text(f"Category: {email.category}"))
    print(_safe_console_text(f"Priority: {email.priority}"))
    print(_safe_console_text(f"Status: {email.status}"))
    print(_safe_console_text(f"Thread: {email.thread_id or '-'}"))
    print("Attachments:")
    if email.attachments:
        for attachment in email.attachments:
            print(_safe_console_text(f"- {attachment}"))
    else:
        print("- none")

    print("Summary:")
    print(_safe_console_text(email.summary or "-"))
    print("Body:")
    print(_safe_console_text(email.body or "-"))
