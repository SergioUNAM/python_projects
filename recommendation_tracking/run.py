from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POLICY_START = date(2026, 1, 1)
STOCK_INITIAL = 20  # scaled fictional lot; production configuration is not exposed
CYCLES = [
    (1, date(2026, 1, 1), date(2026, 1, 31), 7),
    (2, date(2026, 2, 1), date(2026, 2, 28), 7),
    (3, date(2026, 3, 1), date(2026, 3, 31), 6),
]
HORIZONS = (7, 14, 30, 61)


def parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def normalize_platform(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "UNKNOWN").strip()).upper()


def normalize_equipment(value: str) -> str:
    text = re.sub(r"[^A-Z0-9]+", " ", (value or "UNKNOWN").upper()).strip()
    aliases = {"ALPHA 1": "ALPHA ONE", "BETA 2": "BETA 2"}
    return aliases.get(text, re.sub(r"\s+", " ", text))


def normalize_row(row: dict[str, str], source_row: int) -> dict[str, object]:
    normalized = {
        "source_row": source_row,
        "iccid": row["iccid"].strip().upper(),
        "delivery_date": parse_date(row["delivery_date"]),
        "platform": normalize_platform(row["platform"]),
        "equipment": normalize_equipment(row["equipment"]),
    }
    raw = "|".join([
        str(normalized["iccid"]),
        normalized["delivery_date"].isoformat(),
        str(normalized["platform"]),
        str(normalized["equipment"]),
    ])
    normalized["fingerprint"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return normalized


def read_deliveries(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [normalize_row(row, index) for index, row in enumerate(csv.DictReader(handle), 1)]


def compare_loads(previous: list[dict[str, object]], current: list[dict[str, object]]) -> dict[str, int]:
    old = Counter(str(row["fingerprint"]) for row in previous)
    new = Counter(str(row["fingerprint"]) for row in current)
    added = sum(max(count - old.get(key, 0), 0) for key, count in new.items())
    removed = sum(max(count - new.get(key, 0), 0) for key, count in old.items())
    unchanged = sum(min(count, old.get(key, 0)) for key, count in new.items())
    pairs_by_key: dict[tuple[str, date], set[tuple[str, str]]] = defaultdict(set)
    for row in current:
        pairs_by_key[(str(row["iccid"]), row["delivery_date"])].add(
            (str(row["platform"]), str(row["equipment"]))
        )
    ambiguous = sum(len(pairs) > 1 for pairs in pairs_by_key.values())
    return {"added": added, "removed": removed, "unchanged": unchanged, "ambiguous_keys": ambiguous}


def canonical_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: (str(row["iccid"]), row["delivery_date"], int(row["source_row"])))
    result: dict[str, dict[str, object]] = {}
    for row in ordered:
        result.setdefault(str(row["iccid"]), row)
    return list(result.values())


def read_statuses(path: Path) -> tuple[dict[str, list[tuple[date, str]]], date]:
    statuses: dict[str, list[tuple[date, str]]] = defaultdict(list)
    horizon: date | None = None
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            observed = parse_date(row["status_date"])
            statuses[row["iccid"].strip().upper()].append((observed, row["status"].strip().title()))
            horizon = observed if horizon is None or observed > horizon else horizon
    for observations in statuses.values():
        observations.sort()
    if horizon is None:
        raise ValueError("Status history must contain at least one observation")
    return statuses, horizon


def activated_within(row: dict[str, object], statuses: dict[str, list[tuple[date, str]]], days: int) -> bool:
    cutoff = row["delivery_date"] + timedelta(days=days)
    return any(
        observed <= cutoff and status != "Idle"
        for observed, status in statuses.get(str(row["iccid"]), [])
    )


def retained_at_61(row: dict[str, object], statuses: dict[str, list[tuple[date, str]]]) -> bool:
    cutoff = row["delivery_date"] + timedelta(days=61)
    candidates = [item for item in statuses.get(str(row["iccid"]), []) if item[0] <= cutoff]
    return bool(candidates and candidates[-1][1] == "Active")


def tracking_summary(canonical: list[dict[str, object]], statuses: dict[str, list[tuple[date, str]]], status_horizon: date) -> dict[str, object]:
    eligible = [row for row in canonical if POLICY_START <= row["delivery_date"] <= status_horizon]
    cycle_counts = {
        str(number): sum(start <= row["delivery_date"] <= end for row in eligible)
        for number, start, end, _target in CYCLES
    }
    outcomes: dict[str, object] = {}
    for days in HORIZONS:
        mature = [row for row in eligible if status_horizon >= row["delivery_date"] + timedelta(days=days)]
        activated = sum(activated_within(row, statuses, days) for row in mature)
        outcomes[f"activation_{days}"] = {
            "matured": len(mature),
            "activated": activated,
            "rate": round(activated / len(mature), 4) if mature else None,
        }
    mature_61 = [row for row in eligible if status_horizon >= row["delivery_date"] + timedelta(days=61)]
    retained = sum(retained_at_61(row, statuses) for row in mature_61)
    outcomes["retention_61"] = {
        "matured": len(mature_61),
        "retained": retained,
        "rate": round(retained / len(mature_61), 4) if mature_61 else None,
    }
    consumed = len(eligible)
    return {
        "status_horizon": status_horizon.isoformat(),
        "consumed": consumed,
        "remaining": max(STOCK_INITIAL - consumed, 0),
        "overage": max(consumed - STOCK_INITIAL, 0),
        "cycle_consumed": cycle_counts,
        "outcomes": outcomes,
    }


def read_recommended_pairs(path: Path) -> tuple[str, set[tuple[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    versions = {row["version"] for row in rows}
    if len(versions) != 1:
        raise ValueError("The demo expects exactly one recommendation version")
    pairs = {(normalize_platform(row["platform"]), normalize_equipment(row["equipment"])) for row in rows}
    return versions.pop(), pairs


def pair_analysis(canonical: list[dict[str, object]], statuses: dict[str, list[tuple[date, str]]], status_horizon: date, recommended: set[tuple[str, str]]) -> list[dict[str, object]]:
    eligible = [row for row in canonical if POLICY_START <= row["delivery_date"] <= status_horizon]
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in eligible:
        grouped[(str(row["platform"]), str(row["equipment"]))].append(row)
    output = []
    for pair, rows in sorted(grouped.items()):
        mature = [row for row in rows if status_horizon >= row["delivery_date"] + timedelta(days=61)]
        activated = sum(activated_within(row, statuses, 61) for row in mature)
        retained = sum(retained_at_61(row, statuses) for row in mature)
        output.append({
            "platform": pair[0],
            "equipment": pair[1],
            "recommended": pair in recommended,
            "deliveries": len(rows),
            "matured_61": len(mature),
            "activated": activated,
            "not_activated": len(mature) - activated,
            "retained": retained,
            "terminal_losses": activated - retained,
            "activation_rate": round(activated / len(mature), 4) if mature else None,
            "retention_rate": round(retained / len(mature), 4) if mature else None,
        })
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run() -> dict[str, object]:
    previous = read_deliveries(ROOT / "data" / "delivery_load_1.csv")
    current = read_deliveries(ROOT / "data" / "delivery_load_2.csv")
    statuses, status_horizon = read_statuses(ROOT / "data" / "status_history.csv")
    version, recommended = read_recommended_pairs(ROOT / "data" / "recommended_pairs.csv")
    delta = compare_loads(previous, current)
    canonical = canonical_rows(current)
    tracking = tracking_summary(canonical, statuses, status_horizon)
    pairs = pair_analysis(canonical, statuses, status_horizon, recommended)
    summary = {
        "recommendation_version": version,
        "previous_rows": len(previous),
        "current_rows": len(current),
        "canonical_sims": len(canonical),
        "delta": delta,
        **tracking,
    }
    output_dir = ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "pair_analysis.csv", pairs)
    write_csv(output_dir / "canonical_deliveries.csv", [
        {
            "iccid": row["iccid"],
            "delivery_date": row["delivery_date"].isoformat(),
            "platform": row["platform"],
            "equipment": row["equipment"],
            "source_row": row["source_row"],
        }
        for row in canonical
    ])
    (output_dir / "tracking_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
