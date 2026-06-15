import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import AppConfig
from app.db import crud
from app.schemas.entities import Email, Task, User, Worker
from app.services.auth_service import hash_password
from app.web.api import create_app


class TestWebApi(unittest.TestCase):
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
        self.client = TestClient(create_app(self.config))
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "login": self.config.bootstrap_owner_email,
                "password": self.config.bootstrap_owner_password,
            },
        )
        self.assertEqual(login_response.status_code, 200)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_root_page_and_dashboard_endpoint(self) -> None:
        root_response = self.client.get("/")
        dashboard_response = self.client.get("/api/dashboard")
        auth_response = self.client.get("/api/auth/me")

        self.assertEqual(root_response.status_code, 200)
        self.assertIn('<div id="app"></div>', root_response.text)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("counts", dashboard_response.json())
        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(auth_response.json()["item"]["role"], "owner")

    def test_worker_cannot_access_owner_email_endpoints(self) -> None:
        worker_id = crud.create_worker(
            self.config,
            Worker(full_name="Josef Pracovník", email="worker@example.com"),
        )
        crud.create_user(
            self.config,
            User(
                email="worker@example.com",
                password_hash=hash_password("tajneheslo"),
                full_name="Josef Pracovník",
                role="worker",
                worker_id=worker_id,
            ),
        )
        worker_client = TestClient(create_app(self.config))
        login_response = worker_client.post(
            "/api/auth/login",
            json={"login": "worker@example.com", "password": "tajneheslo"},
        )
        self.assertEqual(login_response.status_code, 200)

        response = worker_client.get("/api/emails")
        self.assertEqual(response.status_code, 403)

    def test_worker_sees_only_assigned_projects(self) -> None:
        worker_id = crud.create_worker(
            self.config,
            Worker(full_name="Josef Pracovník", email="worker-all@example.com"),
        )
        crud.create_user(
            self.config,
            User(
                email="worker-all@example.com",
                password_hash=hash_password("tajneheslo"),
                full_name="Josef Pracovník",
                role="worker",
                worker_id=worker_id,
            ),
        )

        project_a_response = self.client.post("/api/projects", json={"name": "Zakázka A", "description": "", "status": "new"})
        project_b_response = self.client.post("/api/projects", json={"name": "Zakázka B", "description": "", "status": "new"})
        project_a_id = project_a_response.json()["item"]["id"]
        project_b_id = project_b_response.json()["item"]["id"]
        self.client.post(
            "/api/tasks",
            json={
                "title": "Práce pro Josefa",
                "project_id": project_a_id,
                "assigned_worker_id": worker_id,
                "assigned_worker_ids": [worker_id],
            },
        )

        worker_client = TestClient(create_app(self.config))
        login_response = worker_client.post(
            "/api/auth/login",
            json={"login": "worker-all@example.com", "password": "tajneheslo"},
        )
        self.assertEqual(login_response.status_code, 200)

        projects_response = worker_client.get("/api/projects")
        self.assertEqual(projects_response.status_code, 200)
        projects = projects_response.json()["items"]
        self.assertEqual([item["id"] for item in projects], [project_a_id])

        assigned_detail_response = worker_client.get(f"/api/projects/{project_a_id}")
        forbidden_detail_response = worker_client.get(f"/api/projects/{project_b_id}")
        self.assertEqual(assigned_detail_response.status_code, 200)
        self.assertEqual(forbidden_detail_response.status_code, 403)

    def test_owner_can_manage_users(self) -> None:
        worker_id = crud.create_worker(
            self.config,
            Worker(full_name="Michal Admin", email="michal@example.com"),
        )

        create_response = self.client.post(
            "/api/users",
            json={
                "email": "novy-admin",
                "password": "tajneheslo",
                "full_name": "Michal Admin",
                "role": "admin",
                "worker_id": worker_id,
                "status": "active",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        user_id = create_response.json()["item"]["id"]

        users_response = self.client.get("/api/users")
        self.assertEqual(users_response.status_code, 200)
        self.assertTrue(any(item["id"] == user_id for item in users_response.json()["items"]))

        update_response = self.client.put(
            f"/api/users/{user_id}",
            json={
                "email": "novy-admin-2",
                "password": "",
                "full_name": "Michal Admin Upravený",
                "role": "admin",
                "worker_id": worker_id,
                "status": "inactive",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["item"]["full_name"], "Michal Admin Upravený")
        self.assertEqual(update_response.json()["item"]["status"], "inactive")

        delete_response = self.client.post(f"/api/users/{user_id}/delete")
        self.assertEqual(delete_response.status_code, 200)
        self.assertIsNone(crud.get_user(self.config, user_id))

    def test_user_can_change_password(self) -> None:
        response = self.client.post(
            "/api/auth/change-password",
            json={"current_password": self.config.bootstrap_owner_password, "new_password": "noveheslo"},
        )
        self.assertEqual(response.status_code, 200)

        new_client = TestClient(create_app(self.config))
        login_response = new_client.post(
            "/api/auth/login",
            json={"login": self.config.bootstrap_owner_email, "password": "noveheslo"},
        )
        self.assertEqual(login_response.status_code, 200)

        old_login_response = TestClient(create_app(self.config)).post(
            "/api/auth/login",
            json={"login": self.config.bootstrap_owner_email, "password": self.config.bootstrap_owner_password},
        )
        self.assertEqual(old_login_response.status_code, 401)

    def test_email_action_and_attachment_endpoint(self) -> None:
        attachment_path = self.config.attachments_dir / "email-1_invoice.pdf"
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_text("pdf-test", encoding="utf-8")

        crud.create_email(
            self.config,
            Email(
                id="email-1",
                thread_id="thread-1",
                sender="klient@example.com",
                subject="Faktura duben",
                body="Faktura cislo 2026-001\nCastka: 1500 CZK\nSplatnost: 2026-04-25",
                received_at="2026-04-17T08:00:00+00:00",
                attachments=[str(attachment_path)],
            ),
            summary="Faktura",
        )

        inbox_response = self.client.get("/api/inbox/unprocessed")
        payload = inbox_response.json()
        self.assertEqual(inbox_response.status_code, 200)
        self.assertEqual(len(payload["emails"]), 1)
        self.assertTrue(
            payload["emails"][0]["attachments"][0]["url"].endswith(
                "/api/emails/email-1/attachments/0"
            )
        )

        attachment_response = self.client.get("/api/emails/email-1/attachments/0")
        self.assertEqual(attachment_response.status_code, 200)

        action_response = self.client.post("/api/emails/email-1/action", json={"action": "track"})
        self.assertEqual(action_response.status_code, 200)
        email = crud.get_email(self.config, "email-1")
        self.assertIsNotNone(email)
        self.assertEqual(email.category, "general")
        self.assertEqual(email.status, "confirmed")

    def test_email_mark_invoice_action_removes_email_from_unprocessed(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-invoice-flag",
                thread_id="thread-invoice-flag",
                sender="dodavatel@example.com",
                subject="Podklady k faktuře",
                body="Faktura za materiál",
                received_at="2026-04-18T08:00:00+00:00",
            ),
            summary="Faktura",
        )

        before_payload = self.client.get("/api/inbox/unprocessed").json()
        self.assertEqual(len(before_payload["emails"]), 1)

        action_response = self.client.post(
            "/api/emails/email-invoice-flag/action",
            json={"action": "mark_invoice"},
        )
        self.assertEqual(action_response.status_code, 200)

        email = crud.get_email(self.config, "email-invoice-flag")
        self.assertIsNotNone(email)
        self.assertEqual(email.category, "invoice")
        self.assertEqual(email.status, "confirmed")

        after_payload = self.client.get("/api/inbox/unprocessed").json()
        self.assertEqual(len(after_payload["emails"]), 0)

    def test_email_create_task_action_creates_task(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-task-1",
                thread_id="thread-task-1",
                sender="klient@example.com",
                subject="Připravit nabídku",
                body="Prosím připravit cenovou nabídku.\nTermín: 2026-04-22 10:00",
                received_at="2026-04-18T08:00:00+00:00",
            ),
            summary="Poptávka",
        )

        action_response = self.client.post(
            "/api/emails/email-task-1/action",
            json={"action": "create_task"},
        )
        self.assertEqual(action_response.status_code, 200)
        self.assertIn("created_task_id", action_response.json())

        tasks_payload = self.client.get("/api/tasks").json()["items"]
        self.assertEqual(len(tasks_payload), 1)
        self.assertEqual(tasks_payload[0]["title"], "Připravit nabídku")
        self.assertEqual(tasks_payload[0]["source_email_id"], "email-task-1")

        email = crud.get_email(self.config, "email-task-1")
        self.assertIsNotNone(email)
        self.assertEqual(email.category, "task")
        self.assertEqual(email.status, "confirmed")

    def test_email_create_task_action_accepts_custom_dialog_values(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-task-custom",
                thread_id="thread-task-custom",
                sender="klient@example.com",
                subject="Původní předmět",
                body="Původní text e-mailu.",
                received_at="2026-04-18T08:00:00+00:00",
            ),
            summary="Poptávka",
        )

        action_response = self.client.post(
            "/api/emails/email-task-custom/action",
            json={
                "action": "create_task",
                "title": "Upravený úkol",
                "description": "Vlastní popis z dialogu",
                "due_date": "2026-04-25T09:30",
                "priority": "high",
                "estimated_hours": 2,
            },
        )
        self.assertEqual(action_response.status_code, 200)

        tasks_payload = self.client.get("/api/tasks").json()["items"]
        self.assertEqual(len(tasks_payload), 1)
        self.assertEqual(tasks_payload[0]["title"], "Upravený úkol")
        self.assertEqual(tasks_payload[0]["description"], "Vlastní popis z dialogu")
        self.assertEqual(tasks_payload[0]["due_date"], "2026-04-25T09:30")
        self.assertEqual(tasks_payload[0]["priority"], "high")
        self.assertEqual(tasks_payload[0]["estimated_hours"], 2.0)

    def test_email_list_project_action_and_project_document_upload(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-2",
                thread_id="thread-2",
                sender="zakaznik@example.com",
                subject="Nova zakazka na montaz",
                body="Firma: ACME\nAdresa: Brno\nTermin: 2026-04-25",
                received_at="2026-04-17T09:00:00+00:00",
            ),
            summary="Poptavka",
        )

        email_list_response = self.client.get("/api/emails")
        self.assertEqual(email_list_response.status_code, 200)
        self.assertEqual(len(email_list_response.json()["items"]), 1)

        create_project_response = self.client.post(
            "/api/emails/email-2/action",
            json={"action": "create_project"},
        )
        self.assertEqual(create_project_response.status_code, 200)
        project_id = create_project_response.json()["project_id"]

        upload_response = self.client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("foto.jpg", b"fake-image", "image/jpeg")},
            data={"title": "Foto z mista", "document_type": "photo"},
        )
        self.assertEqual(upload_response.status_code, 200)

        project_response = self.client.get(f"/api/projects/{project_id}")
        self.assertEqual(project_response.status_code, 200)
        self.assertEqual(len(project_response.json()["documents"]), 1)

        second_project_response = self.client.post(
            "/api/projects",
            json={"name": "Druha zakazka", "description": "", "status": "new"},
        )
        self.assertEqual(second_project_response.status_code, 200)
        second_project_id = second_project_response.json()["item"]["id"]

        assign_response = self.client.post(
            "/api/emails/email-2/action",
            json={"action": "assign_project", "project_id": second_project_id},
        )
        self.assertEqual(assign_response.status_code, 200)

        email_payload = self.client.get("/api/emails").json()["items"][0]
        self.assertEqual(set(email_payload["project_ids"]), {project_id, second_project_id})

        second_project_detail = self.client.get(f"/api/projects/{second_project_id}").json()
        self.assertEqual(len(second_project_detail["emails"]), 1)

    def test_email_list_can_omit_body_and_fetch_detail(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-slim-1",
                thread_id="thread-slim-1",
                sender="zakaznik@example.com",
                subject="Dlouha poptavka",
                body="Plny text e-mailu " * 80,
                received_at="2026-04-17T09:00:00+00:00",
            ),
            summary="Strucny souhrn",
        )

        list_response = self.client.get("/api/emails?include_body=false&limit=1&offset=0")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertNotIn("body", payload["items"][0])
        self.assertEqual(payload["items"][0]["body_preview"], "Strucny souhrn")

        detail_response = self.client.get("/api/emails/email-slim-1")
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn("Plny text e-mailu", detail_response.json()["item"]["body"])

    def test_project_photo_upload_keeps_worker_and_work_date(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Foto Pracovník", "email": "foto@example.com"},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakázka Foto", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        upload_response = self.client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("foto.jpg", b"fake-image", "image/jpeg")},
            data={
                "title": "Montáž rozvaděče",
                "document_type": "photo",
                "worker_id": worker_id,
                "work_date": "2026-04-21",
            },
        )
        self.assertEqual(upload_response.status_code, 200)
        item = upload_response.json()["item"]
        self.assertEqual(item["document_type"], "photo")
        self.assertEqual(item["worker_id"], worker_id)
        self.assertEqual(item["work_date"], "2026-04-21")

    def test_email_can_be_returned_to_unprocessed_after_project_creation(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-return-1",
                thread_id="thread-return-1",
                sender="zakaznik@example.com",
                subject="Omylem zalozena zakazka",
                body="Tohle se ma vratit zpet do neroztridenych.",
                received_at="2026-04-17T09:30:00+00:00",
            ),
            summary="Omyl",
        )

        create_project_response = self.client.post(
            "/api/emails/email-return-1/action",
            json={"action": "create_project"},
        )
        self.assertEqual(create_project_response.status_code, 200)

        email_after_create = self.client.get("/api/emails").json()["items"][0]
        self.assertGreaterEqual(len(email_after_create["project_ids"]), 1)

        return_response = self.client.post(
            "/api/emails/email-return-1/action",
            json={"action": "return_unprocessed"},
        )
        self.assertEqual(return_response.status_code, 200)

        email = crud.get_email(self.config, "email-return-1")
        self.assertIsNotNone(email)
        self.assertEqual(email.category, "uncategorized")
        self.assertEqual(email.status, "pending")
        self.assertEqual(crud.list_email_project_ids(self.config, "email-return-1"), [])

        unprocessed_payload = self.client.get("/api/inbox/unprocessed").json()
        self.assertEqual(len(unprocessed_payload["emails"]), 1)

    def test_delete_local_entities(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-delete-1",
                thread_id="thread-delete-1",
                sender="lokalni@example.com",
                subject="Smazat tento email",
                body="Jen lokalne.",
                received_at="2026-04-17T10:30:00+00:00",
            ),
            summary="Delete",
        )

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Smazani", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Martin Mazani"},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        task_response = self.client.post(
            "/api/tasks",
            json={"title": "Smazat ukol", "project_id": project_id},
        )
        self.assertEqual(task_response.status_code, 200)
        task_id = task_response.json()["item"]["id"]

        self.assertEqual(self.client.delete("/api/emails/email-delete-1").status_code, 200)
        self.assertIsNone(crud.get_email(self.config, "email-delete-1"))

        self.assertEqual(self.client.delete(f"/api/tasks/{task_id}").status_code, 200)
        tasks_payload = self.client.get("/api/tasks").json()["items"]
        self.assertEqual(len(tasks_payload), 0)

        self.assertEqual(self.client.delete(f"/api/workers/{worker_id}").status_code, 200)
        workers_payload = self.client.get("/api/workers").json()["items"]
        self.assertEqual(len(workers_payload), 0)

        self.assertEqual(self.client.delete(f"/api/projects/{project_id}").status_code, 200)
        projects_payload = self.client.get("/api/projects").json()["items"]
        self.assertEqual(len(projects_payload), 0)

    def test_bulk_email_action_and_task_archive_endpoints(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-3",
                thread_id="thread-3",
                sender="client@example.com",
                subject="Prosim vytvorit ukol",
                body="Potrebuji zpracovat objednavku.",
                received_at="2026-04-17T10:00:00+00:00",
            ),
            summary="Ukol",
        )
        crud.create_email(
            self.config,
            Email(
                id="email-4",
                thread_id="thread-4",
                sender="client@example.com",
                subject="Druhy email",
                body="Take ke zpracovani.",
                received_at="2026-04-17T11:00:00+00:00",
            ),
            summary="Ukol 2",
        )

        bulk_response = self.client.post(
            "/api/emails/bulk-action",
            json={"email_ids": ["email-3", "email-4"], "action": "track"},
        )
        self.assertEqual(bulk_response.status_code, 200)
        self.assertEqual(bulk_response.json()["processed"], 2)

        email_3 = crud.get_email(self.config, "email-3")
        email_4 = crud.get_email(self.config, "email-4")
        self.assertEqual(email_3.status, "confirmed")
        self.assertEqual(email_4.status, "confirmed")

        task_id = crud.create_task(self.config, Task(title="Test ukol", status="pending"))
        archive_response = self.client.post(
            f"/api/tasks/{task_id}/action",
            json={"action": "archive"},
        )
        self.assertEqual(archive_response.status_code, 200)

        archive_payload = self.client.get("/api/archive").json()
        self.assertEqual(len(archive_payload["tasks"]), 1)

    def test_conversation_and_project_task_endpoints(self) -> None:
        crud.create_email(
            self.config,
            Email(
                id="email-thread-1",
                thread_id="thread-shared",
                sender="novak@example.com",
                subject="ZakĂˇzka NovĂˇk",
                body="PrvnĂ­ zprĂˇva",
                received_at="2026-04-17T08:00:00+00:00",
            ),
            summary="PrvnĂ­ zprĂˇva",
        )
        crud.create_email(
            self.config,
            Email(
                id="email-thread-2",
                thread_id="thread-shared",
                sender="technik@example.com",
                subject="Re: ZakĂˇzka NovĂˇk",
                body="DruhĂˇ zprĂˇva",
                received_at="2026-04-17T09:00:00+00:00",
            ),
            summary="DruhĂˇ zprĂˇva",
        )

        conversations_response = self.client.get("/api/conversations")
        self.assertEqual(conversations_response.status_code, 200)
        self.assertEqual(len(conversations_response.json()["items"]), 1)

        conversation_detail_response = self.client.get("/api/conversations/thread-shared")
        self.assertEqual(conversation_detail_response.status_code, 200)
        self.assertEqual(len(conversation_detail_response.json()["emails"]), 2)

        project_response = self.client.post(
            "/api/projects",
            json={"name": "ZakĂˇzka NovĂˇk", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        project_task_response = self.client.post(
            f"/api/projects/{project_id}/tasks",
            json={
                "title": "Objednat materiĂˇl",
                "description": "PĹ™ipravit materiĂˇl na montĂˇĹľ.",
                "priority": "high",
                "due_date": "2026-04-20T09:00:00",
            },
        )
        self.assertEqual(project_task_response.status_code, 200)

        project_detail = self.client.get(f"/api/projects/{project_id}").json()
        self.assertEqual(len(project_detail["tasks"]), 1)

    def test_task_create_endpoint_and_calendar_action(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Petr Svoboda", "email": "petr@example.com"},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={
                "name": "Zakazka Kalendar",
                "description": "",
                "status": "new",
                "contact_email": "klient@example.com",
                "address": "Brno",
            },
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        task_response = self.client.post(
            "/api/tasks",
            json={
                "title": "Zavolat klientovi",
                "description": "Potvrdit termin realizace.",
                "priority": "high",
                "due_date": "2026-04-22T09:30:00",
                "project_id": project_id,
                "assigned_worker_id": worker_id,
                "estimated_hours": 1.5,
            },
        )
        self.assertEqual(task_response.status_code, 200)
        task_id = task_response.json()["item"]["id"]

        list_response = self.client.get("/api/tasks")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["items"]), 1)

        calendar_response = self.client.post(
            f"/api/tasks/{task_id}/action",
            json={"action": "create_calendar_event"},
        )
        self.assertEqual(calendar_response.status_code, 200)
        self.assertIn("created_event_id", calendar_response.json())
        self.assertEqual(calendar_response.json()["invited_workers"], 1)

        events = crud.list_calendar_events(self.config)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Zakazka Kalendar – Zavolat klientovi")
        self.assertEqual(events[0].task_id, task_id)
        self.assertEqual(events[0].project_id, project_id)
        self.assertEqual(events[0].assigned_worker_id, worker_id)
        self.assertEqual(events[0].attendee_emails, ["petr@example.com"])

        updated_task = next(item for item in crud.list_tasks(self.config) if item.id == task_id)
        self.assertEqual(updated_task.status, "scheduled")

        tasks_payload = self.client.get("/api/tasks").json()["items"]
        task_payload = next(item for item in tasks_payload if item["id"] == task_id)
        self.assertEqual(task_payload["worker_ids"], [worker_id])
        self.assertEqual(task_payload["latest_calendar_event"]["attendee_emails"], ["petr@example.com"])
        self.assertTrue(any(entry["kind"] == "calendar" for entry in task_payload["timeline"]))

    def test_task_can_be_updated(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Jan Novak", "email": "jan@example.com"},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Uprava Ukolu", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        task_response = self.client.post(
            "/api/tasks",
            json={
                "title": "Puvodni ukol",
                "description": "Puvodni popis",
                "priority": "normal",
                "project_id": project_id,
            },
        )
        self.assertEqual(task_response.status_code, 200)
        task_id = task_response.json()["item"]["id"]

        update_response = self.client.put(
            f"/api/tasks/{task_id}",
            json={
                "title": "Upraveny ukol",
                "description": "Novy popis",
                "priority": "high",
                "status": "in_progress",
                "due_date": "2026-04-25T08:30",
                "project_id": project_id,
                "assigned_worker_id": worker_id,
                "assigned_worker_ids": [worker_id],
                "estimated_hours": 3,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        item = update_response.json()["item"]
        self.assertEqual(item["title"], "Upraveny ukol")
        self.assertEqual(item["description"], "Novy popis")
        self.assertEqual(item["priority"], "high")
        self.assertEqual(item["status"], "in_progress")
        self.assertEqual(item["due_date"], "2026-04-25T08:30")
        self.assertEqual(item["estimated_hours"], 3.0)
        self.assertEqual(item["worker_ids"], [worker_id])

        done_response = self.client.put(
            f"/api/tasks/{task_id}",
            json={
                "title": "Upraveny ukol",
                "description": "Novy popis",
                "priority": "high",
                "status": "done",
                "due_date": "2026-04-25T08:30",
                "project_id": project_id,
                "assigned_worker_id": worker_id,
                "assigned_worker_ids": [worker_id],
                "estimated_hours": 3,
            },
        )
        self.assertEqual(done_response.status_code, 200)
        done_item = done_response.json()["item"]
        self.assertEqual(done_item["status"], "done")
        self.assertIsNotNone(done_item["completed_at"])
        self.assertEqual(done_item["completed_by"]["full_name"], "Pepa")

    def test_worklog_payment_summary_and_mark_paid(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Jan Novak", "payout_rate": 250},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Vyplaty", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        worklog_response = self.client.post(
            "/api/worklogs",
            json={
                "project_id": project_id,
                "worker_id": worker_id,
                "work_date": "2026-04-18",
                "hours": 4,
                "payout_amount": 1000,
                "notes": "Montaz",
            },
        )
        self.assertEqual(worklog_response.status_code, 200)
        worklog = worklog_response.json()["item"]
        self.assertEqual(worklog["payment_status"], "unpaid")

        summary_response = self.client.get("/api/worklogs/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary_items = summary_response.json()["items"]
        self.assertEqual(len(summary_items), 1)
        self.assertEqual(summary_items[0]["hours"], 4.0)
        self.assertEqual(summary_items[0]["unpaid_total"], 1000.0)
        self.assertEqual(summary_items[0]["paid_total"], 0.0)

        payment_response = self.client.post(
            f"/api/worklogs/{worklog['id']}/payment",
            json={"is_paid": True},
        )
        self.assertEqual(payment_response.status_code, 200)
        self.assertEqual(payment_response.json()["item"]["payment_status"], "paid")

        summary_response = self.client.get("/api/worklogs/summary")
        summary_items = summary_response.json()["items"]
        self.assertEqual(summary_items[0]["unpaid_total"], 0.0)
        self.assertEqual(summary_items[0]["paid_total"], 1000.0)

    def test_project_worker_worklog_payment_marks_whole_project_slice(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Ladislav Belani", "payout_rate": 350},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Hromadne Proplaceni", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        for work_date, hours, payout in [("2026-04-18", 4, 1400), ("2026-04-19", 6, 2100)]:
            worklog_response = self.client.post(
                "/api/worklogs",
                json={
                    "project_id": project_id,
                    "worker_id": worker_id,
                    "work_date": work_date,
                    "hours": hours,
                    "payout_amount": payout,
                    "notes": "Montaz",
                },
            )
            self.assertEqual(worklog_response.status_code, 200)

        payment_response = self.client.post(
            "/api/worklogs/project-payment",
            json={"project_id": project_id, "worker_id": worker_id, "is_paid": True},
        )
        self.assertEqual(payment_response.status_code, 200)
        self.assertEqual(payment_response.json()["updated_count"], 2)

        worklogs_response = self.client.get(f"/api/worklogs?project_id={project_id}")
        self.assertEqual(worklogs_response.status_code, 200)
        items = worklogs_response.json()["items"]
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item["payment_status"] == "paid" for item in items))

        summary_response = self.client.get("/api/worklogs/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary_items = summary_response.json()["items"]
        self.assertEqual(summary_items[0]["unpaid_total"], 0.0)
        self.assertEqual(summary_items[0]["paid_total"], 3500.0)

    def test_project_worker_rate_is_used_for_worklog_and_project_detail(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Ladislav Belani", "payout_rate": 350},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Individualni Sazba", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        rates_response = self.client.post(
            f"/api/projects/{project_id}/worker-rates",
            json={"items": [{"worker_id": worker_id, "payout_rate": 500}]},
        )
        self.assertEqual(rates_response.status_code, 200)
        self.assertEqual(len(rates_response.json()["items"]), 1)
        self.assertEqual(rates_response.json()["items"][0]["payout_rate"], 500.0)

        worklog_response = self.client.post(
            "/api/worklogs",
            json={
                "project_id": project_id,
                "worker_id": worker_id,
                "work_date": "2026-05-13",
                "hours": 8,
                "material_cost": 200,
                "notes": "Náročnější práce",
            },
        )
        self.assertEqual(worklog_response.status_code, 200)
        self.assertEqual(worklog_response.json()["item"]["payout_amount"], 4200.0)

        detail_response = self.client.get(f"/api/projects/{project_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["worker_rates"][0]["payout_rate"], 500.0)

    def test_delete_worklog(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={"full_name": "Jan Novak", "payout_rate": 250},
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Mazani Vykazu", "description": "", "status": "new"},
        )
        self.assertEqual(project_response.status_code, 200)
        project_id = project_response.json()["item"]["id"]

        worklog_response = self.client.post(
            "/api/worklogs",
            json={
                "project_id": project_id,
                "worker_id": worker_id,
                "work_date": "2026-04-20",
                "hours": 6,
                "material_cost": 120,
                "notes": "Test mazani",
            },
        )
        self.assertEqual(worklog_response.status_code, 200)
        worklog_id = worklog_response.json()["item"]["id"]

        delete_response = self.client.post(f"/api/worklogs/{worklog_id}/delete")
        self.assertEqual(delete_response.status_code, 200)

        worklogs = crud.list_work_logs(self.config)
        self.assertFalse(any(item.id == worklog_id for item in worklogs))

    def test_worker_can_be_updated(self) -> None:
        worker_response = self.client.post(
            "/api/workers",
            json={
                "full_name": "Jan Novak",
                "email": "old@example.com",
                "hourly_rate": 250,
                "payout_rate": 200,
            },
        )
        self.assertEqual(worker_response.status_code, 200)
        worker_id = worker_response.json()["item"]["id"]

        update_response = self.client.put(
            f"/api/workers/{worker_id}",
            json={
                "full_name": "Jan Novak upraveny",
                "role": "Technik",
                "email": "new@example.com",
                "phone": "777123456",
                "hourly_rate": 300,
                "payout_rate": 240,
                "status": "inactive",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        item = update_response.json()["item"]
        self.assertEqual(item["full_name"], "Jan Novak upraveny")
        self.assertEqual(item["role"], "Technik")
        self.assertEqual(item["email"], "new@example.com")
        self.assertEqual(item["phone"], "777123456")
        self.assertEqual(item["hourly_rate"], 300)
        self.assertEqual(item["payout_rate"], 240)
        self.assertEqual(item["status"], "inactive")

    def test_project_status_can_be_updated(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={"name": "Zakazka Stav", "description": "", "status": "new"},
        )
        self.assertEqual(create_response.status_code, 200)
        project_id = create_response.json()["item"]["id"]

        update_response = self.client.put(
            f"/api/projects/{project_id}",
            json={
                "name": "Zakazka Stav",
                "description": "",
                "status": "waiting",
                "code": "",
                "customer_name": "",
                "contact_person": "",
                "contact_email": "",
                "contact_phone": "",
                "address": "",
                "priority": "high",
                "planned_start_at": None,
                "planned_end_at": None,
                "actual_start_at": None,
                "actual_end_at": None,
                "budget_amount": None,
                "notes": "",
                "internal_notes": "",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        item = update_response.json()["item"]
        self.assertEqual(item["status"], "waiting")
        self.assertEqual(item["priority"], "high")

        project_detail_response = self.client.get(f"/api/projects/{project_id}")
        self.assertEqual(project_detail_response.status_code, 200)
        timeline_events = project_detail_response.json()["timeline_events"]
        self.assertEqual(len(timeline_events), 1)
        self.assertEqual(timeline_events[0]["event_type"], "project_status")
        self.assertEqual(timeline_events[0]["details"], "new -> waiting")


if __name__ == "__main__":
    unittest.main()

