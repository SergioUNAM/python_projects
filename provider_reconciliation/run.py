from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXCLUDED_STATES = {"ELIMINATED", "IN_DISPUTE"}
DATE_RE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$")


def parse_date(token: str) -> datetime | None:
    match = DATE_RE.match(token.strip())
    if not match:
        return None
    day, month, year, hour, minute, second = match.groups()
    year_number = int(year) + (2000 if int(year) < 100 else 0)
    try:
        return datetime(year_number, int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0))
    except ValueError:
        return None


def parse_amount(token: str) -> float | None:
    value = token.strip().replace("$", "").replace("€", "").replace(" ", "")
    if not value:
        return None
    if "," in value and "." not in value:
        value = value.replace(",", ".")
    elif "," in value and value.rfind(",") > value.rfind("."):
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", "")
    try:
        return round(float(value), 2)
    except ValueError:
        return None


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def parse_provider_text(text: str) -> dict[tuple[str, float], list[datetime | None]]:
    text = text.replace("\\t", "\t")
    result: dict[tuple[str, float], list[datetime | None]] = defaultdict(list)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in re.split(r"\t| {2,}", line) if part.strip()]
        timestamp = None
        phone = None
        amount_candidates: list[str] = []
        for part in parts:
            if part in {"$", "€"}:
                continue
            if timestamp is None and (parsed := parse_date(part)) is not None:
                timestamp = parsed
                continue
            digits = normalize_phone(part)
            if phone is None and len(digits) >= 8 and "." not in part and "," not in part:
                phone = digits
                continue
            amount_candidates.append(part)
        if phone is None or not amount_candidates:
            continue
        amount = parse_amount(amount_candidates[-1])
        if amount is None:
            continue
        result[(phone, amount)].append(timestamp)
    return dict(result)


def reconcile(internal_rows: list[dict[str, str]], provider_text: str) -> dict[str, object]:
    provider = parse_provider_text(provider_text)
    internal: dict[tuple[str, float], list[dict[str, str]]] = defaultdict(list)
    for row in internal_rows:
        if row["state"].strip().upper() in EXCLUDED_STATES:
            continue
        phone = normalize_phone(row["msisdn"])
        amount = parse_amount(row["amount"])
        if phone and amount is not None:
            internal[(phone, amount)].append(row)

    discrepancies = []
    missing = []
    for key in sorted(set(internal) | set(provider)):
        phone, amount = key
        internal_group = internal.get(key, [])
        provider_group = provider.get(key, [])
        if len(internal_group) > len(provider_group):
            existing = sorted({row["duplicate_group"] for row in internal_group if row["duplicate_group"]})
            discrepancies.append({
                "msisdn": phone,
                "amount": amount,
                "internal_count": len(internal_group),
                "provider_count": len(provider_group),
                "excess": len(internal_group) - len(provider_group),
                "tx_ids": ";".join(row["tx_id"] for row in internal_group),
                "action": "ADD_TO_EXISTING" if existing else "CREATE_REVIEW_GROUP",
                "existing_group": existing[0] if existing else "",
            })
        elif len(provider_group) > len(internal_group):
            missing_count = len(provider_group) - len(internal_group)
            timestamps = [stamp.isoformat() if stamp else "" for stamp in provider_group]
            missing.append({
                "msisdn": phone,
                "amount": amount,
                "internal_count": len(internal_group),
                "provider_count": len(provider_group),
                "deficit": missing_count,
                "provider_timestamps": ";".join(timestamps),
            })

    return {
        "provider_keys": len(provider),
        "internal_keys": len(internal),
        "discrepancy_keys": len(discrepancies),
        "missing_keys": len(missing),
        "missing_transactions": sum(row["deficit"] for row in missing),
        "missing_amount": round(sum(row["amount"] * row["deficit"] for row in missing), 2),
        "discrepancies": discrepancies,
        "missing": missing,
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run() -> dict[str, object]:
    with (ROOT / "data" / "internal_transactions.csv").open(encoding="utf-8", newline="") as handle:
        internal = list(csv.DictReader(handle))
    provider_text = (ROOT / "data" / "provider_report.tsv").read_text(encoding="utf-8")
    result = reconcile(internal, provider_text)
    output_dir = ROOT / "outputs"
    write_csv(output_dir / "discrepancies.csv", result["discrepancies"], ["msisdn", "amount", "internal_count", "provider_count", "excess", "tx_ids", "action", "existing_group"])
    write_csv(output_dir / "missing_transactions.csv", result["missing"], ["msisdn", "amount", "internal_count", "provider_count", "deficit", "provider_timestamps"])
    summary = {key: value for key, value in result.items() if key not in {"discrepancies", "missing"}}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

