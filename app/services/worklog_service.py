from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import WorkLogModel
from app.schemas.entities import WorkLog
from app.utils.dates import utc_now_iso


def _resolve_worker_rate(worker: object | None) -> float | None:
    if worker is None:
        return None
    payout_rate = getattr(worker, "payout_rate", None)
    if payout_rate is not None and float(payout_rate) > 0:
        return float(payout_rate)
    hourly_rate = getattr(worker, "hourly_rate", None)
    if hourly_rate is not None and float(hourly_rate) > 0:
        return float(hourly_rate)
    return None


class WorkLogService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def create_work_log(
        self,
        *,
        project_id: int,
        worker_id: int,
        work_date: str,
        hours: float,
        notes: str = "",
        starts_at: str | None = None,
        ends_at: str | None = None,
        travel_km: float = 0.0,
        material_cost: float = 0.0,
        payout_amount: float | None = None,
        billable_amount: float | None = None,
        payment_status: str = "unpaid",
        paid_at: str | None = None,
    ) -> int:
        worker = crud.get_worker(self.config, worker_id)
        resolved_payout_amount = payout_amount
        if resolved_payout_amount is None and worker is not None:
            rate = _resolve_worker_rate(worker)
            if rate is not None:
                resolved_payout_amount = round(float(hours) * float(rate) + float(material_cost or 0), 2)

        work_log = WorkLog(
            project_id=project_id,
            worker_id=worker_id,
            work_date=work_date,
            hours=hours,
            notes=notes.strip(),
            starts_at=starts_at,
            ends_at=ends_at,
            travel_km=travel_km,
            material_cost=material_cost,
            payout_amount=resolved_payout_amount,
            billable_amount=billable_amount,
            payment_status=payment_status,
            paid_at=paid_at,
        )
        return crud.create_work_log(self.config, work_log)

    def list_work_logs(
        self,
        *,
        project_id: int | None = None,
        worker_id: int | None = None,
    ) -> Sequence[WorkLogModel]:
        return crud.list_work_logs(self.config, project_id=project_id, worker_id=worker_id)

    def resolve_payout_amount(self, item: WorkLogModel) -> float:
        if item.payout_amount is not None:
            return round(float(item.payout_amount), 2)
        worker = crud.get_worker(self.config, item.worker_id)
        if worker is None:
            return 0.0
        rate = _resolve_worker_rate(worker)
        if rate is None:
            return 0.0
        return round(float(item.hours or 0) * float(rate) + float(item.material_cost or 0), 2)

    def set_payment_status(self, work_log_id: int, *, is_paid: bool) -> bool:
        return crud.update_work_log_payment_status(
            self.config,
            work_log_id,
            payment_status="paid" if is_paid else "unpaid",
            paid_at=utc_now_iso() if is_paid else None,
        )

    def set_project_worker_payment_status(
        self,
        *,
        project_id: int,
        worker_id: int,
        is_paid: bool,
    ) -> int:
        return crud.update_work_logs_payment_status(
            self.config,
            project_id=project_id,
            worker_id=worker_id,
            payment_status="paid" if is_paid else "unpaid",
            paid_at=utc_now_iso() if is_paid else None,
        )

    def delete_work_log(self, work_log_id: int) -> bool:
        return crud.delete_work_log(self.config, work_log_id)

    def get_payment_summary(self) -> list[dict[str, object]]:
        work_logs = list(crud.list_work_logs(self.config))
        workers = {item.id: item for item in crud.list_workers(self.config)}
        projects = {item.id: item for item in crud.list_projects(self.config)}
        grouped: dict[tuple[int, int], dict[str, object]] = {}

        for item in work_logs:
            key = (item.worker_id, item.project_id)
            if key not in grouped:
                grouped[key] = {
                    "worker_id": item.worker_id,
                    "worker_name": workers.get(item.worker_id).full_name if workers.get(item.worker_id) else "-",
                    "project_id": item.project_id,
                    "project_name": projects.get(item.project_id).name if projects.get(item.project_id) else "-",
                    "hours": 0.0,
                    "payout_total": 0.0,
                    "paid_total": 0.0,
                    "unpaid_total": 0.0,
                    "entry_count": 0,
                }

            payout_amount = self.resolve_payout_amount(item)
            grouped_item = grouped[key]
            grouped_item["hours"] = round(float(grouped_item["hours"]) + float(item.hours or 0), 2)
            grouped_item["payout_total"] = round(float(grouped_item["payout_total"]) + payout_amount, 2)
            grouped_item["entry_count"] = int(grouped_item["entry_count"]) + 1
            if item.payment_status == "paid":
                grouped_item["paid_total"] = round(float(grouped_item["paid_total"]) + payout_amount, 2)
            else:
                grouped_item["unpaid_total"] = round(float(grouped_item["unpaid_total"]) + payout_amount, 2)

        return sorted(
            grouped.values(),
            key=lambda item: (
                str(item["worker_name"]).lower(),
                str(item["project_name"]).lower(),
            ),
        )
