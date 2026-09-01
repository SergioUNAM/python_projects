# Spreadsheet Data Transfer, Cleaning & Mapping — Mini-demo

This compact demo mirrors the riskiest parts of the Upwork brief using **12 fictional records only**. It demonstrates a controlled workflow for transferring fields, detecting values entered under the wrong column, extracting only clear facts from free-text Notes, retaining ambiguous content, and producing an auditable QA report.

## What the demo proves

- Misplaced values can be detected and moved without silently overwriting populated destinations.
- Explicit phrases in Notes are mapped only when confidence is at least `0.80`.
- Ambiguous phrases are **not guessed**: they remain in Notes and enter `review_queue.csv`.
- Remaining Notes are compacted as `A / B / C` after mapping.
- Row counts, unique IDs, blank IDs, note formatting, mapped fragments, and review isolation are checked.

## Run

Requires Python 3.10+ and no third-party packages.

```bash
python src/clean_mapping.py
python -m unittest discover -s tests -v
```

Generated evidence is written to `outputs/`:

- `cleaned_leads.csv` — transferred and cleaned records
- `review_queue.csv` — ambiguous or conflicting items requiring human review
- `qa_report.csv` — reconciliation and quality-control checks
- `demo_evidence.xlsx` — reviewer-friendly workbook snapshot of the same evidence

## Important scope boundary

This is not presented as a fully automatic solution for the client's 800 records. The real workbook must be reviewed against the client's completed example. Automation is limited to deterministic cleanup, explicit pattern suggestions, reconciliation, and QA; a human remains responsible for ambiguous mapping decisions and the final row-by-row review.

## Production approach for the client workbook

1. Inspect the completed example and create a field-mapping checklist.
2. Transfer straightforward rows in controlled batches.
3. Review all Notes-bearing rows individually; map only defensible facts.
4. Put uncertain/conflicting items into a review queue rather than guessing.
5. Reconcile record counts and IDs; spot-check every batch and perform a final pass.

All names, emails, phone numbers, companies, and notes in this repository are synthetic and use the reserved `.test` domain.

