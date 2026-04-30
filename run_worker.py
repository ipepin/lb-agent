from __future__ import annotations

import sys

from app.worker import run_worker


if __name__ == "__main__":
    run_worker(once="--once" in sys.argv)
