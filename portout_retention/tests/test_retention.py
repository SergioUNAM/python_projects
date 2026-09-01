import csv
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import enrich, summarize  # noqa: E402


class RetentionTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "data" / "portout_events.csv").open(encoding="utf-8") as handle:
            self.rows = list(csv.DictReader(handle))

    def test_invalid_or_missing_activation_falls_back_to_one_day(self):
        enriched = enrich(self.rows)
        corrected = [row for row in enriched if row["activation_corrected"]]
        self.assertEqual(len(corrected), 3)
        self.assertTrue(all(row["tenure_days"] == 1 for row in corrected))

    def test_early_abandonment_includes_estimated_sources(self):
        enriched = enrich(self.rows)
        estimated = [row for row in enriched if row["activation_source"] == "ESTIMATED"]
        self.assertTrue(all(row["early_abandonment"] for row in estimated))

    def test_summary_exposes_confidence_and_segments(self):
        summary = summarize(enrich(self.rows))
        self.assertEqual(summary["total"], 12)
        self.assertEqual(summary["confidence"], {"ESTIMATED": 2, "INFERRED": 3, "MEASURED": 7})
        self.assertEqual(sum(summary["segments"].values()), 12)


if __name__ == "__main__":
    unittest.main()

