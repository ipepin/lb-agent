from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    attachments_dir: Path
    db_path: Path
    sync_state_path: Path
    agent_poll_interval_seconds: int
    notification_channel: str
    gmail_credentials_path: Path
    gmail_token_path: Path
    gmail_query: str
    openai_api_key: str
    openai_model: str
    openai_reasoning_effort: str
    google_calendar_id: str
    google_calendar_token_path: Path | None = None
    google_calendar_timezone: str = "Europe/Prague"
    idoklad_client_id: str = ""
    idoklad_client_secret: str = ""
    auth_session_secret: str = "lb-agent-dev-secret"
    bootstrap_owner_email: str = "pepa"
    bootstrap_owner_password: str = "p"
    bootstrap_owner_name: str = "Pepa"
    bootstrap_admin_email: str = "michal"
    bootstrap_admin_password: str = "m"
    bootstrap_admin_name: str = "Michal"


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _resolve_path(project_root: Path, value: str, default: Path) -> Path:
    raw_path = Path(value) if value else default
    if raw_path.is_absolute():
        return raw_path
    return project_root / raw_path


def load_config() -> AppConfig:
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    _load_env_file(env_path)

    data_dir = project_root / "data"
    attachments_dir = data_dir / "attachments"
    db_path = data_dir / "app.db"
    sync_state_path = _resolve_path(
        project_root=project_root,
        value=os.getenv("SYNC_STATE_PATH", ""),
        default=project_root / "data" / "last_sync.txt",
    )
    gmail_credentials_path = _resolve_path(
        project_root=project_root,
        value=os.getenv("GMAIL_CREDENTIALS_PATH", ""),
        default=project_root / "credentials.json",
    )
    gmail_token_path = _resolve_path(
        project_root=project_root,
        value=os.getenv("GMAIL_TOKEN_PATH", ""),
        default=project_root / "data" / "gmail_token.json",
    )
    google_calendar_token_path = _resolve_path(
        project_root=project_root,
        value=os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", ""),
        default=project_root / "data" / "google_calendar_token.json",
    )

    return AppConfig(
        project_root=project_root,
        data_dir=data_dir,
        attachments_dir=attachments_dir,
        db_path=db_path,
        sync_state_path=sync_state_path,
        agent_poll_interval_seconds=int(os.getenv("AGENT_POLL_INTERVAL_SECONDS", "300")),
        notification_channel=os.getenv("NOTIFICATION_CHANNEL", "log"),
        gmail_credentials_path=gmail_credentials_path,
        gmail_token_path=gmail_token_path,
        gmail_query=os.getenv("GMAIL_QUERY", "-in:spam -in:trash -in:sent"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "5dbb896af6fddde4fc0c53ef334d3c6686fe51ae1c0a600de653c2a7595f2293@group.calendar.google.com"),
        google_calendar_token_path=google_calendar_token_path,
        google_calendar_timezone=os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Prague"),
        idoklad_client_id=os.getenv("IDOKLAD_CLIENT_ID", ""),
        idoklad_client_secret=os.getenv("IDOKLAD_CLIENT_SECRET", ""),
        auth_session_secret=os.getenv("AUTH_SESSION_SECRET", "lb-agent-dev-secret"),
        bootstrap_owner_email=os.getenv("BOOTSTRAP_OWNER_EMAIL", "pepa"),
        bootstrap_owner_password=os.getenv("BOOTSTRAP_OWNER_PASSWORD", "p"),
        bootstrap_owner_name=os.getenv("BOOTSTRAP_OWNER_NAME", "Pepa"),
        bootstrap_admin_email=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "michal"),
        bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "m"),
        bootstrap_admin_name=os.getenv("BOOTSTRAP_ADMIN_NAME", "Michal"),
    )
