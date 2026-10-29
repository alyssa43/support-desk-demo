"""Check model-facing data locally, without running a model or recording."""

import asyncio
import contextlib
import io
import json
import unittest
from pathlib import Path

from agents.run_config import CallModelData, ModelInputData
from agents.tool_context import ToolContext
from kitaru.api_models.v1.replay_config import StaticConfig
from kitaru_openai_agents.inputs import normalize_openai_input
from kitaru_openai_agents.replay import _copy_static_tool

from support_desk.kitaru_args import tool_policy
from support_desk.specialists import (
    TOOLS_BY_ROUTE,
    build_run_config,
    show_model_only_message,
)
from support_desk.tools import issue_refund, lookup_order


ROOT = Path(__file__).resolve().parents[1]


def tool_context(tool, arguments):
    return ToolContext(context=None, tool_name=tool.name,
                       tool_call_id="offline-call", tool_arguments=arguments)


class ModelVisibilityTests(unittest.TestCase):
    def test_all_cases_hide_evaluation_metadata_on_first_and_later_calls(self):
        cases = json.loads((ROOT / "cases.json").read_text())
        filter_input = build_run_config().call_model_input_filter
        self.assertIs(filter_input, show_model_only_message)
        for case in cases:
            with self.subTest(case=case["id"]):
                # Include extra evaluation fields to verify that even an
                # accidentally expanded run input cannot expose these fields.
                run_input = {
                    **case, "case_id": case["id"], "route": "refund", "run": 3,
                    "evaluation_marker": "PRIVATE_EVALUATION_SENTINEL",
                }
                user_item = {"role": "user", "content": normalize_openai_input(run_input)}
                tool_result = {
                    "type": "function_call_output", "call_id": "call-lookup",
                    "output": '{"found":true,"order_id":"1003"}',
                }
                for history in [[user_item], [user_item, tool_result]]:
                    data = CallModelData(
                        agent=None, context=None,
                        model_data=ModelInputData(input=history, instructions="Support policy"),
                    )
                    visible = filter_input(data)
                    self.assertEqual(visible.input[0], {
                        "role": "user",
                        "content": f"Order ID: {case['order_id']}\n\n{case['message']}",
                    })
                    self.assertEqual(visible.instructions, "Support policy")
                    self.assertNotIn("PRIVATE_EVALUATION_SENTINEL", json.dumps(visible.input))
                    if len(history) > 1:
                        self.assertEqual(visible.input[1], tool_result)
                    # The recorded input stays intact for evaluators.
                    self.assertEqual(json.loads(user_item["content"]), run_input)

    def test_tool_surface_and_prompts_do_not_announce_simulation(self):
        self.assertEqual([tool.name for tool in TOOLS_BY_ROUTE["refund"]],
                         ["lookup_order", "issue_refund"])
        for tool in TOOLS_BY_ROUTE["refund"]:
            visible_schema = json.dumps({
                "name": tool.name, "description": tool.description,
                "parameters": tool.params_json_schema,
            }).lower()
            for marker in ["fake", "mock", "replay", "evaluation", "expected_action"]:
                self.assertNotIn(marker, visible_schema)
        for prompt_file in (ROOT / "prompts").glob("refund_*.md"):
            prompt = prompt_file.read_text().lower()
            for marker in ["fake", "mock", "replay", "evaluation", "case_id"]:
                self.assertNotIn(marker, prompt)

    def test_refund_confirmation_matches_replay_without_exposing_local_log(self):
        args = json.dumps({"order_id": "1003", "reason": "Damaged shirt"})
        local_log = io.StringIO()
        with contextlib.redirect_stderr(local_log):
            baseline = asyncio.run(issue_refund.on_invoke_tool(
                tool_context(issue_refund, args), args,
            ))
        self.assertIn("would refund", local_log.getvalue())
        self.assertEqual(baseline, "Refund issued.")

        config = StaticConfig.model_validate(tool_policy("refund")["tools"]["issue_refund"])
        replay_tool = _copy_static_tool(issue_refund, config)
        replay_log = io.StringIO()
        with contextlib.redirect_stderr(replay_log):
            replay = asyncio.run(replay_tool.on_invoke_tool(
                tool_context(replay_tool, args), args,
            ))
        self.assertEqual(replay, baseline)
        self.assertEqual(replay_log.getvalue(), "")
        self.assertEqual(replay_tool.description, issue_refund.description)
        self.assertEqual(replay_tool.params_json_schema, issue_refund.params_json_schema)

    def test_lookup_results_contain_order_data_without_fixture_metadata(self):
        cases = json.loads((ROOT / "cases.json").read_text())
        for order_id in {case["order_id"] for case in cases}:
            with self.subTest(order=order_id):
                args = json.dumps({"order_id": order_id})
                result = asyncio.run(lookup_order.on_invoke_tool(
                    tool_context(lookup_order, args), args,
                ))
                self.assertEqual(result["order_id"], order_id)
                self.assertIn("found", result)
                self.assertTrue(set(result) <= {
                    "found", "order_id", "item", "size", "status",
                    "days_since_delivery", "damaged", "eta_days",
                })


if __name__ == "__main__":
    unittest.main()
