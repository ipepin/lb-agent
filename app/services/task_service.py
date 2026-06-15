from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import TaskModel
from app.schemas.entities import Task


class TaskService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "normal",
        status: str = "pending",
        due_date: str | None = None,
        deadline_at: str | None = None,
        planned_start_at: str | None = None,
        planned_end_at: str | None = None,
        source_email_id: str | None = None,
        project_id: int | None = None,
        assigned_worker_id: int | None = None,
        assigned_worker_ids: list[int] | None = None,
        estimated_hours: float | None = None,
    ) -> int:
        normalized_worker_ids = list(dict.fromkeys(assigned_worker_ids or []))
        if assigned_worker_id is not None and assigned_worker_id not in normalized_worker_ids:
            normalized_worker_ids.insert(0, assigned_worker_id)
        primary_worker_id = normalized_worker_ids[0] if normalized_worker_ids else assigned_worker_id

        task = Task(
            title=title,
            description=description,
            priority=priority,
            status=status,
            due_date=deadline_at or due_date,
            deadline_at=deadline_at or due_date,
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
            source_email_id=source_email_id,
            project_id=project_id,
            assigned_worker_id=primary_worker_id,
            estimated_hours=estimated_hours,
        )
        task_id = crud.create_task(self.config, task)
        if normalized_worker_ids:
            crud.set_task_worker_ids(self.config, task_id, normalized_worker_ids)
        elif primary_worker_id is not None:
            crud.set_task_worker_ids(self.config, task_id, [primary_worker_id])
        return task_id

    def list_tasks(self) -> Sequence[TaskModel]:
        return crud.list_tasks(self.config)

    def update_task(
        self,
        task_id: int,
        *,
        title: str,
        description: str = "",
        priority: str = "normal",
        status: str = "pending",
        due_date: str | None = None,
        deadline_at: str | None = None,
        planned_start_at: str | None = None,
        planned_end_at: str | None = None,
        project_id: int | None = None,
        assigned_worker_id: int | None = None,
        assigned_worker_ids: list[int] | None = None,
        estimated_hours: float | None = None,
        completed_by_user_id: int | None = None,
    ) -> bool:
        normalized_worker_ids = list(dict.fromkeys(assigned_worker_ids or []))
        if assigned_worker_id is not None and assigned_worker_id not in normalized_worker_ids:
            normalized_worker_ids.insert(0, assigned_worker_id)
        primary_worker_id = normalized_worker_ids[0] if normalized_worker_ids else assigned_worker_id

        updated = crud.update_task(
            self.config,
            task_id,
            title=title,
            description=description,
            priority=priority,
            status=status,
            due_date=deadline_at or due_date,
            deadline_at=deadline_at or due_date,
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
            project_id=project_id,
            assigned_worker_id=primary_worker_id,
            estimated_hours=estimated_hours,
            completed_by_user_id=completed_by_user_id,
        )
        if not updated:
            return False
        crud.set_task_worker_ids(
            self.config,
            task_id,
            normalized_worker_ids if normalized_worker_ids else ([primary_worker_id] if primary_worker_id is not None else []),
        )
        return True

    def complete_task(self, task_id: int, completed_by_user_id: int | None = None) -> bool:
        return crud.update_task_status(self.config, task_id, "done", completed_by_user_id=completed_by_user_id)

    def archive_task(self, task_id: int) -> bool:
        return crud.update_task_status(self.config, task_id, "archived")

    def delete_task(self, task_id: int) -> bool:
        return crud.delete_task(self.config, task_id)
