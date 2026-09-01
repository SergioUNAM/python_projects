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

