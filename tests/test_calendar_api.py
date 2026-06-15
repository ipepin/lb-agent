import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.integrations.calendar_api import CalendarApiClient


class _FakeCredentials:
    refresh_should_fail = False
    saved_payload = '{"token":"new-calendar-token"}'
    refresh_calls = 0

    def __init__(self, *, valid: bool, expired: bool, refresh_token: str | None) -> None:
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token

    def refresh(self, request: object) -> None:
        type(self).refresh_calls += 1
        if type(self).refresh_should_fail:
            raise RuntimeError("invalid_grant")
        self.valid = True
        self.expired = False

    def to_json(self) -> str:
        return type(self).saved_payload

    @classmethod
    def from_authorized_user_file(cls, path: str, scopes: list[str]) -> "_FakeCredentials":
        return cls(valid=False, expired=True, refresh_token="refresh-token")


class _FakeFlow:
    run_calls = 0

    @classmethod
    def from_client_secrets_file(cls, path: str, scopes: list[str]) -> "_FakeFlow":
        return cls()

    def run_local_server(self, port: int = 0) -> _FakeCredentials:
        type(self).run_calls += 1
        return _FakeCredentials(valid=True, expired=False, refresh_token="refresh-token")


class TestCalendarApiClient(unittest.TestCase):
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
            google_calendar_token_path=root / "data" / "google_calendar_token.json",
            idoklad_client_id="",
            idoklad_client_secret="",
        )
        self.config.gmail_credentials_path.write_text("{}", encoding="utf-8")
        self.config.google_calendar_token_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.google_calendar_token_path.write_text('{"token":"old"}', encoding="utf-8")
        _FakeCredentials.refresh_should_fail = False
        _FakeCredentials.refresh_calls = 0
        _FakeFlow.run_calls = 0

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_interactive_authorize_replaces_invalid_token(self) -> None:
        class TestClient(CalendarApiClient):
            pass

        from app.integrations import calendar_api

        original_request = calendar_api.Request
        original_credentials = calendar_api.Credentials
        original_flow = calendar_api.InstalledAppFlow
        try:
            calendar_api.Request = object
            calendar_api.Credentials = _FakeCredentials
            calendar_api.InstalledAppFlow = _FakeFlow
            _FakeCredentials.refresh_should_fail = True

            client = TestClient(self.config)
            credentials = client._load_credentials(interactive=True)
        finally:
            calendar_api.Request = original_request
            calendar_api.Credentials = original_credentials
            calendar_api.InstalledAppFlow = original_flow

        self.assertIsNotNone(credentials)
        self.assertEqual(_FakeCredentials.refresh_calls, 1)
        self.assertEqual(_FakeFlow.run_calls, 1)
        self.assertEqual(
            self.config.google_calendar_token_path.read_text(encoding="utf-8"),
            _FakeCredentials.saved_payload,
        )

    def test_noninteractive_invalid_token_returns_none(self) -> None:
        class TestClient(CalendarApiClient):
            pass

        from app.integrations import calendar_api

        original_request = calendar_api.Request
        original_credentials = calendar_api.Credentials
        try:
            calendar_api.Request = object
            calendar_api.Credentials = _FakeCredentials
            _FakeCredentials.refresh_should_fail = True

            client = TestClient(self.config)
            credentials = client._load_credentials(interactive=False)
        finally:
            calendar_api.Request = original_request
            calendar_api.Credentials = original_credentials

        self.assertIsNone(credentials)
        self.assertEqual(_FakeCredentials.refresh_calls, 1)


if __name__ == "__main__":
    unittest.main()
