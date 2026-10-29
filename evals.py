"""Kitaru evaluators. This file is uploaded to Kitaru and runs in the worker.

Checks refund action selection, count, and target order, using recorded tool
calls rather than the agent's prose. This does not grade reply quality, lookup
ordering, or real payment outcomes. The answer key arrives as the `expected`
parameter, so the agent never sees it. Missing evidence raises an evaluation
error instead of producing an agent-quality verdict.
"""

from kitaru.task.evaluator import EvaluationResult, SessionView


def _order_id(value: object) -> str | None:
    """Match the normalization used by the demo's lookup_order tool."""
    if not isinstance(value, str):
        return None
    return value.strip().lstrip("#") or None


def action_correct(
    view: SessionView, expected: dict[str, str] | None = None
) -> EvaluationResult:
    """Require one refund to the requested order when eligible, otherwise zero.

    Repeated read-only lookups are allowed. Any other action tool fails. Failed
    or incomplete sessions and missing tool payloads remain evaluation errors.
    """
    if expected is None:
        raise ValueError("action_correct needs the 'expected' answer-key parameter")
    inputs = view.session.inputs
    if not isinstance(inputs, dict) or not inputs.get("case_id"):
        raise ValueError("Session input must include case_id and order_id")
    case_id = inputs["case_id"]
    if case_id not in expected:
        raise ValueError(f"No expected action configured for {case_id}")
    want = expected[case_id]
    if want not in {"issue_refund", "none"}:
        raise ValueError(f"Unsupported expected action for {case_id}: {want}")
    order_id = _order_id(inputs.get("order_id"))
    if order_id is None:
        raise ValueError("Session input must include a nonempty string order_id")
    if view.session.status != "completed" or view.session.error:
        raise ValueError("Only completed, error-free sessions can be graded")
    if not view.nodes:
        raise ValueError("Session nodes are missing")
    tool_calls = [node for node in view.nodes if node.node_type == "tool_call"]
    if len(tool_calls) != view.session.tool_call_count:
        raise ValueError("Tool node count does not match the session; evidence is incomplete")
    for node in tool_calls:
        if node.status != "completed" or node.error:
            raise ValueError(f"Tool call {node.id} did not complete successfully")
        if not node.tool_name:
            raise ValueError(f"Tool call {node.id} is missing its tool name")

    actions = [node for node in tool_calls if node.tool_name != "lookup_order"]
    refunds = [node for node in actions if node.tool_name == "issue_refund"]
    for node in refunds:
        if not isinstance(node.inputs, dict):
            raise ValueError(f"Refund call {node.id} is missing its argument payload")
        if node.outputs is None:
            raise ValueError(f"Refund call {node.id} is missing its result payload")

    issues = []
    if want == "none" and actions:
        issues.append("no action was permitted")
    if want == "issue_refund" and len(refunds) != 1:
        issues.append(f"expected exactly one refund, observed {len(refunds)}")
    for node in actions:
        if node.tool_name != "issue_refund":
            issues.append(f"unexpected action tool {node.tool_name} (node {node.id})")
    for node in refunds:
        actual_order = _order_id(node.inputs.get("order_id"))
        if actual_order != order_id:
            issues.append(
                f"refund targeted {actual_order!r}, expected {order_id!r} (node {node.id})"
            )

    got = ", ".join(node.tool_name for node in actions) or "none"
    detail = "; ".join(issues) if issues else "action count and target match"
    passed = not issues
    return EvaluationResult(
        name="action_correct",
        passed=passed,
        score=passed,
        explanation=f"{case_id}: expected {want} for order {order_id}; observed {got}; {detail}",
    )
