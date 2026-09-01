# Process map

## 1. Bounded sequence audit

**Operational question:** Are all expected serialized inventory items present between two known endpoints?

**Controls demonstrated:**

- resolve the consecutive number represented by each endpoint;
- calculate expected vs. observed inventory;
- group adjacent missing numbers into actionable ranges;
- reconcile counts by status and offer;
- flag duplicate consecutive values separately from missing values.

## 2. Bidirectional provider reconciliation

**Operational question:** Does the provider report contain the same number of transactions as the internal ledger for each normalized `(phone, amount)` key?

**Controls demonstrated:**

- tolerate pasted tabular text with reordered date, phone, currency, and amount columns;
- normalize punctuation in phone identifiers and localized monetary formats;
- exclude transactions already eliminated or in dispute;
- report `internal > provider` as duplicate/discrepancy candidates;
- report `provider > internal` as missing internal transactions;
- preserve provider timestamps for later controlled materialization.

## 3. Port-out tenure and confidence

**Operational question:** How long did each line remain active before leaving, and how reliable is the activation date used?

**Controls demonstrated:**

- use calendar-day differences rather than raw timestamp duration;
- correct impossible activation dates on/after port-out to a conservative one-day fallback;
- classify early abandonment at `<= 30` days regardless of activation source;
- expose confidence by measured, inferred, and estimated activation dates;
- segment the population by origin channel and recharge activity.

## 4. SIM recommendation tracking

**Operational question:** Is the closed SIM lot being consumed through the recommended platform/equipment pairs, and what outcomes are observable once each delivery cohort matures?

**Controls demonstrated:**

- treat each upload as a complete cumulative snapshot and calculate added, removed, and unchanged rows with multiset semantics;
- normalize platform/equipment labels before fingerprinting while preserving repeated identical rows;
- flag one SIM/date key as ambiguous when it maps to more than one normalized pair;
- select one deterministic canonical delivery per SIM (earliest date, then source-row order);
- count only canonical deliveries inside the policy window against the scaled closed lot and cycle totals;
- report activation at 7, 14, 30, and 61 days only for cohorts mature against the actual status horizon;
- report 61-day retention from the latest observed status on or before day 61;
- expose pair-level deliveries, mature cohorts, activation, retention, and membership in a versioned recommendation list.

The demo uses a scaled fictional lot of 20 SIMs instead of the production-sized lot so every calculation is easy to verify by hand.
