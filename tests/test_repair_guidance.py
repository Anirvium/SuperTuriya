import unittest

from superturiya.adaptive import AdaptiveEvaluationRunner
from superturiya.repair_guidance import ReplayGuidedRepairSelector


class ReplayGuidedRepairSelectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = AdaptiveEvaluationRunner()
        cls.selector = ReplayGuidedRepairSelector(
            cls.runner.workload,
            cls.runner.verifier,
        )

    def _case(self, case_id):
        return next(case for case in self.runner.cases if case["case_id"] == case_id)

    def test_catalog_is_pruned_by_decisive_invariant(self):
        case = self._case("eval-006")
        original = self.runner.verifier.verify(case, self.runner.workload.run(case))
        investigation = self.runner.investigator.investigate(case, original, "frozen")[
            "output"
        ]
        result = self.selector.select(case, investigation)
        self.assertTrue(result["verified_safe_recovery"])
        self.assertFalse(result["abstained"])
        self.assertEqual(
            result["selected_surface"],
            "tool_argument.constraint::fulfill.quantity",
        )
        self.assertEqual(len(result["candidate_surfaces"]), 3)
        self.assertTrue(
            all(
                "tool.quantity_is_positive_integer" in item["declared_effects"]
                for item in result["candidate_evaluations"]
            )
        )

    def test_selector_abstains_when_one_patch_cannot_repair_multi_causal_case(self):
        case = self._case("eval-012")
        original = self.runner.verifier.verify(case, self.runner.workload.run(case))
        investigation = self.runner.investigator.investigate(case, original, "frozen")[
            "output"
        ]
        result = self.selector.select(case, investigation)
        self.assertTrue(result["abstained"])
        self.assertFalse(result["verified_safe_recovery"])
        self.assertIsNone(result["recommended_intervention"])

    def test_one_patch_oracle_exposes_the_mechanical_ceiling(self):
        report = self.selector.oracle_ceiling(self.runner.cases)
        self.assertEqual(report["eligible_initial_failures"], 12)
        self.assertEqual(report["one_patch_recoverable"], 11)
        self.assertEqual(report["ceiling_rate"], 0.9167)
        self.assertEqual(len(report["report_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
