from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name: str) -> None:
    script_path = PROJECT_ROOT / "scripts" / script_name
    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    print("== Full verification: unit + smoke + browser E2E ==")
    run_script("run_full_smoke.py")
    run_script("run_e2e.py")
    print("== All checks passed ==")


if __name__ == "__main__":
    main()
