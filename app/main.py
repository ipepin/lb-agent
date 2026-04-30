from __future__ import annotations

from uuid import uuid4

from app.config import AppConfig, load_config
from app.db import crud
from app.db.database import initialize_database
from app.services.agent_service import AgentService
from app.services.approval_service import ApprovalService
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService
from app.schemas.entities import Email
from app.ui.console import (
    print_approval_detail,
    print_approvals,
    print_dashboard,
    print_email_detail,
    print_email_analysis,
    print_emails,
    print_reminders,
    print_startup_message,
    print_tasks,
    prompt_approval_review,
    prompt_email_detail,
    prompt_email_input,
    prompt_main_menu,
)
from app.utils.dates import utc_now_iso
from app.utils.logger import get_logger


logger = get_logger(__name__)


def bootstrap(config: AppConfig | None = None) -> AppConfig:
    active_config = config or load_config()
    initialize_database(active_config)
    logger.info("Application bootstrap completed.")
    return active_config


def run() -> None:
    config = bootstrap()
    task_service = TaskService(config)
    reminder_service = ReminderService(config)
    approval_service = ApprovalService(config)
    agent_service = AgentService(
        config=config,
        approval_service=approval_service,
        reminder_service=reminder_service,
    )

    while True:
        tasks = task_service.list_tasks()
        reminders = reminder_service.list_reminders()
        approvals = approval_service.list_items()
        emails = crud.list_emails(config)
        print_startup_message(
            config=config,
            tasks=tasks,
            reminders=reminders,
            approvals=approvals,
            emails=emails,
        )
        choice = prompt_main_menu()

        if choice == "1":
            print_dashboard(tasks=tasks, reminders=reminders, approvals=approvals, emails=emails)
        elif choice == "2":
            sender, subject, body, attachments = prompt_email_input()
            email = Email(
                id=str(uuid4()),
                sender=sender,
                subject=subject,
                body=body,
                received_at=utc_now_iso(),
                attachments=attachments,
            )
            processing_result = agent_service.process_email(email)

            print_email_analysis(
                classification=processing_result.classification,
                parsed_email=processing_result.parsed_email,
                approval_count=len(processing_result.approval_ids),
            )
        elif choice == "3":
            print_approvals(approvals)
        elif choice == "4":
            print_tasks(tasks)
        elif choice == "5":
            print_reminders(reminders)
        elif choice == "6":
            print_emails(emails)
        elif choice == "7":
            approval_id, action = prompt_approval_review()
            if approval_id is None:
                print("Invalid approval id.")
                continue

            if action == "v":
                print_approval_detail(approval_service.get_item(approval_id))
            elif action == "a":
                approved = approval_service.approve_item(approval_id)
                print("Approval applied." if approved else "Approval could not be applied.")
            elif action == "r":
                rejected = approval_service.reject_item(approval_id)
                print("Approval rejected." if rejected else "Approval could not be rejected.")
            else:
                print("Unknown approval action.")
        elif choice == "8":
            email_id = prompt_email_detail()
            print_email_detail(crud.get_email(config, email_id))
        elif choice == "0":
            break
        else:
            print("Unknown action.")


if __name__ == "__main__":
    run()
