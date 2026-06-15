from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from multiprocessing import Process
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import Worker
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
        google_calendar_token_path=root / "data" / "google_calendar_token.json",
        idoklad_client_id="",
        idoklad_client_secret="",
    )


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def serve_app(temp_dir: str, port: int) -> None:
    import uvicorn

    config = build_temp_config(Path(temp_dir))
    initialize_database(config)
    crud.create_worker(
        config,
        Worker(full_name="E2E Worker", email="e2e.worker@example.com"),
    )
    app = create_app(config)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def wait_for_server(base_url: str, timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"E2E server did not start in time: {last_error}")


def ensure_playwright_ready() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:  # pragma: no cover - local runtime check
        raise RuntimeError(
            "Playwright není nainstalovaný. Spusť `python -m pip install playwright` "
            "a potom `python -m playwright install chromium`."
        ) from exc


def get_browser_launch_options() -> dict[str, object]:
    edge_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if edge_path.exists():
        return {"headless": True, "channel": "msedge"}
    if chrome_path.exists():
        return {"headless": True, "channel": "chrome"}
    return {"headless": True}


def dismiss_message_dialog(page: object) -> None:
    page.wait_for_timeout(200)
    close_button = page.locator("[data-close-message-dialog]")
    if close_button.count() and close_button.first.is_visible():
        close_button.first.click()
        page.wait_for_timeout(100)
        return
    page.evaluate(
        """
        () => {
          const dialog = document.querySelector('#message-dialog');
          if (dialog && dialog.open) {
            dialog.close();
          }
        }
        """
    )
    page.wait_for_timeout(100)


def run_browser_flow(base_url: str) -> None:
    from playwright.sync_api import expect, sync_playwright

    now = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    planned_start = now.isoformat(timespec="minutes")
    planned_end = (now + timedelta(hours=2)).isoformat(timespec="minutes")
    deadline = (now + timedelta(hours=4)).isoformat(timespec="minutes")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**get_browser_launch_options())
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        page.goto(base_url, wait_until="domcontentloaded")

        page.locator("#login-form input[name=login]").fill("pepa")
        page.locator("#login-form input[name=password]").fill("p")
        page.locator("#login-form button[type=submit]").click()
        dismiss_message_dialog(page)
        expect(page.locator(".dashboard-calendar-layout")).to_be_visible()

        page.locator('[data-view="tasks"]').click(force=True)
        expect(page.locator('[data-open-task-dialog]')).to_be_visible()
        page.locator("[data-open-task-dialog]").first.click()
        expect(page.locator("#task-form")).to_be_visible()
        expect(page.locator('#task-form input[name="deadline_at"]')).to_have_attribute(
            "placeholder",
            "Deadline: dokdy musí být hotovo",
        )
        expect(page.locator('#task-form input[name="planned_start_at"]')).to_have_attribute(
            "placeholder",
            "Začátek práce: blok v kalendáři",
        )
        expect(page.locator('#task-form input[name="planned_end_at"]')).to_have_attribute(
            "placeholder",
            "Konec práce: konec bloku v kalendáři",
        )
        page.locator('#task-form input[name="title"]').fill("E2E plánovaný úkol")
        page.locator('#task-form select[name="priority"]').select_option("high")
        page.locator('#task-form input[name="deadline_at"]').fill(deadline)
        page.locator('#task-form input[name="planned_start_at"]').fill(planned_start)
        page.locator('#task-form input[name="planned_end_at"]').fill(planned_end)
        page.locator('#task-form select[name="assigned_worker_ids"]').select_option(label="E2E Worker")
        page.locator('#task-form input[name="estimated_hours"]').fill("2")
        page.locator('#task-form textarea[name="description"]').fill("Browser E2E ověření plánování.")
        page.locator('#task-form button[type="submit"]').click()
        dismiss_message_dialog(page)
        expect(page.locator(".list-stack")).to_contain_text("E2E plánovaný úkol")

        page.locator('[data-select-item^="task:"]').filter(has_text="E2E plánovaný úkol").click()
        expect(page.locator(".hero-title")).to_contain_text("E2E plánovaný úkol")
        page.locator('[data-task-action="create_calendar_event"]').click()
        expect(page.locator(".message-dialog-text")).to_contain_text("Dashboard plán už je vidět automaticky.")
        page.locator("[data-close-message-dialog]").click()

        page.locator('[data-view="dashboard"]').click(force=True)
        expect(page.locator(".dashboard-calendar-layout")).to_be_visible()
        expect(page.locator(".dashboard-calendar-layout")).to_contain_text("E2E plánovaný úkol")

        browser.close()


def main() -> None:
    ensure_playwright_ready()
    with tempfile.TemporaryDirectory() as temp_dir:
        port = find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = Process(target=serve_app, args=(temp_dir, port), daemon=True)
        process.start()
        try:
            wait_for_server(base_url)
            print("== Running browser E2E test ==")
            run_browser_flow(base_url)
            print("== Browser E2E passed ==")
        finally:
            process.terminate()
            process.join(timeout=5)


if __name__ == "__main__":
    main()
