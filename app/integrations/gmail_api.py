from __future__ import annotations

import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Sequence

from app.config import AppConfig
from app.schemas.entities import Email
from app.utils.dates import utc_now_iso
from app.utils.file_utils import ensure_directory, sanitize_filename
from app.utils.logger import get_logger
from app.utils.text_utils import cleanup_email_text, html_to_text


logger = get_logger(__name__)


class GmailApiClient:
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def fetch_messages(
        self,
        max_results: int = 0,
        received_after: str | None = None,
        progress_callback: Callable[[str, int | None, int | None], None] | None = None,
    ) -> Sequence[Email]:
        credentials = self._load_credentials(interactive=False)
        if credentials is None:
            return []

        service = self._build_service(credentials)
        message_refs: list[dict] = []
        page_token: str | None = None
        remaining = max_results if max_results and max_results > 0 else None

        if progress_callback is not None:
            progress_callback("Vyhledavam zpravy v Gmailu...", None, None)

        while True:
            batch_size = min(500, remaining) if remaining is not None else 500
            response = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=self._build_query(received_after),
                    maxResults=batch_size,
                    pageToken=page_token,
                )
                .execute()
            )
            batch_refs = response.get("messages", [])
            if not batch_refs:
                break
            message_refs.extend(batch_refs)

            if progress_callback is not None:
                progress_callback("Vyhledavam zpravy v Gmailu...", len(message_refs), None)

            if remaining is not None:
                remaining -= len(batch_refs)
                if remaining <= 0:
                    break

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        messages: list[Email] = []
        total_refs = len(message_refs)
        for index, message_ref in enumerate(message_refs, start=1):
            if progress_callback is not None:
                progress_callback("Stahuji obsah zprav...", index, total_refs)
            message_id = message_ref["id"]
            payload = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            if not self._is_received_message(payload):
                continue
            messages.append(self._build_email(service=service, payload=payload))

        return messages

    def _build_query(self, received_after: str | None) -> str:
        base_query = self.config.gmail_query.strip()
        if not received_after:
            return base_query
        try:
            dt_value = datetime.fromisoformat(received_after.strip().lstrip("\ufeff"))
            timestamp = max(0, int(dt_value.timestamp()) - 60)
            return f"{base_query} after:{timestamp}"
        except ValueError:
            return base_query

    def _is_received_message(self, payload: dict) -> bool:
        label_ids = set(payload.get("labelIds", []) or [])
        return "SENT" not in label_ids

    def authorize(self) -> bool:
        credentials = self._load_credentials(interactive=True)
        return credentials is not None

    def _load_credentials(self, interactive: bool) -> object | None:
        google_modules = self._import_google_auth_modules()
        if google_modules is None:
            return None

        Request, Credentials, InstalledAppFlow = google_modules
        creds = None

        if self.config.gmail_token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.config.gmail_token_path),
                self.SCOPES,
            )

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                if not interactive:
                    raise
                logger.warning("Stored Gmail OAuth token is invalid, starting a new login: %s", exc)
                creds = None
                self._delete_token()
            else:
                self._save_token(creds)
                return creds

        if not interactive:
            return None

        if not self.config.gmail_credentials_path.exists():
            return None

        ensure_directory(self.config.gmail_token_path.parent)
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.config.gmail_credentials_path),
            self.SCOPES,
        )
        creds = flow.run_local_server(port=0)
        self._save_token(creds)
        return creds

    def _delete_token(self) -> None:
        if self.config.gmail_token_path.exists():
            self.config.gmail_token_path.unlink()

    def _save_token(self, creds: object) -> None:
        ensure_directory(self.config.gmail_token_path.parent)
        self.config.gmail_token_path.write_text(creds.to_json(), encoding="utf-8")

    def _build_service(self, credentials: object) -> object:
        google_api_modules = self._import_google_api_modules()
        if google_api_modules is None:
            raise RuntimeError("Google API client libraries are not installed.")

        build, _ = google_api_modules
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def _build_email(self, service: object, payload: dict) -> Email:
        headers = self._headers_to_dict(payload.get("payload", {}).get("headers", []))
        body = self._extract_body(payload.get("payload", {}))
        attachments = self._extract_attachments(
            service=service,
            message_id=payload["id"],
            part=payload.get("payload", {}),
        )

        return Email(
            id=payload["id"],
            subject=headers.get("Subject", ""),
            sender=headers.get("From", ""),
            body=body or payload.get("snippet", ""),
            received_at=self._parse_received_at(payload, headers),
            thread_id=payload.get("threadId", ""),
            attachments=attachments,
        )

    def _headers_to_dict(self, headers: list[dict]) -> dict[str, str]:
        return {
            header.get("name", ""): header.get("value", "")
            for header in headers
            if header.get("name")
        }

    def _parse_received_at(self, payload: dict, headers: dict[str, str]) -> str:
        internal_date = payload.get("internalDate")
        if internal_date:
            try:
                return self._millis_to_iso(int(internal_date))
            except (TypeError, ValueError):
                pass

        raw_date = headers.get("Date", "")
        if raw_date:
            try:
                return parsedate_to_datetime(raw_date).isoformat()
            except (TypeError, ValueError, IndexError):
                pass

        return utc_now_iso()

    def _millis_to_iso(self, value: int) -> str:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()

    def _extract_body(self, part: dict) -> str:
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        parts = part.get("parts", [])

        if mime_type == "text/plain" and body_data:
            return cleanup_email_text(
                self._decode_base64_url(body_data).decode("utf-8", errors="replace")
            )

        for child in parts:
            text = self._extract_body(child)
            if text:
                return text

        if mime_type == "text/html" and body_data:
            return cleanup_email_text(
                html_to_text(
                    self._decode_base64_url(body_data).decode("utf-8", errors="replace")
                )
            )

        return ""

    def _extract_attachments(self, service: object, message_id: str, part: dict) -> list[str]:
        ensure_directory(self.config.attachments_dir)
        stored_files: list[str] = []

        for child in self._walk_parts(part):
            filename = child.get("filename") or ""
            if not filename:
                continue

            body = child.get("body", {})
            attachment_data = body.get("data")
            attachment_id = body.get("attachmentId")

            if attachment_id:
                attachment = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=attachment_id)
                    .execute()
                )
                attachment_data = attachment.get("data")

            if not attachment_data:
                continue

            safe_name = sanitize_filename(filename)
            target_path = self._build_attachment_path(message_id, safe_name)
            target_path.write_bytes(self._decode_base64_url(attachment_data))
            stored_files.append(str(target_path))

        return stored_files

    def _walk_parts(self, part: dict) -> list[dict]:
        parts = [part]
        for child in part.get("parts", []):
            parts.extend(self._walk_parts(child))
        return parts

    def _build_attachment_path(self, message_id: str, filename: str) -> Path:
        return self.config.attachments_dir / f"{message_id}_{filename}"

    def _decode_base64_url(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)

    def _import_google_auth_modules(self) -> tuple[object, object, object] | None:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            return None

        return Request, Credentials, InstalledAppFlow

    def _import_google_api_modules(self) -> tuple[object, object] | None:
        try:
            from googleapiclient.discovery import build
        except ImportError:
            return None

        return build, None
