# FAIGRI-X-EG V36 Render, Reproducibility, and Package QA Report

## Analytical verification

The following commands completed successfully:

- `python scripts/reproduce_full_analysis.py`
- `python scripts/build_uk_atrs_public_benchmark.py`
- `python scripts/build_canada_register_benchmark.py`
- `python scripts/audit_manganello_public_record.py`
- `python scripts/verify_numeric_consistency.py`
- `python scripts/verify_publication_outputs.py`
- `python scripts/verify_external_evidence.py`
- `python scripts/verify_v36_external_benchmarks.py`

The core numeric report passes. The V36 verifier confirms 412 Canadian records, a 33-record education/training subset, 38 source-registry records, lifecycle counts, selected field-completeness values, EDUCAUSE aggregates, Figures 7-8, and the outreach register.

## Manuscript production

- Manuscript: 32 pages.
- Supplement: 8 pages.
- Equations: 17.
- Main-text tables: 14.
- Main-text figures: 8.
- References: 68.
- Undefined citations/references: 0.
- Overfull boxes: 0.
- Type-3 fonts: 0.

All 32 manuscript pages and 8 supplement pages were rendered at 120 dpi and reviewed through contact sheets. No clipping, overlap, black boxes, blank pages, broken glyphs, or orphan figures were identified.

## Workbook

The V36 evidence workbook is a static evidence, traceability, and results register. It contains no calculation formulas. Numerical calculations are executed in Python. The workbook error-string scan returned zero matches, and the Overview sheet was rendered for layout verification.

## Package boundary

The final source manifest and delivery manifest are generated after all artifacts are frozen. The clean source ZIP is independently extracted, the analytical commands are rerun, and both manuscript and supplement are compiled before delivery. Nested ZIP integrity is checked separately.
