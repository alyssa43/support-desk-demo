"""Record four fixed, synthetic cases; never alters the original recordings.

Run through scripts/saisei.py so credentials and registered version target AWS.
Each invocation creates a separate timestamped evidence directory.
"""
import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kitaru_openai_agents import KitaruRunner
from support_desk.main import to_input
from support_desk.specialists import build_agent, build_run_config

async def main():
    case_ids = ["refund-01", "refund-04", "refund-10", "refund-11"]
    dataset = ROOT / "datasets/refund-cases-v1.json"
    cases = json.loads(dataset.read_text())
    if isinstance(cases, dict):
        cases = cases["cases"]
    selected = [next(c for c in cases if c["id"] == case_id) for case_id in case_ids]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "sessions" / f"aws_smoke_{stamp}_{uuid.uuid4().hex[:6]}"
    evidence.mkdir(parents=True)
    manifest = {
        "server_url": os.environ["KITARU_API_URL"],
        "agent_id": os.environ["SUPPORT_DESK_AGENT_ID"],
        "agent_version_id": os.environ["SUPPORT_DESK_AGENT_VERSION_ID"],
        "model": os.environ["OPENAI_MODEL"],
        "prompt": os.environ["REFUND_PROMPT"],
        "dataset": str(dataset.relative_to(ROOT)),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256((ROOT / "prompts" / (os.environ["REFUND_PROMPT"] + ".md")).read_bytes()).hexdigest(),
        "cases": case_ids, "sessions": [],
        "expected": {c["id"]: c["expected_action"] for c in selected},
    }
    checkpoint = evidence / "recording.json"
    def save():
        checkpoint.write_text(json.dumps(manifest, indent=2) + "\n")
    save()
    print(f"Evidence: {evidence}", flush=True)
    for case in selected:
        def observed(session):
            manifest["sessions"].append({"case_id": case["id"], "session_id": str(session.id)})
            save()
        runner = KitaruRunner(
            agent_id=uuid.UUID(manifest["agent_id"]),
            agent_version_id=uuid.UUID(manifest["agent_version_id"]),
            session_name=f"AWS smoke {case['id']}", session_observer=observed,
        )
        try:
            result = await runner.run(build_agent("refund"), to_input(case, 1), run_config=build_run_config())
        except Exception as exc:
            manifest["recording_error"] = type(exc).__name__
            save()
            raise
        manifest["sessions"][-1]["output"] = result.final_output
        save()
        print(f"{case['id']}: {result.final_output}", flush=True)
    (evidence / "sessions.txt").write_text("".join(s["session_id"] + "\n" for s in manifest["sessions"]))
    print("Recorded all four cases.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
