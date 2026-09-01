from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EARLY_DAYS = 30


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    return date.fromisoformat(value) if value else None


def segment(platform: str) -> str:
    normalized = (platform or "").lower()
    if normalized == "financed-device":
        return "FINANCED_DEVICE"
    if normalized in {"portability-retail", "portability-branches"}:
        return "PORTABILITY"
    return "OTHER"


def enrich(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    enriched = []
    for row in rows:
        portout = parse_date(row["portout_date"])
        activation = parse_date(row["activation_date"])
        source = row["activation_source"].strip().upper() or "ESTIMATED"
        corrected = False
        if activation is None or activation >= portout:
            activation = portout - timedelta(days=1)
            corrected = True
        tenure = abs((portout - activation).days)
        recharge_count = int(row["recharge_count"] or 0)
        enriched.append({
            **row,
            "resolved_activation_date": activation.isoformat(),
            "activation_corrected": corrected,
            "tenure_days": tenure,
            "early_abandonment": tenure <= EARLY_DAYS,
            "segment": segment(row["platform"]),
            "recharge_activity": "ACTIVE" if recharge_count > 0 else "INACTIVE",
        })
    return enriched


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    early = [row for row in rows if row["early_abandonment"]]
    mature = [row for row in rows if 30 < row["tenure_days"] <= 365]
    long_term = [row for row in rows if row["tenure_days"] > 365]
    confidence = Counter(str(row["activation_source"]).upper() for row in rows)
    segments = Counter(str(row["segment"]) for row in rows)
    recharge = Counter(str(row["recharge_activity"]) for row in rows)
    organizations = Counter(str(row["organization"]) for row in rows)
    early_org = Counter(str(row["organization"]) for row in early)
    return {
        "total": total,
        "early_abandonment": len(early),
        "early_abandonment_pct": round(len(early) / total * 100, 1) if total else 0,
        "between_31_and_365_days": len(mature),
        "over_365_days": len(long_term),
        "corrected_activation_dates": sum(bool(row["activation_corrected"]) for row in rows),
        "confidence": dict(sorted(confidence.items())),
        "segments": dict(sorted(segments.items())),
        "recharge_activity": dict(sorted(recharge.items())),
        "top_organizations": [
            {"organization": name, "total": count, "early": early_org.get(name, 0)}
            for name, count in organizations.most_common()
        ],
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run() -> dict[str, object]:
    with (ROOT / "data" / "portout_events.csv").open(encoding="utf-8", newline="") as handle:
        source = list(csv.DictReader(handle))
    rows = enrich(source)
    summary = summarize(rows)
    output_dir = ROOT / "outputs"
    enriched_fields = list(source[0].keys()) + ["resolved_activation_date", "activation_corrected", "tenure_days", "early_abandonment", "segment", "recharge_activity"]
    write_csv(output_dir / "enriched_events.csv", rows, enriched_fields)
    write_csv(output_dir / "top_organizations.csv", summary["top_organizations"], ["organization", "total", "early"])
    confidence_rows = [{"source": key, "count": value, "pct": round(value / len(rows) * 100, 1)} for key, value in summary["confidence"].items()]
    write_csv(output_dir / "activation_confidence.csv", confidence_rows, ["source", "count", "pct"])
    json_summary = {key: value for key, value in summary.items() if key != "top_organizations"}
    (output_dir / "kpis.json").write_text(json.dumps(json_summary, indent=2), encoding="utf-8")
    return json_summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

