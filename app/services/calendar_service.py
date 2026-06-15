from __future__ import annotations

from typing import Sequence

from app.config import AppConfig
from app.db import crud
from app.db.models import CalendarEventModel
from app.integrations.calendar_api import CalendarApiClient
from app.schemas.entities import CalendarEvent


class CalendarService:
    def __init__(
        self,
        config: AppConfig,
        client: CalendarApiClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or CalendarApiClient(config)

    def sync(self) -> None:
        self.client.sync()

    def authorize(self) -> bool:
        return self.client.authorize()

    def create_event_proposal(
        self,
        title: str,
        starts_at: str,
        ends_at: str,
        description: str = "",
        location: str = "",
        priority: str = "normal",
        source_email_id: str | None = None,
        task_id: int | None = None,
        project_id: int | None = None,
        assigned_worker_id: int | None = None,
        attendee_emails: list[str] | None = None,
    ) -> int:
        external_event_id = self.client.create_event(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            description=description,
            location=location,
            priority=priority,
            attendee_emails=attendee_emails,
        )
        event = CalendarEvent(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            description=description,
            location=location,
            status="scheduled" if external_event_id else "proposed",
            source_email_id=source_email_id,
            task_id=task_id,
            project_id=project_id,
            assigned_worker_id=assigned_worker_id,
            attendee_emails=attendee_emails or [],
            calendar_id=self.config.google_calendar_id if external_event_id else "",
            external_event_id=external_event_id or "",
        )
        return crud.create_calendar_event(self.config, event)

    def list_events(self) -> Sequence[CalendarEventModel]:
        return crud.list_calendar_events(self.config)

    def sync_existing_event(self, event_id: int) -> CalendarEventModel | None:
        event = crud.get_calendar_event(self.config, event_id)
        if event is None:
            return None

        external_event_id = self.client.create_event(
            title=event.title,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            description=event.description,
            location=event.location,
            attendee_emails=event.attendee_emails,
        )
        if not external_event_id:
            return event

        crud.update_calendar_event_sync(
            self.config,
            event_id,
            status="scheduled",
            calendar_id=self.config.google_calendar_id,
            external_event_id=external_event_id,
        )
        return crud.get_calendar_event(self.config, event_id)
