import csv
import tempfile
import unittest
from pathlib import Path

from src.clean_mapping import AUTO_MAP_THRESHOLD, compact_notes, process_row, run


class CleaningDemoTests(unittest.TestCase):
    def test_notes_are_compacted_with_slashes(self):
        self.assertEqual(compact_notes("A\nB\r\nC"), "A / B / C")
        self.assertEqual(compact_notes(r"A\nB\nC"), "A / B / C")

    def test_misplaced_budget_is_moved_out_of_phone(self):
        row = {"lead_id": "X", "phone": "Budget: $7,500", "budget": "", "timeline": "", "notes": "", "full_name": "", "email": "", "company": "", "interest": "", "contact_preference": ""}
        cleaned, reviews, _ = process_row(row)
        self.assertEqual(cleaned["budget"], "$7,500")
        self.assertEqual(cleaned["phone"], "")
        self.assertFalse(reviews)

    def test_explicit_note_maps_at_high_confidence(self):
        row = {"lead_id": "X", "phone": "", "budget": "", "timeline": "", "notes": "Budget around $3,000", "full_name": "", "email": "", "company": "", "interest": "", "contact_preference": ""}
        cleaned, _, _ = process_row(row)
        self.assertEqual(cleaned["budget"], "$3,000")
        self.assertEqual(cleaned["notes"], "")

    def test_ambiguous_interest_is_not_guessed(self):
        fragment = "Maybe interested in coaching or consulting; unsure"
        row = {"lead_id": "X", "phone": "", "budget": "", "timeline": "", "notes": fragment, "full_name": "", "email": "", "company": "", "interest": "", "contact_preference": ""}
        cleaned, reviews, _ = process_row(row)
        self.assertEqual(cleaned["interest"], "")
        self.assertEqual(cleaned["notes"], fragment)
        self.assertEqual(len(reviews), 1)
        self.assertLess(reviews[0].confidence, AUTO_MAP_THRESHOLD)

    def test_existing_destination_is_not_overwritten(self):
        row = {"lead_id": "X", "phone": "", "budget": "$5,000", "timeline": "", "notes": "Budget around $3,000", "full_name": "", "email": "", "company": "", "interest": "", "contact_preference": ""}
        cleaned, reviews, _ = process_row(row)
        self.assertEqual(cleaned["budget"], "$5,000")
        self.assertEqual(len(reviews), 1)

    def test_pipeline_reconciles_counts_and_writes_outputs(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            summary = run(root / "data" / "synthetic_source.csv", Path(temp))
            self.assertEqual(summary["source_rows"], summary["cleaned_rows"])
            with (Path(temp) / "qa_report.csv").open(encoding="utf-8") as handle:
                self.assertTrue(all(row["status"] == "PASS" for row in csv.DictReader(handle)))


if __name__ == "__main__":
    unittest.main()

