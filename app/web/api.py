from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from app.config import AppConfig, load_config
from app.db import crud
from app.db.models import UserModel
from app.db.database import initialize_database
from app.schemas.entities import Email, EmailClassification, User
from app.services.auth_service import AuthService, ROLE_ADMIN, ROLE_OWNER, ROLE_WORKER, hash_password
from app.services.calendar_service import CalendarService
from app.services.dashboard_service import DashboardService
from app.services.invoice_service import InvoiceService
from app.services.parser_service import ParserService
from app.services.project_service import ProjectService
from app.services.project_document_service import ProjectDocumentService
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService
from app.services.worker_service import WorkerService
from app.services.worklog_service import WorkLogService


class ProjectCreatePayload(BaseModel):
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


class WorkerCreatePayload(BaseModel):
    full_name: str
    role: str = ""
    email: str = ""
    phone: str = ""
    hourly_rate: float | None = None
    payout_rate: float | None = None
    status: str = "active"


class WorkLogCreatePayload(BaseModel):
    project_id: int
    worker_id: int
    work_date: str
    hours: float = Field(gt=0)
    notes: str = ""
    starts_at: str | None = None
    ends_at: str | None = None
    travel_km: float = 0.0
    material_cost: float = 0.0
    payout_amount: float | None = None
    billable_amount: float | None = None


class WorkLogPaymentPayload(BaseModel):
    is_paid: bool


class WorkLogSummaryPaymentPayload(BaseModel):
    project_id: int
    worker_id: int
    is_paid: bool


class ProjectWorkerRateItemPayload(BaseModel):
    worker_id: int
    payout_rate: float | None = None


class ProjectWorkerRateBulkPayload(BaseModel):
    items: list[ProjectWorkerRateItemPayload]


class EmailActionPayload(BaseModel):
    action: str
    project_id: int | None = None
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    priority: str | None = None
    assigned_worker_id: int | None = None
    assigned_worker_ids: list[int] = []
    estimated_hours: float | None = None


class BulkEmailActionPayload(BaseModel):
    email_ids: list[str]
    action: str
    project_id: int | None = None


class TaskActionPayload(BaseModel):
    action: str
    project_id: int | None = None


class BulkTaskActionPayload(BaseModel):
    task_ids: list[int]
    action: str
    project_id: int | None = None


class ProjectTaskCreatePayload(BaseModel):
    title: str
    description: str = ""
    status: str = "pending"
    due_date: str | None = None
    priority: str = "normal"
    assigned_worker_id: int | None = None
    assigned_worker_ids: list[int] = []
    estimated_hours: float | None = None


class TaskCreatePayload(ProjectTaskCreatePayload):
    project_id: int | None = None
    source_email_id: str | None = None


class LoginPayload(BaseModel):
    login: str
    password: str


class UserPayload(BaseModel):
    email: str
    password: str = ""
    full_name: str
    role: str = ROLE_WORKER
    worker_id: int | None = None
    status: str = "active"


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


def _serialize_many(items: list[Any]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]


def _serialize_user(config: AppConfig, user: UserModel) -> dict[str, Any]:
    worker = crud.get_worker(config, user.worker_id) if user.worker_id is not None else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "status": user.status,
        "worker_id": user.worker_id,
        "worker": asdict(worker) if worker is not None else None,
    }


def _serialize_email(config: AppConfig, item: Any, *, include_body: bool = True) -> dict[str, Any]:
    payload = asdict(item)
    if not include_body:
        payload.pop("body", None)
        payload["body_preview"] = (item.summary or item.body or "")[:240]
    project_ids = crud.list_email_project_ids(config, item.id)
    projects = []
    for project_id in project_ids:
        project = crud.get_project(config, project_id)
        if project is not None:
            projects.append({"id": project.id, "name": project.name})
    payload["attachments"] = [
        {
            "name": Path(path).name,
            "path": path,
            "url": f"/api/emails/{item.id}/attachments/{index}",
        }
        for index, path in enumerate(item.attachments)
    ]
    payload["project_ids"] = project_ids
    payload["projects"] = projects
    return payload


def _serialize_document(item: Any) -> dict[str, Any]:
    payload = asdict(item)
    payload["url"] = f"/api/project-documents/{item.id}/file"
    payload["name"] = Path(item.file_path).name
    return payload


