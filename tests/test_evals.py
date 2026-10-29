"""Offline behavioral checks using the installed Kitaru session models."""

import asyncio
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from kitaru.task.evaluator import SessionView, call_evaluator

from evals import action_correct
from support_desk.data import ORDERS
from support_desk.kitaru_args import answer_key


def tool(name="issue_refund", order_id="1003"):
    return {
        "node_type": "tool_call",
        "tool_name": name,
        "inputs": {"order_id": order_id, "reason": "Customer requested a refund"},
        "outputs": "Fake tool result",
    }


def session_view(*calls, order_id="1003", case_id="example"):
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    nodes = []
    # Even a no-tool response has a model call in a complete recorded session.
    for spec in [{"node_type": "llm_call"}, *calls]:
        nodes.append({
            "id": uuid4(), "session_id": session_id, "external_id": str(uuid4()),
            "links": [], "name": "fixture", "status": "completed", "metadata": {},
            **spec,
        })
    return SessionView.model_validate({
        "session": {
            "id": session_id, "agent_id": uuid4(), "owner_id": uuid4(),
            "created": now, "updated": now, "number": 1, "origin": "recorded",
            "status": "completed", "metadata": {}, "llm_call_count": 1,
            "tool_call_count": len(calls),
            "inputs": {"case_id": case_id, "order_id": order_id},
            "outputs": "Synthetic customer reply",
        },
        "nodes": nodes,
    })


class ActionCorrectTests(unittest.TestCase):
    def grade(self, view, want="issue_refund"):
        return action_correct(view, {"example": want})

    def test_correct_refund_has_exact_binary_result(self):
        result = self.grade(session_view(tool("lookup_order"), tool()))
        self.assertEqual(result.model_dump(exclude_none=True), {
            "name": "action_correct", "score": True, "passed": True,
            "explanation": "example: expected issue_refund for order 1003; "
            "observed issue_refund; action count and target match",
        })

    def test_correct_decline(self):
        self.assertTrue(self.grade(session_view(tool("lookup_order")), "none").passed)

    def test_action_failures(self):
        examples = [
            ("missed refund", session_view(tool("lookup_order")), "issue_refund",
             "expected exactly one refund, observed 0"),
            ("unauthorized refund", session_view(tool()), "none", "no action was permitted"),
            ("duplicate refund", session_view(tool(), tool()), "issue_refund",
             "expected exactly one refund, observed 2"),
            ("wrong order", session_view(tool(order_id="1004")), "issue_refund",
             "refund targeted '1004', expected '1003'"),
            ("unexpected action", session_view(tool(), tool("issue_exchange")),
             "issue_refund", "unexpected action tool issue_exchange"),
            ("unknown action", session_view(tool("unrecognized_action")), "none",
             "unexpected action tool unrecognized_action"),
        ]
        for label, view, want, reason in examples:
            with self.subTest(label):
                result = self.grade(view, want)
                self.assertIs(result.passed, False)
                self.assertIs(result.score, False)
                self.assertIn(reason, result.explanation)

    def test_equivalent_order_format_and_repeated_lookups(self):
        view = session_view(tool("lookup_order"), tool("lookup_order"),
                            tool(order_id=" #1003 "))
        self.assertTrue(self.grade(view).passed)

    def test_metric_does_not_require_a_particular_lookup_sequence(self):
        self.assertTrue(self.grade(session_view(tool())).passed)
        self.assertTrue(self.grade(session_view(), "none").passed)

    def test_missing_order_argument_is_a_recorded_wrong_action(self):
        view = session_view(tool())
        view.nodes[-1].inputs = {"reason": "No order ID supplied"}
        self.assertFalse(self.grade(view).passed)

    def test_missing_evidence_and_dependency_errors_do_not_get_a_verdict(self):
        examples = []
        for status in ["failed", "in_progress"]:
            view = session_view(tool())
            view.session.status = status
            examples.append((f"session {status}", view))
        view = session_view(tool())
        view.session.error = "Provider unavailable"
        examples.append(("session error", view))
        view = session_view()
        view.nodes = []
        examples.append(("missing nodes", view))
        view = session_view(tool())
        view.nodes.pop()
        examples.append(("incomplete node list", view))
        for field, value in [("inputs", None), ("outputs", None), ("tool_name", None),
                             ("status", "failed"), ("error", "Tool unavailable")]:
            view = session_view(tool())
            setattr(view.nodes[-1], field, value)
            examples.append((f"tool {field}", view))
        for label, view in examples:
            with self.subTest(label), self.assertRaises(ValueError):
                self.grade(view)

    def test_bad_configuration_does_not_get_a_verdict(self):
        view = session_view(tool())
        for expected in [None, {}, {"example": "issue_exchange"}]:
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                action_correct(view, expected)
        for inputs in [None, {}, {"case_id": "example"}]:
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                view.session.inputs = inputs
                self.grade(view)

    def test_installed_kitaru_invocation_contract(self):
        results = asyncio.run(call_evaluator(
            "action_correct", action_correct, session_view(tool()),
            {"expected": {"example": "issue_refund"}},
        ))
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)

    def test_all_twenty_cases_score_correct_and_incorrect_actions(self):
        cases = json.loads((Path(__file__).resolve().parents[1] / "cases.json").read_text())
        expected = answer_key("refund")["expected"]
        self.assertEqual(len(cases), 20)
        self.assertEqual(list(expected.values()).count("issue_refund"), 8)
        for case in cases:
            with self.subTest(case=case["id"]):
                order = ORDERS.get(case["order_id"])
                eligible = order is not None and (
                    order["status"] == "not_shipped" or (
                        order["status"] == "delivered" and order["damaged"]
                        and order["days_since_delivery"] <= 30
                    )
                )
                # Independently check the proposed answer key against the shop policy.
                self.assertEqual(expected[case["id"]], "issue_refund" if eligible else "none")
                for should_refund in [False, True]:
                    calls = [tool("lookup_order", case["order_id"])]
                    if should_refund:
                        calls.append(tool(order_id=case["order_id"]))
                    view = session_view(*calls, order_id=case["order_id"], case_id=case["id"])
                    self.assertEqual(action_correct(view, expected).passed,
                                     should_refund == eligible)


if __name__ == "__main__":
    unittest.main()
