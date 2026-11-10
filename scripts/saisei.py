"""Run the demo or Kitaru CLI against the AWS server through an open SSM tunnel.

    .venv/bin/python scripts/saisei.py kitaru status
    .venv/bin/python scripts/saisei.py python scripts/aws_smoke.py
    .venv/bin/python scripts/saisei.py kitaru worker start --concurrency 10
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

def main():
    connection = ROOT / ".env.saisei"
    if not connection.is_file():
        raise SystemExit("Missing .env.saisei; configure this machine's AWS Kitaru connection first.")
    if len(sys.argv) < 2 or sys.argv[1] not in {"python", "kitaru"}:
        raise SystemExit("Usage: python scripts/saisei.py {python|kitaru} [arguments...]")
    load_dotenv(ROOT / ".env")
    load_dotenv(connection, override=True)
    os.environ.setdefault("KITARU_ACTIVE_SKILL", "kitaru-investigation")
    os.chdir(ROOT)
    executable = Path(sys.executable) if sys.argv[1] == "python" else ROOT / ".venv/bin/kitaru"
    # Keep the virtualenv path: resolving its symlink would select system Python.
    os.execv(str(executable), [str(executable), *sys.argv[2:]])

if __name__ == "__main__":
    main()
