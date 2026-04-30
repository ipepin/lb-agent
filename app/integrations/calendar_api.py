from __future__ import annotations

from datetime import datetime

from app.config import AppConfig
from app.utils.file_utils import ensure_directory
from app.utils.logger import get_logger

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:  # pragma: no cover - optional runtime dependency
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception


CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
logger = get_logger(__name__)


class CalendarApiClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def sync(self) -> None:
        return None

    def authorize(self) -> bool:
        credentials = self._run_oauth_flow()
        return credentials is not None

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
    ) -> str | None:
        if not self.config.google_calendar_id:
            return None

        service = self._build_service(interactive=False)
        if service is None:
            return None

        event_body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {
                "dateTime": self._normalize_datetime_string(starts_at),
                "timeZone": self.config.google_calendar_timezone,
            },
            "end": {
                "dateTime": self._normalize_datetime_string(ends_at),
                "timeZone": self.config.google_calendar_timezone,
            },
        }
        color_id = self._get_color_id(priority)
        if color_id:
            event_body["colorId"] = color_id
        normalized_attendees = [
            {"email": email.strip()}
            for email in (attendee_emails or [])
            if email and email.strip()
        ]
        if normalized_attendees:
            event_body["attendees"] = normalized_attendees
        try:
            created_event = (
                service.events()
                .insert(
                    calendarId=self.config.google_calendar_id,
                    body=event_body,
                    sendUpdates="all" if normalized_attendees else "none",
                )
                .execute()
            )
            return str(created_event.get("id") or "")
        except HttpError as error:
            logger.warning("Google Calendar zápis selhal: %s", error)
            return None
        except Exception as error:  # pragma: no cover - runtime safety
            logger.exception("Neočekávaná chyba při zápisu do Google Kalendáře: %s", error)
            return None

    def _build_service(self, *, interactive: bool) -> object | None:
        if build is None:
            return None

        credentials = self._load_credentials(interactive=interactive)
        if credentials is None:
            return None

        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def _load_credentials(self, *, interactive: bool) -> Credentials | None:
        if Credentials is None:
            return None

        token_path = self.config.google_calendar_token_path
        if token_path is not None and token_path.exists():
            credentials = Credentials.from_authorized_user_file(
                str(token_path),
                CALENDAR_SCOPES,
            )
            if credentials and credentials.valid:
                return credentials
            if credentials and credentials.expired and credentials.refresh_token:
                if Request is None:
                    return None
                credentials.refresh(Request())
                self._save_credentials(credentials)
                return credentials

        if interactive:
            return self._run_oauth_flow()

        return None

    def _run_oauth_flow(self) -> Credentials | None:
        if InstalledAppFlow is None or Credentials is None:
            return None

        credentials_path = self.config.gmail_credentials_path
        if not credentials_path.exists():
            return None

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            CALENDAR_SCOPES,
        )
        credentials = flow.run_local_server(port=0)
        self._save_credentials(credentials)
        return credentials

    def _save_credentials(self, credentials: Credentials) -> None:
        token_path = self.config.google_calendar_token_path
        if token_path is None:
            return
        ensure_directory(token_path.parent)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    def _normalize_datetime_string(self, value: str) -> str:
        normalized = value.strip()
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            return normalized

    def _get_color_id(self, priority: str) -> str | None:
        normalized = (priority or "normal").strip().lower()
        mapping = {
            "low": "10",
            "normal": "9",
            "medium": "9",
            "high": "11",
            "urgent": "11",
        }
        return mapping.get(normalized, "9")
