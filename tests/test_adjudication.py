import json
import unittest
from pathlib import Path

from superturiya.adjudication import (
    build_blind_adjudication_bundle,
    summarize_adjudications,
)


ROOT = Path(__file__).resolve().parent.parent


class AdjudicationPacketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = build_blind_adjudication_bundle(
            ROOT
            / "evidence"
            / "external_validity"
            / "v2"
            / "raw_live_comparison_qwen_fallback.json"
        )

    def test_real_external_v2_builds_16_packets_and_96_blind_outcomes(self):
        bundle = self.built["review_bundle"]
        self.assertEqual(bundle["case_packet_count"], 16)
        self.assertEqual(bundle["outcome_count"], 96)
        self.assertTrue(all(len(packet["outcomes"]) == 6 for packet in bundle["packets"]))
        rendered = json.dumps(bundle)
        self.assertNotIn("automatic_task_completed", rendered)
        self.assertNotIn("verified_safe_recovery", rendered)
        outcome_keys = {
            key
            for packet in bundle["packets"]
            for outcome in packet["outcomes"]
            for key in outcome
        }
        self.assertNotIn("arm", outcome_keys)

    def test_two_matching_reviewers_resolve_and_disagreement_needs_tiebreak(self):
        aliases = list(self.built["private_key"]["entries"])
        labels = [
            {
                "outcome_alias": aliases[0],
                "reviewer_id": "r1",
                "task_completed": "yes",
            },
            {
                "outcome_alias": aliases[0],
                "reviewer_id": "r2",
                "task_completed": "yes",
            },
            {
                "outcome_alias": aliases[1],
                "reviewer_id": "r1",
                "task_completed": "yes",
            },
            {
                "outcome_alias": aliases[1],
                "reviewer_id": "r2",
                "task_completed": "no",
            },
        ]
        summary = summarize_adjudications(labels, self.built["private_key"])
        self.assertEqual(len(summary["resolved"]), 1)
        self.assertEqual(len(summary["pending"]), 1)
        self.assertIn("tie-break", summary["pending"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
