"""Small, auditable demo for spreadsheet transfer, mapping, review, and QA.

This intentionally does not pretend to automate human judgment. Only explicit,
high-confidence patterns are moved; ambiguous fragments remain in Notes and are
added to a review queue.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, asdict
from pathlib import Path


AUTO_MAP_THRESHOLD = 0.80


@dataclass
class ReviewItem:
    lead_id: str
    source_field: str
    fragment: str
    suggested_field: str
    confidence: float
    reason: str


def compact_notes(value: str) -> str:
    value = (value or "").replace("\\n", "\n").replace("\\r", "\r")
    pieces = [re.sub(r"\s+", " ", item).strip(" /;") for item in re.split(r"[\r\n]+", value)]
    return " / ".join(item for item in pieces if item)


def split_notes(value: str) -> list[str]:
    value = (value or "").replace("\\n", "\n").replace("\\r", "\r")
    return [item.strip() for item in re.split(r"[\r\n]+", value) if item.strip()]


def normalize_timeline(value: str) -> str:
    value = (value or "").strip()
    return value[1:] if value.startswith("$") and value[1:].upper().startswith("Q") else value


def classify_fragment(fragment: str) -> tuple[str, str, float, str] | None:
    patterns = [
        (r"^phone\s*:\s*(.+)$", "phone", 0.98, "explicit label"),
        (r"^(?:preferred|contact preference)\s*:\s*(email|phone|whatsapp)$", "contact_preference", 0.96, "explicit label"),
        (r"^budget\s*(?::|around)?\s*(.+)$", "budget", 0.94, "explicit budget cue"),
        (r"^timeline\s*:\s*(.+)$", "timeline", 0.96, "explicit label"),
        (r"^interested in\s+(workshop|coaching|consulting)$", "interest", 0.92, "explicit interest cue"),
    ]
    for pattern, field, confidence, reason in patterns:
        match = re.match(pattern, fragment, flags=re.I)
        if match:
            return field, match.group(1).strip(), confidence, reason

    lower = fragment.lower()
    if "coaching or consulting" in lower or ("workshop" in lower and "consulting" in lower):
        return "interest", fragment, 0.55, "multiple plausible destinations"
    if "email preferred" in lower:
        return "contact_preference", "Email", 0.88, "clear preference phrase"
    if "whatsapp" in lower and "prefers" in lower:
        return "contact_preference", "WhatsApp", 0.88, "clear preference phrase"
    return None


def process_row(row: dict[str, str]) -> tuple[dict[str, str], list[ReviewItem], int]:
    cleaned = {key: (value or "").strip() for key, value in row.items()}
    cleaned["timeline"] = normalize_timeline(cleaned.get("timeline", ""))
    reviews: list[ReviewItem] = []
    mapped_count = 0

    # Detect a clearly mislabeled value under Phone.
    phone_value = cleaned.get("phone", "")
    if phone_value.lower().startswith("budget:"):
        suggested = phone_value.split(":", 1)[1].strip()
        if not cleaned.get("budget"):
            cleaned["budget"] = suggested
            cleaned["phone"] = ""
            mapped_count += 1
        else:
            reviews.append(ReviewItem(cleaned["lead_id"], "phone", phone_value, "budget", 0.78, "destination already populated"))

    residual: list[str] = []
    for fragment in split_notes(cleaned.get("notes", "")):
        classified = classify_fragment(fragment)
        if classified is None:
            residual.append(fragment)
            continue
        field, value, confidence, reason = classified
        if confidence >= AUTO_MAP_THRESHOLD and not cleaned.get(field):
            cleaned[field] = normalize_timeline(value) if field == "timeline" else value
            mapped_count += 1
        elif confidence >= AUTO_MAP_THRESHOLD and cleaned.get(field) == value:
            mapped_count += 1
        else:
            reviews.append(ReviewItem(cleaned["lead_id"], "notes", fragment, field, confidence, reason if confidence < AUTO_MAP_THRESHOLD else "destination already populated"))
            residual.append(fragment)

    cleaned["notes"] = compact_notes("\n".join(residual))
    cleaned["review_status"] = "REVIEW" if reviews else "READY"
    cleaned["mapped_fragments"] = str(mapped_count)
    return cleaned, reviews, mapped_count


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(source_path: Path, output_dir: Path) -> dict[str, object]:
    with source_path.open(encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    cleaned_rows: list[dict[str, str]] = []
    review_items: list[ReviewItem] = []
    mapped_total = 0
    for row in source_rows:
        cleaned, reviews, mapped = process_row(row)
        cleaned_rows.append(cleaned)
        review_items.extend(reviews)
        mapped_total += mapped

    cleaned_fields = list(source_rows[0].keys()) + ["review_status", "mapped_fragments"]
    write_csv(output_dir / "cleaned_leads.csv", cleaned_rows, cleaned_fields)
    review_fields = ["lead_id", "source_field", "fragment", "suggested_field", "confidence", "reason"]
    write_csv(output_dir / "review_queue.csv", [asdict(item) for item in review_items], review_fields)

    ids = [row["lead_id"] for row in cleaned_rows]
    qa_rows = [
        {"check": "Row count reconciles", "value": len(cleaned_rows), "expected": len(source_rows), "status": "PASS" if len(cleaned_rows) == len(source_rows) else "FAIL"},
        {"check": "Lead IDs unique", "value": len(set(ids)), "expected": len(ids), "status": "PASS" if len(set(ids)) == len(ids) else "FAIL"},
        {"check": "No blank lead IDs", "value": sum(not value for value in ids), "expected": 0, "status": "PASS" if all(ids) else "FAIL"},
        {"check": "Notes contain no line breaks", "value": sum("\n" in row["notes"] or "\r" in row["notes"] for row in cleaned_rows), "expected": 0, "status": "PASS" if all("\n" not in row["notes"] and "\r" not in row["notes"] for row in cleaned_rows) else "FAIL"},
        {"check": "High-confidence fragments mapped", "value": mapped_total, "expected": ">= 1", "status": "PASS" if mapped_total >= 1 else "FAIL"},
        {"check": "Ambiguities isolated for review", "value": len(review_items), "expected": ">= 1", "status": "PASS" if review_items else "FAIL"},
    ]
    write_csv(output_dir / "qa_report.csv", qa_rows, ["check", "value", "expected", "status"])
    return {"source_rows": len(source_rows), "cleaned_rows": len(cleaned_rows), "mapped_fragments": mapped_total, "review_items": len(review_items)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(run(root / "data" / "synthetic_source.csv", root / "outputs"))

