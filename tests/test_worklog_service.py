import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db.database import initialize_database
from app.services.project_service import ProjectService
from app.services.worker_service import WorkerService
from app.services.worklog_service import WorkLogService


class TestWorkLogService(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.config = AppConfig(
            project_root=root,
            data_dir=root / "data",
            attachments_dir=root / "data" / "attachments",
            db_path=root / "data" / "app.db",
            sync_state_path=root / "data" / "last_sync.txt",
            agent_poll_interval_seconds=60,
            notification_channel="log",
            gmail_credentials_path=root / "credentials.json",
            gmail_token_path=root / "data" / "gmail_token.json",
            gmail_query="-in:spam -in:trash -in:sent",
            openai_api_key="",
            openai_model="gpt-5.4-mini",
            openai_reasoning_effort="low",
            google_calendar_id="",
            idoklad_client_id="",
            idoklad_client_secret="",
        )
        initialize_database(self.config)
        self.project_service = ProjectService(self.config)
        self.worker_service = WorkerService(self.config)
        self.worklog_service = WorkLogService(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_work_log_and_project_finance_summary(self) -> None:
        project_id = self.project_service.create_project(
            "Zakazka Delta",
            customer_name="ACME",
            budget_amount=100000.0,
        )
        worker_id = self.worker_service.create_worker(
            "Jan Novak",
            role="Technik",
            hourly_rate=400.0,
            payout_rate=250.0,
        )

        log_id = self.worklog_service.create_work_log(
            project_id=project_id,
            worker_id=worker_id,
            work_date="2026-04-17",
            hours=6.5,
            material_cost=800.0,
            payout_amount=1625.0,
            billable_amount=2600.0,
            notes="Montaz a test",
        )

        self.assertGreater(log_id, 0)

        logs = list(self.worklog_service.list_work_logs(project_id=project_id))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].worker_id, worker_id)
        self.assertEqual(logs[0].hours, 6.5)

        finance = self.project_service.get_project_finance_summary(project_id)
        self.assertEqual(finance["payout_total"], 1625.0)
        self.assertEqual(finance["material_total"], 800.0)
        self.assertEqual(finance["labor_hours"], 6.5)

    def test_create_work_log_calculates_payout_from_worker_rate(self) -> None:
        project_id = self.project_service.create_project("Zakazka Sazba")
        worker_id = self.worker_service.create_worker(
            "Petr Dvorak",
            payout_rate=300.0,
        )

        self.worklog_service.create_work_log(
            project_id=project_id,
            worker_id=worker_id,
            work_date="2026-04-18",
            hours=4.0,
            notes="Pomocne prace",
        )

        logs = list(self.worklog_service.list_work_logs(project_id=project_id))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].payout_amount, 1200.0)

    def test_payment_summary_uses_worker_rate_when_payout_amount_missing(self) -> None:
        project_id = self.project_service.create_project("Zakazka Souhrn")
        worker_id = self.worker_service.create_worker(
            "Roman Kral",
            hourly_rate=350.0,
        )

        self.worklog_service.create_work_log(
            project_id=project_id,
            worker_id=worker_id,
            work_date="2026-04-19",
            hours=2.5,
            payout_amount=None,
            notes="Bez ručně zadané částky",
        )

        summary = self.worklog_service.get_payment_summary()
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["payout_total"], 875.0)
        self.assertEqual(summary[0]["unpaid_total"], 875.0)

    def test_create_work_log_prefers_project_worker_rate(self) -> None:
        project_id = self.project_service.create_project("Zakazka Extra Sazba")
        worker_id = self.worker_service.create_worker(
            "Ladislav Belani",
            payout_rate=350.0,
        )
        self.worklog_service.set_project_worker_rate(
            project_id=project_id,
            worker_id=worker_id,
            payout_rate=500.0,
        )

        self.worklog_service.create_work_log(
            project_id=project_id,
            worker_id=worker_id,
            work_date="2026-05-13",
            hours=8.0,
            material_cost=200.0,
            payout_amount=None,
        )

        logs = list(self.worklog_service.list_work_logs(project_id=project_id))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].payout_amount, 4200.0)


if __name__ == "__main__":
    unittest.main()
