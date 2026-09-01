import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import (  # noqa: E402
    canonical_rows,
    compare_loads,
    pair_analysis,
    read_deliveries,
    read_recommended_pairs,
    read_statuses,
    tracking_summary,
)


class RecommendationTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = read_deliveries(ROOT / "data" / "delivery_load_1.csv")
        cls.current = read_deliveries(ROOT / "data" / "delivery_load_2.csv")
        cls.canonical = canonical_rows(cls.current)
        cls.statuses, cls.horizon = read_statuses(ROOT / "data" / "status_history.csv")

    def test_multiset_delta_preserves_duplicates_and_flags_ambiguity(self):
        self.assertEqual(
            compare_loads(self.previous, self.current),
            {"added": 3, "removed": 3, "unchanged": 7, "ambiguous_keys": 1},
        )

    def test_canonical_row_is_earliest_then_source_order(self):
        self.assertEqual(len(self.canonical), 9)
        sim5 = next(row for row in self.canonical if str(row["iccid"]).endswith("0005F"))
        self.assertEqual((sim5["platform"], sim5["equipment"]), ("WEB", "ALPHA ONE"))

    def test_inventory_and_maturation_match_known_cohorts(self):
        summary = tracking_summary(self.canonical, self.statuses, self.horizon)
        self.assertEqual((summary["consumed"], summary["remaining"], summary["overage"]), (8, 12, 0))
        self.assertEqual(summary["cycle_consumed"], {"1": 5, "2": 1, "3": 2})
        self.assertEqual(summary["outcomes"]["activation_7"], {"matured": 8, "activated": 4, "rate": 0.5})
        self.assertEqual(summary["outcomes"]["activation_30"], {"matured": 8, "activated": 6, "rate": 0.75})
        self.assertEqual(summary["outcomes"]["retention_61"], {"matured": 5, "retained": 3, "rate": 0.6})

    def test_pair_analysis_marks_versioned_recommendations(self):
        version, recommended = read_recommended_pairs(ROOT / "data" / "recommended_pairs.csv")
        pairs = pair_analysis(self.canonical, self.statuses, self.horizon, recommended)
        self.assertEqual(version, "demo-v1")
        self.assertEqual(sum(row["recommended"] for row in pairs), 2)
        web = next(row for row in pairs if row["platform"] == "WEB")
        self.assertEqual((web["deliveries"], web["matured_61"], web["retained"]), (5, 3, 2))


if __name__ == "__main__":
    unittest.main()
