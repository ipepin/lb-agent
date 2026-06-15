from __future__ import annotations

from collections import Counter

from app.config import AppConfig
from app.db import crud


class DashboardService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def get_snapshot(self) -> dict[str, object]:
        emails = list(crud.list_emails(self.config))
        tasks = list(crud.list_tasks(self.config))
        invoices = list(crud.list_invoices(self.config))
        reminders = list(crud.list_reminders(self.config))
        approvals = list(crud.list_approval_items(self.config))
        projects = list(crud.list_projects(self.config))
        workers = list(crud.list_workers(self.config))
        work_logs = list(crud.list_work_logs(self.config))
        triage_stats = self._build_triage_stats(emails)

        return {
            "counts": {
                "emails": len(emails),
                "unprocessed_emails": sum(
                    1
                    for item in emails
                    if item.category == "uncategorized" and item.status != "archived"
                ),
                "open_tasks": sum(
                    1 for item in tasks if item.status not in {"done", "archived"}
                ),
                "pending_approvals": sum(1 for item in approvals if item.status == "pending"),
                "active_projects": sum(
                    1 for item in projects if item.status not in {"done", "closed", "archived"}
                ),
                "workers": len(workers),
                "work_logs": len(work_logs),
                "pending_invoices": sum(
                    1 for item in invoices if item.status not in {"paid", "archived"}
                ),
                "due_reminders": sum(
                    1 for item in reminders if item.status not in {"done", "archived"}
                ),
            },
            "finance": {
                "invoice_total": round(sum(item.amount or 0 for item in invoices), 2),
                "material_total": round(sum(item.material_cost or 0 for item in work_logs), 2),
                "payout_total": round(sum(item.payout_amount or 0 for item in work_logs), 2),
                "paid_payout_total": round(
                    sum(item.payout_amount or 0 for item in work_logs if item.payment_status == "paid"),
                    2,
                ),
                "unpaid_payout_total": round(
                    sum(item.payout_amount or 0 for item in work_logs if item.payment_status != "paid"),
                    2,
                ),
                "billable_total": round(sum(item.billable_amount or 0 for item in work_logs), 2),
            },
            "triage": triage_stats,
        }

    def _build_triage_stats(self, emails: list[object]) -> dict[str, object]:
        ai_emails = [item for item in emails if getattr(item, "ai_payload", None)]
        decisions = [
            getattr(item, "ai_payload", {}).get("user_decision") or {}
            for item in ai_emails
        ]
        confirmed = [item for item in decisions if item.get("action")]
        matched = [item for item in confirmed if item.get("matches_ai_suggestion") is True]
        mismatched = [item for item in confirmed if item.get("matches_ai_suggestion") is False]
        top_suggested_actions = Counter(
            str((getattr(item, "ai_payload", {}).get("classification") or {}).get("action") or "").strip()
            for item in ai_emails
            if str((getattr(item, "ai_payload", {}).get("classification") or {}).get("action") or "").strip()
        )
        top_confirmed_actions = Counter(
            str(item.get("action") or "").strip()
            for item in confirmed
            if str(item.get("action") or "").strip()
        )

        return {
            "suggested_total": len(ai_emails),
            "confirmed_total": len(confirmed),
            "matched_total": len(matched),
            "mismatched_total": len(mismatched),
            "pending_review_total": max(len(ai_emails) - len(confirmed), 0),
            "top_suggested_actions": [
                {"action": action, "count": count}
                for action, count in top_suggested_actions.most_common(4)
            ],
            "top_confirmed_actions": [
                {"action": action, "count": count}
                for action, count in top_confirmed_actions.most_common(4)
            ],
        }