def _serialize_task(config: AppConfig, item: Any) -> dict[str, Any]:
    payload = asdict(item)
    worker_ids = payload.get("worker_ids") or []
    workers = []
    for worker_id in worker_ids:
        worker = crud.get_worker(config, int(worker_id))
        if worker is not None:
            workers.append({"id": worker.id, "full_name": worker.full_name, "email": worker.email})
    source_email = crud.get_email(config, item.source_email_id) if item.source_email_id else None
    project = crud.get_project(config, item.project_id) if item.project_id is not None else None
    completed_by_user = crud.get_user(config, int(item.completed_by_user_id)) if item.completed_by_user_id is not None else None
    calendar_events = [
        event
        for event in crud.list_calendar_events(config)
        if event.task_id == item.id
    ]
    calendar_events_payload = [
        {
            "id": event.id,
            "title": event.title,
            "starts_at": event.starts_at,
            "ends_at": event.ends_at,
            "status": event.status,
            "calendar_id": event.calendar_id,
            "external_event_id": event.external_event_id,
            "attendee_emails": list(event.attendee_emails),
            "created_at": event.created_at,
        }
        for event in calendar_events
    ]
    timeline: list[dict[str, Any]] = [
        {
            "at": item.created_at,
            "kind": "task",
            "title": "Úkol vytvořen",
            "details": item.title,
        }
    ]
    if source_email is not None:
        timeline.append(
            {
                "at": source_email.received_at,
                "kind": "email",
                "title": "Zdrojový e-mail",
                "details": source_email.subject,
            }
        )
    if item.due_date:
        timeline.append(
            {
                "at": item.due_date,
                "kind": "deadline",
                "title": "Termín úkolu",
                "details": item.due_date,
            }
        )
    if item.completed_at:
        timeline.append(
            {
                "at": item.completed_at,
                "kind": "status",
                "title": "Úkol dokončen",
                "details": f"Dokončil: {completed_by_user.full_name}" if completed_by_user is not None else "Stav: done",
            }
        )
    for event in calendar_events:
        timeline.append(
            {
                "at": event.created_at,
                "kind": "calendar",
                "title": "Zápis do kalendáře" if event.external_event_id else "Lokální kalendářový návrh",
                "details": event.title,
            }
        )
    payload["workers"] = workers
    payload["project"] = (
        {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "code": project.code,
            "customer_name": project.customer_name,
            "contact_person": project.contact_person,
            "contact_email": project.contact_email,
            "contact_phone": project.contact_phone,
            "address": project.address,
            "priority": project.priority,
            "notes": project.notes,
            "internal_notes": project.internal_notes,
        }
        if project is not None
        else None
    )
    payload["source_email"] = (
        {
            "id": source_email.id,
            "subject": source_email.subject,
            "sender": source_email.sender,
            "received_at": source_email.received_at,
        }
        if source_email is not None
        else None
    )
    payload["completed_by"] = (
        {
            "id": completed_by_user.id,
            "full_name": completed_by_user.full_name,
            "role": completed_by_user.role,
        }
        if completed_by_user is not None
        else None
    )
    payload["calendar_events"] = calendar_events_payload
    payload["latest_calendar_event"] = calendar_events_payload[-1] if calendar_events_payload else None
    payload["timeline"] = sorted(
        timeline,
        key=lambda entry: entry.get("at") or "",
        reverse=True,
    )
    return payload


def _conversation_key(email: Any) -> str:
    return email.thread_id or f"single:{email.id}"


