"""Fake tools. Side-effect tools only print what they would have done."""

import sys

from agents import function_tool

from support_desk.data import ORDERS


@function_tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by its ID, e.g. "1003"."""
    order = ORDERS.get(order_id.strip().lstrip("#"))
    if order is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order_id": order_id, **order}


@function_tool
def issue_refund(order_id: str, reason: str) -> str:
    """Refund an order in full."""
    print(f"[side effect] would refund order {order_id}: {reason}", file=sys.stderr)
    return "Refund issued."
