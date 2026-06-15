from __future__ import annotations

from time import sleep

from app.config import AppConfig, load_config
from app.db.database import initialize_database
from app.services.agent_service import AgentService
from app.utils.logger import get_logger


logger = get_logger(__name__)


def bootstrap_worker(config: AppConfig | None = None) -> AppConfig:
    active_config = config or load_config()
    initialize_database(active_config)
    logger.info("Worker bootstrap completed.")
    return active_config


def run_worker(once: bool = False, config: AppConfig | None = None) -> None:
    active_config = bootstrap_worker(config)
    agent_service = AgentService(active_config)

    while True:
        try:
            result = agent_service.run_cycle()
        except Exception:
            logger.exception("Agent cycle failed.")
            if once:
                raise
        else:
            logger.info(
                "Agent cycle completed | emails=%s approvals=%s due_reminders=%s notifications=%s",
                result.checked_emails,
                result.pending_approvals,
                result.due_reminders,
                result.notifications_sent,
            )

        if once:
            return

        sleep(active_config.agent_poll_interval_seconds)
