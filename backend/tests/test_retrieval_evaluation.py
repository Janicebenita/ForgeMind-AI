from __future__ import annotations

import unittest
from pathlib import Path

from scripts.evaluate_retrieval import evaluate


class RetrievalEvaluationTests(unittest.TestCase):
    def test_labelled_retrieval_baseline_is_repeatable(self) -> None:
        cases = Path(__file__).resolve().parents[1] / "evaluation" / "retrieval_cases.json"
        report = evaluate(cases, top_k=5)

        self.assertEqual(report["case_count"], 8)
        self.assertIsNotNone(report["mean_recall_at_k"])
        self.assertIsNotNone(report["mean_reciprocal_rank"])
        self.assertIsNotNone(report["negative_abstention_accuracy"])
        self.assertGreaterEqual(report["passed_cases"], 6)


if __name__ == "__main__":
    unittest.main()
