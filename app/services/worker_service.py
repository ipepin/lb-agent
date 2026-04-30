from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import WorkerModel
from app.schemas.entities import Worker


class WorkerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def create_worker(
        self,
        full_name: str,
        *,
        role: str = "",
        email: str = "",
        phone: str = "",
        hourly_rate: float | None = None,
        payout_rate: float | None = None,
        status: str = "active",
    ) -> int:
        worker = Worker(
            full_name=full_name.strip(),
            role=role.strip(),
            email=email.strip(),
            phone=phone.strip(),
            hourly_rate=hourly_rate,
            payout_rate=payout_rate,
            status=status,
        )
        return crud.create_worker(self.config, worker)

    def list_workers(self) -> Sequence[WorkerModel]:
        return crud.list_workers(self.config)

    def get_worker(self, worker_id: int) -> WorkerModel | None:
        return crud.get_worker(self.config, worker_id)

    def update_worker(
        self,
        worker_id: int,
        *,
        full_name: str,
        role: str = "",
        email: str = "",
        phone: str = "",
        hourly_rate: float | None = None,
        payout_rate: float | None = None,
        status: str = "active",
    ) -> bool:
        worker = Worker(
            full_name=full_name.strip(),
            role=role.strip(),
            email=email.strip(),
            phone=phone.strip(),
            hourly_rate=hourly_rate,
            payout_rate=payout_rate,
            status=status,
        )
        return crud.update_worker(self.config, worker_id, worker)

    def delete_worker(self, worker_id: int) -> bool:
        return crud.delete_worker(self.config, worker_id)
