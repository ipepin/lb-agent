from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.config import AppConfig
from app.web.api import create_app


def build_temp_config(root: Path) -> AppConfig:
    return AppConfig(
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


def run_unittests() -> None:
    print("== Running unit tests ==")
    subprocess.run([sys.executable, "-m", "unittest"], check=True)


def run_api_smoke() -> None:
    print("== Running API smoke test ==")
    with tempfile.TemporaryDirectory() as temp_dir:
        config = build_temp_config(Path(temp_dir))
        app = create_app(config)
        client = TestClient(app)

        login_response = client.post(
            "/api/auth/login",
            json={
                "login": config.bootstrap_owner_email,
                "password": config.bootstrap_owner_password,
            },
        )
        login_response.raise_for_status()

        worker_response = client.post(
            "/api/workers",
            json={"full_name": "Smoke Worker", "email": "smoke@example.com"},
        )
        worker_response.raise_for_status()
        worker_id = worker_response.json()["item"]["id"]

        project_response = client.post(
            "/api/projects",
            json={"name": "Smoke Project", "description": "", "status": "new"},
        )
        project_response.raise_for_status()
        project_id = project_response.json()["item"]["id"]

        task_response = client.post(
            "/api/tasks",
            json={
                "title": "Smoke Task",
                "project_id": project_id,
                "assigned_worker_id": worker_id,
                "assigned_worker_ids": [worker_id],
                "deadline_at": "2026-06-20T15:00:00",
                "planned_start_at": "2026-06-20T13:00:00",
                "planned_end_at": "2026-06-20T15:00:00",
                "estimated_hours": 2,
            },
        )
        task_response.raise_for_status()
        task_id = task_response.json()["item"]["id"]

        dashboard_response = client.get("/api/dashboard")
        dashboard_response.raise_for_status()

        tasks_response = client.get("/api/tasks")
        tasks_response.raise_for_status()
        task_payload = next(item for item in tasks_response.json()["items"] if item["id"] == task_id)
        assert task_payload["planned_start_at"] == "2026-06-20T13:00:00"

        calendar_response = client.post(
            f"/api/tasks/{task_id}/action",
            json={"action": "create_calendar_event", "force": True},
        )
        calendar_response.raise_for_status()

        print("Smoke test passed:")
        print(f"- task_id={task_id}")
        print(f"- project_id={project_id}")
        print(f"- worker_id={worker_id}")


def main() -> None:
    run_unittests()
    run_api_smoke()
    print("== All checks passed ==")


if __name__ == "__main__":
    main()
