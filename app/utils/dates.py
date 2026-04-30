from __future__ import annotations

from datetime import datetime, time, timezone


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def is_due_timestamp(value: str, now: datetime | None = None) -> bool:
    if not value:
        return False

    current = now or datetime.now(tz=timezone.utc)
    normalized = value.strip()

    try:
        dt_value = datetime.fromisoformat(normalized)
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=current.tzinfo)
        return dt_value <= current
    except ValueError:
        pass

    try:
        date_value = datetime.fromisoformat(f"{normalized}T00:00:00")
        date_value = date_value.replace(tzinfo=current.tzinfo)
        return date_value.date() <= current.date()
    except ValueError:
        pass

    try:
        time_value = time.fromisoformat(normalized)
        return current.time().replace(second=0, microsecond=0) >= time_value.replace(
            second=0,
            microsecond=0,
        )
    except ValueError:
        return False
