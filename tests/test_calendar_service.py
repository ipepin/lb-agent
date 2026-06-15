import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.db import crud
from app.db.database import initialize_database
from app.schemas.entities import CalendarEvent
from app.services.calendar_service import CalendarService


class FakeCalendarClient:
    def __init__(self) -> None:
        self.created_events: list[dict[str, object]] = []

    def sync(self) -> None:
        return None

    def authorize(self) -> bool:
        return True

    def create_event(
        self,
        *,
        title: str,
        starts_at: str,
        ends_at: str,
        description: str = "",
        location: str = "",
        priority: str = "normal",
        attendee_emails: list[str] | None = None,
    ) -> dict[str, str] | None:
        self.created_events.append(
            {
                "title": title,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "description": description,
                "location": location,
                "priority": priority,
                "attendee_emails": attendee_emails or [],
            }
        )
        return {"id": "gcal-event-1", "html_link": "https://calendar.google.com/event?eid=test"}

    def update_event(self, **kwargs: object) -> dict[str, str] | None:
        return {"id": "gcal-event-1", "html_link": "https://calendar.google.com/event?eid=test"}

    def delete_event(self, **kwargs: object) -> bool:
        return True


class TestCalendarService(unittest.TestCase):
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
            google_calendar_id="team-calendar@example.com",
        )
        initialize_database(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_event_proposal_stores_external_calendar_metadata(self) -> None:
        fake_client = FakeCalendarClient()
        service = CalendarService(self.config, client=fake_client)

        event_id = service.create_event_proposal(
            title="Montáž Novák",
            starts_at="2026-04-21T08:00:00+02:00",
            ends_at="2026-04-21T10:00:00+02:00",
            description="Výjezd na zakázku",
            location="Brno",
            source_email_id="email-1",
            project_id=5,
            assigned_worker_id=2,
            attendee_emails=["technik@example.com", "montaz@example.com"],
        )

        self.assertGreater(event_id, 0)
        self.assertEqual(len(fake_client.created_events), 1)
        self.assertEqual(fake_client.created_events[0]["priority"], "normal")
        self.assertEqual(
            fake_client.created_events[0]["attendee_emails"],
            ["technik@example.com", "montaz@example.com"],
        )

        stored_event = crud.list_calendar_events(self.config)[0]
        self.assertEqual(stored_event.status, "scheduled")
        self.assertEqual(stored_event.calendar_id, "team-calendar@example.com")
        self.assertEqual(stored_event.external_event_id, "gcal-event-1")
        self.assertEqual(stored_event.project_id, 5)
        self.assertEqual(stored_event.assigned_worker_id, 2)

    def test_sync_existing_event_updates_external_metadata(self) -> None:
        fake_client = FakeCalendarClient()
        service = CalendarService(self.config, client=fake_client)

        event_id = crud.create_calendar_event(
            self.config,
            CalendarEvent(
                title="Lokální plán",
                starts_at="2026-04-21T08:00:00+02:00",
                ends_at="2026-04-21T10:00:00+02:00",
                description="Pouze dashboard",
                location="Brno",
                status="proposed",
                task_id=7,
                project_id=8,
                assigned_worker_id=3,
                attendee_emails=["technik@example.com"],
            ),
        )

        stored_event = service.sync_existing_event(
            event_id,
            title="Lokální plán",
            starts_at="2026-04-21T08:00:00+02:00",
            ends_at="2026-04-21T10:00:00+02:00",
            description="Pouze dashboard",
            location="Brno",
            attendee_emails=["technik@example.com"],
        )

        self.assertIsNotNone(stored_event)
        assert stored_event is not None
        self.assertEqual(stored_event.status, "scheduled")
        self.assertEqual(stored_event.calendar_id, "team-calendar@example.com")
        self.assertEqual(stored_event.external_event_id, "gcal-event-1")


if __name__ == "__main__":
    unittest.main()