def _serialize_conversations(emails: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = {}
    for email in emails:
        key = _conversation_key(email)
        grouped.setdefault(key, []).append(email)

    conversations: list[dict[str, Any]] = []
    for key, items in grouped.items():
        ordered = sorted(items, key=lambda item: item.received_at)
        latest = ordered[-1]
        senders = sorted({item.sender for item in ordered if item.sender})
        conversations.append(
            {
                "id": key,
                "thread_id": latest.thread_id,
                "project_id": latest.project_id,
                "subject": latest.subject,
                "latest_sender": latest.sender,
                "latest_received_at": latest.received_at,
                "email_count": len(ordered),
                "participants": senders,
                "status": latest.status,
                "category": latest.category,
            }
        )

    conversations.sort(
        key=lambda item: item.get("latest_received_at") or "",
        reverse=True,
    )
    return conversations


def _email_entity(email_model: Any) -> Email:
    return Email(
        id=email_model.id,
        thread_id=email_model.thread_id,
        sender=email_model.sender,
        subject=email_model.subject,
        body=email_model.body,
        received_at=email_model.received_at,
        attachments=list(email_model.attachments),
        category=email_model.category,
        priority=email_model.priority,
        project_id=email_model.project_id,
    )


def create_app(config: AppConfig | None = None) -> FastAPI:
    active_config = config or load_config()
    initialize_database(active_config)
    static_dir = Path(__file__).resolve().parent / "static"

    dashboard_service = DashboardService(active_config)
    project_service = ProjectService(active_config)
    task_service = TaskService(active_config)
    invoice_service = InvoiceService(active_config)
    reminder_service = ReminderService(active_config)
    calendar_service = CalendarService(active_config)
    parser_service = ParserService()
    worker_service = WorkerService(active_config)
    worklog_service = WorkLogService(active_config)
    project_document_service = ProjectDocumentService(active_config)
    auth_service = AuthService(active_config)
    auth_service.ensure_bootstrap_owner()

    app = FastAPI(
        title="LB-AGENT API",
        version="0.1.0",
        description=(
            "Viceplatformni backend pro zpracovani e-mailu, zakazky, ukoly, "
            "faktury, pracovniky a vykazy prace."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_config.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=active_config.auth_session_secret,
        session_cookie="lb_agent_session",
        same_site="lax",
        https_only=active_config.secure_session_cookies,
        max_age=60 * 60 * 24 * 30,
    )
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def get_manifest() -> FileResponse:
        return FileResponse(static_dir / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def get_service_worker() -> FileResponse:
        return FileResponse(static_dir / "sw.js", media_type="application/javascript")

    def current_user(request: Request) -> UserModel:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Přihlášení vypršelo nebo neexistuje.")
        user = crud.get_user(active_config, int(user_id))
        if user is None or user.status != "active":
            request.session.clear()
            raise HTTPException(status_code=401, detail="Uživatel není dostupný.")
        return user

    def require_roles(request: Request, *roles: str) -> UserModel:
        user = current_user(request)
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Na tuto akci nemáš oprávnění.")
        return user

    def get_worker_visible_project_ids(user: UserModel) -> set[int]:
        if user.worker_id is None:
            return set()
        task_project_ids = {
            int(task.project_id)
            for task in crud.list_tasks(active_config)
            if task.project_id is not None and (
                int(user.worker_id) in [int(worker_id) for worker_id in (task.worker_ids or [])]
                or task.assigned_worker_id == user.worker_id
            )
        }
        worklog_project_ids = {
            int(item.project_id)
            for item in worklog_service.list_work_logs(worker_id=user.worker_id)
        }
        return task_project_ids | worklog_project_ids

    def filter_tasks_for_user(user: UserModel, tasks: list[Any]) -> list[Any]:
        if user.role in {ROLE_OWNER, ROLE_ADMIN}:
            return tasks
        if user.worker_id is None:
            return []
        return [
            item
            for item in tasks
            if int(user.worker_id) in [int(worker_id) for worker_id in (item.worker_ids or [])]
            or item.assigned_worker_id == user.worker_id
        ]

    def filter_projects_for_user(user: UserModel, projects: list[Any]) -> list[Any]:
        if user.role in {ROLE_OWNER, ROLE_ADMIN}:
            return projects
        visible_ids = get_worker_visible_project_ids(user)
        return [item for item in projects if item.id in visible_ids]

    def filter_worklogs_for_user(user: UserModel, items: list[Any]) -> list[Any]:
        if user.role in {ROLE_OWNER, ROLE_ADMIN}:
            return items
        if user.worker_id is None:
            return []
        return [item for item in items if item.worker_id == user.worker_id]

    def filter_workers_for_user(user: UserModel, items: list[Any]) -> list[Any]:
        if user.role in {ROLE_OWNER, ROLE_ADMIN}:
            return items
        if user.worker_id is None:
            return []
        return [item for item in items if item.id == user.worker_id]

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/login")
    def login(payload: LoginPayload, request: Request) -> dict[str, object]:
        user = auth_service.authenticate(payload.login, payload.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Neplatný e-mail nebo heslo.")
        request.session["user_id"] = user.id
        return {"item": _serialize_user(active_config, user)}

    @app.post("/api/auth/logout")
    def logout(request: Request) -> dict[str, str]:
        request.session.clear()
        return {"status": "ok"}

    @app.post("/api/auth/change-password")
    def change_password(payload: ChangePasswordPayload, request: Request) -> dict[str, str]:
        user = current_user(request)
        authenticated = auth_service.authenticate(user.email, payload.current_password)
        if authenticated is None:
            raise HTTPException(status_code=400, detail="Současné heslo není správné.")
        if not payload.new_password.strip():
            raise HTTPException(status_code=400, detail="Nové heslo nesmí být prázdné.")
        crud.update_user(
            active_config,
            user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            worker_id=user.worker_id,
            status=user.status,
            password_hash=hash_password(payload.new_password),
        )
        return {"status": "ok"}

    @app.get("/api/auth/me")
    def auth_me(request: Request) -> dict[str, object]:
        user = current_user(request)
        return {"item": _serialize_user(active_config, user)}

    @app.get("/api/users")
    def list_users(request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        return {"items": [_serialize_user(active_config, item) for item in crud.list_users(active_config)]}

    @app.post("/api/users")
    def create_user(payload: UserPayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        user_id = crud.create_user(
            active_config,
            User(
                email=payload.email,
                password_hash=hash_password(payload.password or active_config.bootstrap_owner_password),
                full_name=payload.full_name,
                role=payload.role,
                worker_id=payload.worker_id,
                status=payload.status,
            ),
        )
        user = crud.get_user(active_config, user_id)
        return {"item": _serialize_user(active_config, user) if user is not None else None}

    @app.put("/api/users/{user_id}")
    def update_user(user_id: int, payload: UserPayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        updated = crud.update_user(
            active_config,
            user_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            worker_id=payload.worker_id,
            status=payload.status,
            password_hash=hash_password(payload.password) if payload.password else None,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Uživatel nebyl nalezen.")
        user = crud.get_user(active_config, user_id)
        return {"item": _serialize_user(active_config, user) if user is not None else None}

    @app.delete("/api/users/{user_id}")
    def delete_user(user_id: int, request: Request) -> dict[str, object]:
        current = require_roles(request, ROLE_OWNER)
        if current.id == user_id:
            raise HTTPException(status_code=400, detail="Nemůžeš smazat právě přihlášeného uživatele.")
        deleted = crud.delete_user(active_config, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Uživatel nebyl nalezen.")
        return {"status": "ok"}

    @app.post("/api/users/{user_id}/delete")
    def delete_user_post(user_id: int, request: Request) -> dict[str, object]:
        return delete_user(user_id, request)

    @app.get("/api/dashboard")
    def dashboard(request: Request) -> dict[str, object]:
        user = current_user(request)
        if user.role in {ROLE_OWNER, ROLE_ADMIN}:
            return dashboard_service.get_snapshot()
        tasks = filter_tasks_for_user(user, list(crud.list_tasks(active_config)))
        work_logs = filter_worklogs_for_user(user, list(worklog_service.list_work_logs()))
        return {
            "counts": {
                "emails": 0,
                "unprocessed_emails": 0,
                "active_projects": len(get_worker_visible_project_ids(user)),
                "open_tasks": len([item for item in tasks if item.status not in {"done", "archived"}]),
                "pending_invoices": 0,
                "workers": 1 if user.worker_id else 0,
                "work_logs": len(work_logs),
            },
            "finance": {
                "unpaid_worklogs": sum(getattr(item, "payout_amount", 0) or 0 for item in work_logs if item.payment_status != "paid"),
            },
        }

    @app.get("/api/inbox/unprocessed")
    def unprocessed_inbox(request: Request, include_body: bool = True) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        emails = [
            item
            for item in crud.list_emails(active_config)
            if item.category == "uncategorized" and item.status != "archived"
        ]
        tasks = [
            item
            for item in crud.list_tasks(active_config)
            if item.status not in {"done", "archived"}
        ]
        return {
            "emails": [_serialize_email(active_config, item, include_body=include_body) for item in emails],
            "tasks": [_serialize_task(active_config, item) for item in tasks],
        }

    @app.get("/api/archive")
    def archive(request: Request, include_body: bool = True) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        emails = [item for item in crud.list_emails(active_config) if item.status == "archived"]
        tasks = [
            item
            for item in crud.list_tasks(active_config)
            if item.status in {"done", "archived"}
        ]
        return {
            "emails": [_serialize_email(active_config, item, include_body=include_body) for item in emails],
            "tasks": [_serialize_task(active_config, item) for item in tasks],
        }

    @app.get("/api/conversations")
    def list_conversations(request: Request, include_archived: bool = False) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        emails = list(crud.list_emails(active_config))
        if not include_archived:
            emails = [item for item in emails if item.status != "archived"]
        return {"items": _serialize_conversations(emails)}

    @app.get("/api/conversations/{conversation_id:path}")
    def get_conversation(conversation_id: str, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        emails = list(crud.list_emails(active_config))
        items = [
            item
            for item in emails
            if _conversation_key(item) == conversation_id
        ]
        if not items:
            raise HTTPException(status_code=404, detail="Konverzace nebyla nalezena.")

        ordered = sorted(items, key=lambda item: item.received_at)
        latest = ordered[-1]
        return {
            "item": {
                "id": conversation_id,
                "thread_id": latest.thread_id,
                "project_id": latest.project_id,
                "subject": latest.subject,
                "latest_sender": latest.sender,
                "latest_received_at": latest.received_at,
                "email_count": len(ordered),
                "participants": sorted({item.sender for item in ordered if item.sender}),
                "status": latest.status,
                "category": latest.category,
            },
            "emails": [_serialize_email(active_config, item) for item in ordered],
        }

    @app.get("/api/emails")
    def list_emails(
        request: Request,
        include_archived: bool = False,
        include_body: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        emails = list(crud.list_emails(active_config))
        if not include_archived:
            emails = [item for item in emails if item.status != "archived"]
        total = len(emails)
        safe_offset = max(offset, 0)
        if limit is not None:
            safe_limit = max(min(limit, 500), 1)
            emails = emails[safe_offset : safe_offset + safe_limit]
        elif safe_offset:
            emails = emails[safe_offset:]
        return {
            "items": [
                _serialize_email(active_config, item, include_body=include_body)
                for item in emails
            ],
            "total": total,
            "limit": limit,
            "offset": safe_offset,
        }

    @app.get("/api/emails/{email_id}")
    def get_email(email_id: str, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        email = crud.get_email(active_config, email_id)
        if email is None:
            raise HTTPException(status_code=404, detail="E-mail nebyl nalezen.")
        return {"item": _serialize_email(active_config, email)}

    @app.get("/api/tasks")
    def list_tasks(request: Request) -> dict[str, object]:
        user = current_user(request)
        tasks = filter_tasks_for_user(user, list(crud.list_tasks(active_config)))
        return {"items": [_serialize_task(active_config, item) for item in tasks]}

    @app.post("/api/tasks")
    def create_task(payload: TaskCreatePayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        if payload.project_id is not None:
            project = project_service.get_project(payload.project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")

        task_id = task_service.create_task(
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
            source_email_id=payload.source_email_id,
            project_id=payload.project_id,
            assigned_worker_id=payload.assigned_worker_id,
            assigned_worker_ids=payload.assigned_worker_ids,
            estimated_hours=payload.estimated_hours,
        )
        task = next((item for item in task_service.list_tasks() if item.id == task_id), None)
        return {"item": _serialize_task(active_config, task) if task else None}

    @app.put("/api/tasks/{task_id}")
    def update_task(task_id: int, payload: TaskCreatePayload, request: Request) -> dict[str, object]:
        user = require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        if payload.project_id is not None:
            project = project_service.get_project(payload.project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")

        updated = task_service.update_task(
            task_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
            project_id=payload.project_id,
            assigned_worker_id=payload.assigned_worker_id,
            assigned_worker_ids=payload.assigned_worker_ids,
            estimated_hours=payload.estimated_hours,
            completed_by_user_id=user.id if payload.status == "done" else None,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Úkol nebyl nalezen.")
        task = next((item for item in task_service.list_tasks() if item.id == task_id), None)
        return {"item": _serialize_task(active_config, task) if task else None}

    @app.get("/api/emails/{email_id}/attachments/{attachment_index}")
    def get_email_attachment(email_id: str, attachment_index: int, request: Request) -> FileResponse:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        email = crud.get_email(active_config, email_id)
        if email is None:
            raise HTTPException(status_code=404, detail="E-mail nebyl nalezen.")
        if attachment_index < 0 or attachment_index >= len(email.attachments):
            raise HTTPException(status_code=404, detail="Příloha nebyla nalezena.")

        attachment_path = Path(email.attachments[attachment_index]).resolve()
        attachments_dir = active_config.attachments_dir.resolve()
        try:
            attachment_path.relative_to(attachments_dir)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Přístup k příloze není povolen.") from exc

        if not attachment_path.exists():
            raise HTTPException(status_code=404, detail="Soubor přílohy neexistuje.")

        return FileResponse(attachment_path)

    def _apply_email_action(email_id: str, payload: EmailActionPayload) -> dict[str, object]:
        email_model = crud.get_email(active_config, email_id)
        if email_model is None:
            raise HTTPException(status_code=404, detail="E-mail nebyl nalezen.")

        email = _email_entity(email_model)
        action = payload.action

        if action == "create_task":
            classification = EmailClassification(
                category="task",
                action="create_task",
                priority=email.priority,
                needs_reply=False,
                confidence=1.0,
            )
            parsed = parser_service.parse_message(email, classification)
            if payload.project_id is not None:
                project = project_service.get_project(payload.project_id)
                if project is None:
                    raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
            task_id = task_service.create_task(
                title=(payload.title or "").strip() or email.subject,
                description=(payload.description or "").strip() or parsed.summary or email.body[:500],
                priority=(payload.priority or "").strip() or email.priority,
                due_date=(payload.due_date or "").strip() or parsed.requested_deadline,
                source_email_id=email.id,
                project_id=payload.project_id if payload.project_id is not None else email.project_id,
                assigned_worker_id=payload.assigned_worker_id,
                assigned_worker_ids=payload.assigned_worker_ids,
                estimated_hours=payload.estimated_hours,
            )
            crud.update_email_category(active_config, email.id, "task")
            crud.update_email_status(active_config, email.id, "confirmed")
            return {"status": "ok", "action": action, "created_task_id": task_id}

        if action == "create_project":
            parsed = parser_service.parse_message(
                email,
                EmailClassification(
                    category="new_order",
                    action="create_project",
                    priority=email.priority,
                    needs_reply=False,
                    confidence=1.0,
                ),
            )
            project_id = project_service.create_project(
                name=parsed.company_name or email.subject[:80] or f"Zakazka {email.id[:8]}",
                description=parsed.requested_action or parsed.summary,
                customer_name=parsed.customer_name or parsed.company_name,
                contact_person=parsed.contact,
                contact_email=email.sender,
                address=parsed.address,
                priority=email.priority,
            )
            project_service.assign_email(email.id, project_id)
            project_document_service.import_email_attachments(project_id=project_id, email_id=email.id)
            crud.update_email_category(active_config, email.id, "new_order")
            crud.update_email_status(active_config, email.id, "confirmed")
            return {"status": "ok", "action": action, "project_id": project_id}

        if action == "assign_project":
            if payload.project_id is None:
                raise HTTPException(status_code=400, detail="Chybí project_id pro přiřazení.")
            project = project_service.get_project(payload.project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
            created_link = project_service.assign_email(email.id, payload.project_id)
            if created_link:
                project_document_service.import_email_attachments(
                    project_id=payload.project_id,
                    email_id=email.id,
                )
            crud.update_email_status(active_config, email.id, "confirmed")
            return {"status": "ok", "action": action, "project_id": payload.project_id}

        if action == "create_invoice":
            classification = EmailClassification(
                category="invoice",
                action="create_invoice",
                priority=email.priority,
                needs_reply=False,
                confidence=1.0,
            )
            parsed = parser_service.parse_message(email, classification)
            pdf_attachment = next(
                (attachment for attachment in email.attachments if attachment.lower().endswith(".pdf")),
                "",
            )
            invoice_id = invoice_service.create_invoice(
                supplier=parsed.company_name or parsed.contact or email.sender,
                invoice_number=parsed.invoice_number,
                amount=parsed.invoice_amount,
                currency=parsed.invoice_currency,
                due_date=parsed.invoice_due_date,
                source_email_id=email.id,
                attachment_path=pdf_attachment,
                project_id=email.project_id,
            )
            crud.update_email_category(active_config, email.id, "invoice")
            crud.update_email_status(active_config, email.id, "confirmed")
            if parsed.invoice_due_date:
                reminder_service.create_reminder(
                    title=f"Splatnost faktury: {parsed.invoice_number or email.subject}",
                    remind_at=parsed.invoice_due_date,
                    notes=parsed.summary,
                    related_type="invoice",
                    related_id=email.id,
                )
            return {"status": "ok", "action": action, "created_invoice_id": invoice_id}

        if action == "track":
            crud.update_email_category(active_config, email.id, "general")
            crud.update_email_status(active_config, email.id, "confirmed")
            return {"status": "ok", "action": action}

        if action == "ignore":
            crud.update_email_category(active_config, email.id, "general")
            crud.update_email_status(active_config, email.id, "confirmed")
            return {"status": "ok", "action": action}

        if action == "mark_invoice":
            crud.update_email_category(active_config, email.id, "invoice")
            crud.update_email_status(active_config, email.id, "confirmed")
            return {"status": "ok", "action": action}

        if action == "archive":
            crud.update_email_status(active_config, email.id, "archived")
            return {"status": "ok", "action": action}

        if action == "restore":
            crud.update_email_status(active_config, email.id, "pending")
            return {"status": "ok", "action": action}

        if action == "return_unprocessed":
            project_service.clear_email_assignments(email.id)
            crud.update_email_category(active_config, email.id, "uncategorized")
            crud.update_email_status(active_config, email.id, "pending")
            return {"status": "ok", "action": action}

        if action == "create_calendar_event":
            classification = EmailClassification(
                category="calendar",
                action="create_calendar_event",
                priority=email.priority,
                needs_reply=False,
                confidence=1.0,
            )
            parsed = parser_service.parse_message(email, classification)
            if not parsed.requested_deadline:
                raise HTTPException(status_code=400, detail="V e-mailu nebyl nalezen termín.")
            event_id = calendar_service.create_event_proposal(
                title=email.subject,
                starts_at=parsed.requested_deadline,
                ends_at=parsed.requested_deadline,
                description=parsed.summary or email.body[:500],
                location=parsed.address,
                priority=email.priority,
                source_email_id=email.id,
                project_id=email.project_id,
            )
            crud.update_email_category(active_config, email.id, "calendar")
            crud.update_email_status(active_config, email.id, "confirmed")
            stored_event = crud.get_calendar_event(active_config, event_id)
            return {
                "status": "ok",
                "action": action,
                "created_event_id": event_id,
                "synced_to_google": bool(stored_event and stored_event.external_event_id),
                "calendar_id": stored_event.calendar_id if stored_event else "",
                "external_event_id": stored_event.external_event_id if stored_event else "",
            }

        raise HTTPException(status_code=400, detail="Neznámá akce pro e-mail.")

    @app.post("/api/emails/{email_id}/action")
    def apply_email_action(email_id: str, payload: EmailActionPayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        return _apply_email_action(email_id, payload)

    @app.post("/api/emails/bulk-action")
    def apply_bulk_email_action(payload: BulkEmailActionPayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        if not payload.email_ids:
            raise HTTPException(status_code=400, detail="Nebyl vybrán žádný e-mail.")

        result_items = [
            _apply_email_action(
                email_id,
                EmailActionPayload(action=payload.action, project_id=payload.project_id),
            )
            for email_id in payload.email_ids
        ]
        return {"status": "ok", "processed": len(result_items), "items": result_items}

    @app.post("/api/tasks/{task_id}/action")
    def apply_task_action(task_id: int, payload: TaskActionPayload, request: Request) -> dict[str, object]:
        user = current_user(request)
        if user.role not in {ROLE_OWNER, ROLE_ADMIN}:
            raise HTTPException(status_code=403, detail="Na tuto akci nemáš oprávnění.")
        task = next((item for item in task_service.list_tasks() if item.id == task_id), None)
        if task is None:
            raise HTTPException(status_code=404, detail="Úkol nebyl nalezen.")

        if payload.action == "complete":
            task_service.complete_task(task_id, completed_by_user_id=user.id)
            return {"status": "ok", "action": payload.action}

        if payload.action == "archive":
            task_service.archive_task(task_id)
            return {"status": "ok", "action": payload.action}

        if payload.action == "reopen":
            crud.update_task_status(active_config, task_id, "pending")
            return {"status": "ok", "action": payload.action}

        if payload.action == "assign_project":
            if payload.project_id is None:
                raise HTTPException(status_code=400, detail="Chybí project_id pro přiřazení.")
            project = project_service.get_project(payload.project_id)
            if project is None:
                raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
            project_service.assign_task(task_id, payload.project_id)
            return {"status": "ok", "action": payload.action, "project_id": payload.project_id}

        if payload.action == "create_calendar_event":
            if not task.due_date:
                raise HTTPException(status_code=400, detail="Úkol nemá zadaný termín.")
            project = (
                project_service.get_project(task.project_id)
                if task.project_id is not None
                else None
            )
            worker_ids = list(
                dict.fromkeys(
                    (task.worker_ids or [])
                    + ([task.assigned_worker_id] if task.assigned_worker_id is not None else [])
                )
            )
            attendee_emails: list[str] = []
            for worker_id in worker_ids:
                worker = crud.get_worker(active_config, int(worker_id))
                if worker is None or not worker.email:
                    continue
                normalized_email = worker.email.strip()
                if normalized_email and normalized_email not in attendee_emails:
                    attendee_emails.append(normalized_email)
            event_title = f"{project.name} – {task.title}" if project is not None else task.title
            existing_event = next(
                (
                    item for item in crud.list_calendar_events(active_config)
                    if item.task_id == task_id
                    and (item.title or "") == event_title
                    and (item.starts_at or "") == (task.due_date or "")
                    and (item.ends_at or item.starts_at or "") == (task.due_date or "")
                ),
                None,
            )
            if existing_event is not None:
                crud.update_task_status(active_config, task_id, "scheduled")
                return {
                    "status": "ok",
                    "action": payload.action,
                    "created_event_id": existing_event.id,
                    "synced_to_google": bool(existing_event.external_event_id),
                    "calendar_id": existing_event.calendar_id,
                    "external_event_id": existing_event.external_event_id,
                    "invited_workers": len(existing_event.attendee_emails or attendee_emails),
                }
            event_id = calendar_service.create_event_proposal(
                title=event_title,
                starts_at=task.due_date,
                ends_at=task.due_date,
                description=task.description,
                location=project.address if project is not None else "",
                priority=task.priority,
                source_email_id=task.source_email_id,
                task_id=task_id,
                project_id=task.project_id,
                assigned_worker_id=task.assigned_worker_id,
                attendee_emails=attendee_emails,
            )
            stored_event = crud.get_calendar_event(active_config, event_id)
            synced_to_google = bool(stored_event and stored_event.external_event_id)
            crud.update_task_status(active_config, task_id, "scheduled")
            return {
                "status": "ok",
                "action": payload.action,
                "created_event_id": event_id,
                "synced_to_google": synced_to_google,
                "calendar_id": stored_event.calendar_id if stored_event else "",
                "external_event_id": stored_event.external_event_id if stored_event else "",
                "invited_workers": len(attendee_emails),
            }

        raise HTTPException(status_code=400, detail="Neznámá akce pro úkol.")

    @app.post("/api/tasks/bulk-action")
    def apply_bulk_task_action(payload: BulkTaskActionPayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        if not payload.task_ids:
            raise HTTPException(status_code=400, detail="Nebyl vybrán žádný úkol.")

        result_items = [
            apply_task_action(
                task_id,
                TaskActionPayload(action=payload.action, project_id=payload.project_id),
                request,
            )
            for task_id in payload.task_ids
        ]
        return {"status": "ok", "processed": len(result_items), "items": result_items}

    @app.delete("/api/emails/{email_id}")
    def delete_email(email_id: str, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        deleted = crud.delete_email(active_config, email_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="E-mail nebyl nalezen.")
        return {"status": "ok"}

    @app.post("/api/emails/{email_id}/delete")
    def delete_email_post(email_id: str, request: Request) -> dict[str, object]:
        return delete_email(email_id, request)

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: int, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        deleted = task_service.delete_task(task_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Úkol nebyl nalezen.")
        return {"status": "ok"}

    @app.post("/api/tasks/{task_id}/delete")
    def delete_task_post(task_id: int, request: Request) -> dict[str, object]:
        return delete_task(task_id, request)

    @app.get("/api/projects")
    def list_projects(request: Request) -> dict[str, object]:
        user = current_user(request)
        return {"items": _serialize_many(filter_projects_for_user(user, list(project_service.list_projects())))}

    @app.post("/api/projects")
    def create_project(payload: ProjectCreatePayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        project_id = project_service.create_project(**payload.model_dump())
        project = project_service.get_project(project_id)
        return {"item": asdict(project) if project else None}

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: int, request: Request) -> dict[str, object]:
        user = current_user(request)
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
        if user.role == ROLE_WORKER and project_id not in get_worker_visible_project_ids(user):
            raise HTTPException(status_code=403, detail="Na tuto zakázku nemáš oprávnění.")

        emails, tasks, invoices, work_logs, timeline_events = project_service.get_project_summary(project_id)
        return {
            "item": asdict(project),
            "finance": project_service.get_project_finance_summary(project_id),
            "emails": [_serialize_email(active_config, item) for item in emails],
            "tasks": [_serialize_task(active_config, item) for item in tasks],
            "invoices": _serialize_many(list(invoices)),
            "work_logs": _serialize_many(list(work_logs)),
            "timeline_events": _serialize_many(list(timeline_events)),
            "documents": [
                _serialize_document(item)
                for item in project_document_service.list_documents(project_id)
            ],
            "worker_rates": _serialize_many(list(worklog_service.list_project_worker_rates(project_id))),
        }

    @app.put("/api/projects/{project_id}")
    def update_project(project_id: int, payload: ProjectCreatePayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        updated = project_service.update_project(project_id, **payload.model_dump())
        if not updated:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")

        project = project_service.get_project(project_id)
        return {"item": asdict(project) if project else None}

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: int, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
        project_document_service.delete_documents_for_project(project_id)
        project_service.delete_project(project_id)
        return {"status": "ok"}

    @app.post("/api/projects/{project_id}/delete")
    def delete_project_post(project_id: int, request: Request) -> dict[str, object]:
        return delete_project(project_id, request)

    @app.post("/api/projects/{project_id}/tasks")
    def create_project_task(
        project_id: int,
        payload: ProjectTaskCreatePayload,
        request: Request,
    ) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")

        task_id = task_service.create_task(
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
            project_id=project_id,
            assigned_worker_id=payload.assigned_worker_id,
            assigned_worker_ids=payload.assigned_worker_ids,
            estimated_hours=payload.estimated_hours,
        )
        task = next((item for item in task_service.list_tasks() if item.id == task_id), None)
        return {"item": _serialize_task(active_config, task) if task else None}

    @app.get("/api/project-worker-rates")
    def list_project_worker_rates(request: Request, project_id: int | None = None) -> dict[str, object]:
        user = current_user(request)
        items = list(worklog_service.list_project_worker_rates(project_id)) if project_id is not None else list(crud.list_project_worker_rates(active_config))
        allowed_project_ids = {item.id for item in filter_projects_for_user(user, list(project_service.list_projects()))}
        return {"items": [asdict(item) for item in items if item.project_id in allowed_project_ids]}

    @app.post("/api/projects/{project_id}/worker-rates")
    def upsert_project_worker_rates(
        project_id: int,
        payload: ProjectWorkerRateBulkPayload,
        request: Request,
    ) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
        for item in payload.items:
            if item.payout_rate is None or float(item.payout_rate) <= 0:
                worklog_service.delete_project_worker_rate(project_id=project_id, worker_id=item.worker_id)
            else:
                worklog_service.set_project_worker_rate(
                    project_id=project_id,
                    worker_id=item.worker_id,
                    payout_rate=item.payout_rate,
                )
        return {"items": _serialize_many(list(worklog_service.list_project_worker_rates(project_id)))}

    @app.get("/api/workers")
    def list_workers(request: Request) -> dict[str, object]:
        user = current_user(request)
        return {"items": _serialize_many(filter_workers_for_user(user, list(worker_service.list_workers())))}

    @app.post("/api/workers")
    def create_worker(payload: WorkerCreatePayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        worker_id = worker_service.create_worker(**payload.model_dump())
        worker = worker_service.get_worker(worker_id)
        return {"item": asdict(worker) if worker else None}

    @app.put("/api/workers/{worker_id}")
    def update_worker(worker_id: int, payload: WorkerCreatePayload, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        updated = worker_service.update_worker(worker_id, **payload.model_dump())
        if not updated:
            raise HTTPException(status_code=404, detail="Pracovník nebyl nalezen.")
        worker = worker_service.get_worker(worker_id)
        return {"item": asdict(worker) if worker else None}

    @app.delete("/api/workers/{worker_id}")
    def delete_worker(worker_id: int, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER)
        deleted = worker_service.delete_worker(worker_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Pracovník nebyl nalezen.")
        return {"status": "ok"}

    @app.post("/api/workers/{worker_id}/delete")
    def delete_worker_post(worker_id: int, request: Request) -> dict[str, object]:
        return delete_worker(worker_id, request)

    @app.get("/api/worklogs")
    def list_work_logs(request: Request, project_id: int | None = None, worker_id: int | None = None) -> dict[str, object]:
        user = current_user(request)
        effective_worker_id = worker_id
        if user.role == ROLE_WORKER:
            effective_worker_id = user.worker_id
            if project_id is not None and project_id not in get_worker_visible_project_ids(user):
                raise HTTPException(status_code=403, detail="Na tuto zakázku nemáš oprávnění.")
        work_logs = worklog_service.list_work_logs(project_id=project_id, worker_id=effective_worker_id)
        return {"items": _serialize_many(filter_worklogs_for_user(user, list(work_logs)))}

    @app.get("/api/worklogs/summary")
    def list_work_log_summary(request: Request) -> dict[str, object]:
        user = current_user(request)
        items = worklog_service.get_payment_summary()
        if user.role == ROLE_WORKER and user.worker_id is not None:
            items = [item for item in items if item.get("worker_id") == user.worker_id]
        return {"items": items}

    @app.post("/api/worklogs")
    def create_work_log(payload: WorkLogCreatePayload, request: Request) -> dict[str, object]:
        user = current_user(request)
        if user.role == ROLE_WORKER:
            if user.worker_id is None or payload.worker_id != user.worker_id:
                raise HTTPException(status_code=403, detail="Pracovník může zapisovat jen svou práci.")
            if payload.project_id not in get_worker_visible_project_ids(user):
                raise HTTPException(status_code=403, detail="Na tuto zakázku nemáš oprávnění.")
        work_log_id = worklog_service.create_work_log(**payload.model_dump())
        work_logs = worklog_service.list_work_logs()
        created = next((item for item in work_logs if item.id == work_log_id), None)
        return {"item": asdict(created) if created else None}

    @app.post("/api/worklogs/{work_log_id}/payment")
    def update_work_log_payment(
        work_log_id: int,
        payload: WorkLogPaymentPayload,
        request: Request,
    ) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        updated = worklog_service.set_payment_status(work_log_id, is_paid=payload.is_paid)
        if not updated:
            raise HTTPException(status_code=404, detail="Výkaz práce nebyl nalezen.")

        item = next((entry for entry in worklog_service.list_work_logs() if entry.id == work_log_id), None)
        return {"item": asdict(item) if item else None}

    @app.post("/api/worklogs/project-payment")
    def update_project_work_logs_payment(
        payload: WorkLogSummaryPaymentPayload,
        request: Request,
    ) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        updated_count = worklog_service.set_project_worker_payment_status(
            project_id=payload.project_id,
            worker_id=payload.worker_id,
            is_paid=payload.is_paid,
        )
        if updated_count <= 0:
            raise HTTPException(status_code=404, detail="Pro tuto zakázku a pracovníka nebyly nalezeny žádné výkazy.")
        return {"status": "ok", "updated_count": updated_count}

    @app.delete("/api/worklogs/{work_log_id}")
    def delete_work_log(work_log_id: int, request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        deleted = worklog_service.delete_work_log(work_log_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Výkaz práce nebyl nalezen.")
        return {"status": "ok"}

    @app.post("/api/worklogs/{work_log_id}/delete")
    def delete_work_log_post(work_log_id: int, request: Request) -> dict[str, object]:
        return delete_work_log(work_log_id, request)

    @app.get("/api/invoices")
    def list_invoices(request: Request) -> dict[str, object]:
        require_roles(request, ROLE_OWNER, ROLE_ADMIN)
        invoices = list(invoice_service.list_invoices())
        return {"items": _serialize_many(invoices)}

    @app.get("/api/projects/{project_id}/documents")
    def list_project_documents(project_id: int, request: Request) -> dict[str, object]:
        user = current_user(request)
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
        if user.role == ROLE_WORKER and project_id not in get_worker_visible_project_ids(user):
            raise HTTPException(status_code=403, detail="Na tuto zakázku nemáš oprávnění.")
        return {
            "items": [
                _serialize_document(item)
                for item in project_document_service.list_documents(project_id)
            ]
        }

    @app.post("/api/projects/{project_id}/documents")
    async def upload_project_document(
        request: Request,
        project_id: int,
        file: UploadFile = File(...),
        title: str = Form(""),
        document_type: str = Form("general"),
        worker_id: int | None = Form(None),
        work_date: str | None = Form(None),
    ) -> dict[str, object]:
        user = current_user(request)
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Zakázka nebyla nalezena.")
        if user.role == ROLE_WORKER and project_id not in get_worker_visible_project_ids(user):
            raise HTTPException(status_code=403, detail="Na tuto zakázku nemáš oprávnění.")
        effective_worker_id = worker_id
        if user.role == ROLE_WORKER:
            if user.worker_id is None:
                raise HTTPException(status_code=403, detail="Pracovník není navázaný na účet.")
            effective_worker_id = user.worker_id
        content = await file.read()
        document_id = project_document_service.save_document(
            project_id=project_id,
            filename=file.filename or "soubor",
            content=content,
            title=title,
            document_type=document_type,
            worker_id=effective_worker_id,
            work_date=work_date,
        )
        document = project_document_service.get_document(document_id)
        return {"item": _serialize_document(document) if document else None}

    @app.get("/api/project-documents/{document_id}/file")
    def get_project_document_file(document_id: int, request: Request) -> FileResponse:
        user = current_user(request)
        document = project_document_service.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Dokument nebyl nalezen.")
        if user.role == ROLE_WORKER and document.project_id not in get_worker_visible_project_ids(user):
            raise HTTPException(status_code=403, detail="Na tento dokument nemáš oprávnění.")
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Soubor dokumentu neexistuje.")
        return FileResponse(file_path)

    return app






