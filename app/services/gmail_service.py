from __future__ import annotations

from datetime import datetime
from typing import Callable, Sequence

from app.config import AppConfig
from app.integrations.gmail_api import GmailApiClient
from app.schemas.entities import Email


class GmailService:
    def __init__(
        self,
        config: AppConfig,
        client: GmailApiClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or GmailApiClient(config)

    def fetch_messages(
        self,
        max_results: int = 0,
        received_after: str | None = None,
        progress_callback: Callable[[str, int | None, int | None], None] | None = None,
    ) -> Sequence[Email]:
        return self.client.fetch_messages(
            max_results=max_results,
            received_after=received_after,
            progress_callback=progress_callback,
        )

    def authorize(self) -> bool:
        return self.client.authorize()

    def fetch_new_messages(
        self,
        processed_email_ids: set[str],
        max_results: int = 0,
        received_after: str | None = None,
        progress_callback: Callable[[str, int | None, int | None], None] | None = None,
    ) -> Sequence[Email]:
        messages = self.fetch_messages(
            max_results=max_results,
            received_after=received_after,
            progress_callback=progress_callback,
        )
        received_after_dt = self._parse_iso(received_after)
        filtered_messages: list[Email] = []
        for message in messages:
            if message.id in processed_email_ids:
                continue
            if received_after_dt is not None:
                message_dt = self._parse_iso(message.received_at)
                if message_dt is not None and message_dt <= received_after_dt:
                    continue
            filtered_messages.append(message)
        return filtered_messages

    def _parse_iso(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.strip().lstrip("\ufeff"))
        except ValueError:
            return None
