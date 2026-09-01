import csv
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import parse_amount, parse_provider_text, reconcile  # noqa: E402


class ProviderReconciliationTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "data" / "internal_transactions.csv").open(encoding="utf-8") as handle:
            self.internal = list(csv.DictReader(handle))
        self.provider = (ROOT / "data" / "provider_report.tsv").read_text(encoding="utf-8")

    def test_localized_amounts_are_normalized(self):
        self.assertEqual(parse_amount("1.234,50"), 1234.50)
        self.assertEqual(parse_amount("$1,234.50"), 1234.50)

    def test_provider_parser_preserves_repeated_operations(self):
        parsed = parse_provider_text(self.provider)
        self.assertEqual(len(parsed[("9900000003", 150.0)]), 2)

    def test_reconciliation_is_bidirectional(self):
        result = reconcile(self.internal, self.provider)
        self.assertEqual(result["discrepancy_keys"], 2)
        self.assertEqual(result["missing_keys"], 2)
        self.assertEqual(result["missing_transactions"], 2)
        self.assertEqual(result["missing_amount"], 230.0)


if __name__ == "__main__":
    unittest.main()

