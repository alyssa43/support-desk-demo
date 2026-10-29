"""Builds one specialist SDK agent per route from a versioned prompt file."""

import json
import os
from pathlib import Path

from agents import Agent, RunConfig
from agents.run_config import CallModelData, ModelInputData

from support_desk.tools import issue_refund, lookup_order

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

TOOLS_BY_ROUTE = {
    "refund": [lookup_order, issue_refund],
}


def build_agent(route: str) -> Agent:
    """Return the agent for a route, e.g. "refund".

    The prompt version comes from an env var such as REFUND_PROMPT=refund_v2
    and defaults to v1. Kitaru experiments can also replace it at replay time.
    """
    prompt_name = os.environ.get(f"{route.upper()}_PROMPT", f"{route}_v1")
    return Agent(
        name=f"{route}_agent",
        instructions=(PROMPTS_DIR / f"{prompt_name}.md").read_text(),
        tools=TOOLS_BY_ROUTE[route],
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-nano"),
    )


def build_run_config() -> RunConfig:
    """SDK run settings shared by recording and replay."""
    return RunConfig(call_model_input_filter=show_model_only_message)


def show_model_only_message(data: CallModelData) -> ModelInputData:
    """Make the model see only the order ID and the customer's message.

    Kitaru records the full run input {case_id, run, route, order_id, message}
    and passes it to the SDK as one JSON user message. The SDK calls this
    filter right before every model call, and we swap that JSON for plain text.
    """
    items = []
    for item in data.model_data.input:
        fields = _run_input_fields(item)
        if fields is not None:
            item = {**item, "content": f"Order ID: {fields['order_id']}\n\n{fields['message']}"}
        items.append(item)
    return ModelInputData(input=items, instructions=data.model_data.instructions)


def _run_input_fields(item) -> dict | None:
    """Return the run-input fields if this item is the JSON user message."""
    if not isinstance(item, dict) or item.get("role") != "user":
        return None
    try:
        fields = json.loads(item.get("content"))
    except (TypeError, ValueError):
        return None
    if isinstance(fields, dict) and {"order_id", "message"} <= fields.keys():
        return fields
    return None
