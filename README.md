# Inventory operations — three reproducible demos

These demos turn three real telecommunications inventory processes into small, auditable examples using **fictional data only**. They preserve the operational rules and failure modes while removing company names, customer data, credentials, internal database details, and production configuration.

## Included processes

1. **Range audit** — validates a bounded SIM sequence, detects contiguous gaps, and reconciles counts by inventory status and offer.
2. **Provider reconciliation** — compares internal transactions with a pasted provider report in both directions, isolating internal duplicates and missing transactions.
3. **Port-out retention** — calculates tenure before port-out, classifies early abandonment at `<= 30` days, exposes activation-date confidence, and separates active vs. inactive recharge behavior.

## Run everything

Python 3.10+ is required. There are no third-party dependencies.

```bash
python run_all.py
python -m unittest discover -s range_audit/tests -v
python -m unittest discover -s provider_reconciliation/tests -v
python -m unittest discover -s portout_retention/tests -v
```

Each demo writes reviewable CSV/JSON evidence into its own `outputs/` directory.

## Portfolio boundary

These are focused process demonstrations, not a copy of the private application. They do not include production source code, real identifiers, proprietary catalogs, database schemas, business names, or confidential metrics.

