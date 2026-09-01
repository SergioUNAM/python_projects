from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def contiguous_ranges(values: list[int]) -> list[dict[str, int]]:
    if not values:
        return []
    ordered = sorted(set(values))
    groups: list[dict[str, int]] = []
    start = end = ordered[0]
    for value in ordered[1:]:
        if value == end + 1:
            end = value
            continue
        groups.append({"start": start, "end": end, "count": end - start + 1})
        start = end = value
    groups.append({"start": start, "end": end, "count": end - start + 1})
    return groups


def audit_range(rows: list[dict[str, str]], start_iccid: str, end_iccid: str) -> dict[str, object]:
    by_iccid = {row["iccid"]: row for row in rows}
    if start_iccid not in by_iccid or end_iccid not in by_iccid:
        raise ValueError("Both boundary ICCIDs must exist in the source data")

    start = int(by_iccid[start_iccid]["consecutive"])
    end = int(by_iccid[end_iccid]["consecutive"])
    if start > end:
        start, end = end, start

    bounded = [row for row in rows if start <= int(row["consecutive"]) <= end]
    bounded.sort(key=lambda row: int(row["consecutive"]))
    observed = [int(row["consecutive"]) for row in bounded]
    duplicates = sorted(value for value, count in Counter(observed).items() if count > 1)
    missing = sorted(set(range(start, end + 1)) - set(observed))
    gaps = contiguous_ranges(missing)

    enriched = []
    for number, row in enumerate(bounded, start=1):
        enriched.append({"sequence_number": number, **row})

    return {
        "start_iccid": start_iccid,
        "end_iccid": end_iccid,
        "start_consecutive": start,
        "end_consecutive": end,
        "expected_count": end - start + 1,
        "observed_count": len(bounded),
        "has_gaps": bool(gaps),
        "gaps": gaps,
        "duplicate_consecutives": duplicates,
        "status_counts": dict(sorted(Counter(row["inventory_status"] or "(blank)" for row in bounded).items())),
        "offer_counts": dict(sorted(Counter(row["offer"] or "(blank)" for row in bounded).items())),
        "records": enriched,
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run() -> dict[str, object]:
    with (ROOT / "data" / "sims.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = audit_range(rows, rows[0]["iccid"], rows[-1]["iccid"])
    output_dir = ROOT / "outputs"
    write_csv(output_dir / "audited_range.csv", result["records"], ["sequence_number", "iccid", "msisdn", "consecutive", "inventory_status", "offer"])
    write_csv(output_dir / "gaps.csv", result["gaps"], ["start", "end", "count"])
    summary = {key: value for key, value in result.items() if key != "records"}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

