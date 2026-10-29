"""Prints the JSON arguments for Kitaru CLI commands, so nothing is hand-typed.

    python -m support_desk.kitaru_args answer-key refund   # evaluator params
    python -m support_desk.kitaru_args override refund_v2   # swap in a prompt
    python -m support_desk.kitaru_args tool-policy refund   # replay tool policy
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Recorded results are only for read-only tools. Side-effect tools never run
# on replay: they get a fixed fake result (the call itself is still recorded).
READ_ONLY_TOOLS = {"refund": ["lookup_order"]}
SIDE_EFFECT_TOOLS = {"refund": ["issue_refund"]}


def answer_key(route: str) -> dict:
    cases = json.loads((ROOT / "cases.json").read_text())
    return {
        "expected": {
            case["id"]: case["expected_action"]
            for case in cases
            if case["expected_route"] == route
        }
    }


def override(prompt_name: str) -> dict:
    return {"system_prompt": (ROOT / "prompts" / f"{prompt_name}.md").read_text()}


def tool_policy(route: str) -> dict:
    tools = {
        name: {"type": "history", "scope": "baseline", "on_miss": "passthrough"}
        for name in READ_ONLY_TOOLS[route]
    }
    for name in SIDE_EFFECT_TOOLS[route]:
        tools[name] = {
            "type": "static",
            # No "match", so this one case answers every call to the tool.
            "cases": [{"match_mode": "exact",
                       "result": "Refund issued."}],
            "on_miss": "fail",
        }
    return {"default": {"type": "passthrough"}, "tools": tools}


if __name__ == "__main__":
    builders = {"answer-key": answer_key, "override": override, "tool-policy": tool_policy}
    print(json.dumps(builders[sys.argv[1]](sys.argv[2])))
