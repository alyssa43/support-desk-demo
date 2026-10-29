"""Keep the curated demo's identities and policy coverage intact."""

import json
import unittest
from pathlib import Path

from support_desk.data import ORDERS


class MockCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(
            (Path(__file__).resolve().parents[1] / "cases.json").read_text()
        )

    def test_twenty_unique_complete_cases(self):
        self.assertEqual(len(self.cases), 20)
        self.assertEqual({case["id"] for case in self.cases},
                         {f"refund-{number:02d}" for number in range(1, 21)})
        self.assertEqual(len({case["message"] for case in self.cases}), 20)
        self.assertEqual(len({case["scenario"] for case in self.cases}), 20)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["expected_route"], "refund")
                self.assertIn(case["expected_action"], {"issue_refund", "none"})
                self.assertIn(case["order_id"], case["message"])
                self.assertTrue(case["scenario"].strip())

    def test_cases_isolate_date_boundary_and_damage_requirement(self):
        orders = [ORDERS[case["order_id"]] for case in self.cases
                  if case["order_id"] in ORDERS]
        damaged_days = {order["days_since_delivery"] for order in orders
                        if order["status"] == "delivered" and order["damaged"]}
        self.assertTrue({29, 30, 31, 45} <= damaged_days)
        self.assertTrue(any(order["status"] == "delivered"
                            and order["days_since_delivery"] == 30
                            and not order["damaged"] for order in orders))
        self.assertTrue({"not_shipped", "in_transit"} <=
                        {order["status"] for order in orders})
        self.assertEqual(sum(case["order_id"] not in ORDERS
                             for case in self.cases), 2)

    def test_paired_messages_keep_the_same_policy_expectation(self):
        expected_by_order = {}
        for case in self.cases:
            expected_by_order.setdefault(case["order_id"], set()).add(case["expected_action"])
        self.assertTrue(all(len(actions) == 1 for actions in expected_by_order.values()))


if __name__ == "__main__":
    unittest.main()
