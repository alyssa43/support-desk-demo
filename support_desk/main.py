"""Runs specialist agents through Kitaru's OpenAI Agents SDK adapter.

    python -m support_desk.main record refund              # each refund case once
    python -m support_desk.main record refund --repeat 3   # each refund case 3 times
    python -m support_desk.main task                       # what the Kitaru worker runs on replay

Each run's input is {case_id, run, route, order_id, message}. Kitaru records all
of it, but the model only sees order_id and message (see specialists.py). The
route is already decided, so replaying a specialist never calls the router.
"""

import argparse
import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Never overrides variables the Kitaru worker already set for a task.
load_dotenv()

from kitaru_openai_agents import KitaruRunner  # noqa: E402

from support_desk.specialists import build_agent, build_run_config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT / "sessions"


def load_cases() -> list[dict]:
    return json.loads((ROOT / "cases.json").read_text())


def to_input(case: dict, run: int) -> dict:
    return {
        "case_id": case["id"],
        "run": run,
        "route": case["expected_route"],
        "order_id": case["order_id"],
        "message": case["message"],
    }


async def record(route: str, repeat: int) -> None:
    """Record each test case for one route `repeat` times, one session per run.

    Session IDs go to a new file each time, so earlier recordings never mix in.
    """
    cases = [case for case in load_cases() if case["expected_route"] == route]
    SESSIONS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    ids_file = SESSIONS_DIR / f"{route}_x{repeat}_{stamp}.txt"

    def save_session_id(session) -> None:
        with ids_file.open("a") as f:
            f.write(f"{session.id}\n")

    for case in cases:
        for run in range(1, repeat + 1):
            runner = KitaruRunner(
                agent_id=uuid.UUID(os.environ["SUPPORT_DESK_AGENT_ID"]),
                agent_version_id=(
                    uuid.UUID(os.environ["SUPPORT_DESK_AGENT_VERSION_ID"])
                    if os.environ.get("SUPPORT_DESK_AGENT_VERSION_ID") else None
                ),
                session_name=f"{case['id']} run {run}",
                session_observer=save_session_id,
            )
            result = await runner.run(
                build_agent(route), to_input(case, run), run_config=build_run_config()
            )
            print(f"--- {case['id']} run {run}: {case['message']}\n{result.final_output}\n")

    print(f"Session IDs written to {ids_file.relative_to(ROOT)}")


async def task() -> None:
    """Run one case inside a Kitaru worker. Kitaru supplies the input."""
    run_input = json.loads(os.environ["KITARU_TASK_INPUTS"])
    await KitaruRunner().run(
        build_agent(run_input["route"]), run_input, run_config=build_run_config()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python -m support_desk.main")
    commands = parser.add_subparsers(dest="command", required=True)
    record_parser = commands.add_parser("record", help="record test cases locally")
    record_parser.add_argument("route", help="e.g. refund")
    record_parser.add_argument("--repeat", type=int, default=1,
                               help="record each case N times (default 1)")
    commands.add_parser("task", help="run one case inside a Kitaru worker")
    args = parser.parse_args()

    if args.command == "record":
        asyncio.run(record(args.route, args.repeat))
    else:
        asyncio.run(task())
