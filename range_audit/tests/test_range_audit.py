import csv
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import audit_range, contiguous_ranges  # noqa: E402


class RangeAuditTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "data" / "sims.csv").open(encoding="utf-8") as handle:
            self.rows = list(csv.DictReader(handle))

    def test_contiguous_missing_values_are_grouped(self):
        self.assertEqual(contiguous_ranges([5, 12, 13]), [{"start": 5, "end": 5, "count": 1}, {"start": 12, "end": 13, "count": 2}])

    def test_expected_and_observed_counts_reconcile(self):
        result = audit_range(self.rows, self.rows[0]["iccid"], self.rows[-1]["iccid"])
        self.assertEqual(result["expected_count"], 20)
        self.assertEqual(result["observed_count"], 17)
        self.assertEqual(sum(gap["count"] for gap in result["gaps"]), 3)

    def test_missing_boundary_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_range(self.rows, "missing", self.rows[-1]["iccid"])


if __name__ == "__main__":
    unittest.main()

