# Reproducibility data guide

The computational entry point is `scripts/reproduce_full_analysis.py`.

## Reproducibility start

The analysis begins from `case_input_matrix.csv` and `mandatory_safeguard_matrix.csv`. The original coder-level source annotations were unavailable and are not reconstructed. The mandatory-safeguard records are explicitly marked as derived analytical records.

## Core inputs

- `case_input_matrix.csv`: 12 case-level profiles, including 11 public dossiers and C12.
- `criterion_score_matrix_long.csv`: 72 disclosed criterion/risk rows.
- `mandatory_safeguard_matrix.csv`: 50 binary entries with record-origin, reconstruction, admission, missingness, and applicability fields.
- `source_registry.csv`: 20 case or framework/context evidence records.

## Scope and provenance controls

- `case_selection_protocol.csv`
- `source_registry_role_map.csv`
- `source_preservation_status.csv`
- `evidence_missingness_taxonomy.csv`
- `score_risk_veto_overlap_control.csv`
- `special_case_mapping_and_stress_test_design.csv`
- `software_environment.json`
- `calculation_assertions.json`

## Outputs

- `case_results_with_topsis.csv`
- `public_case_results.csv`
- `protocol_stress_test_result.csv`
- `topsis_tie_audit.csv`
- `upper_band_breakpoint_analysis.csv`
- `risk_posture_sensitivity.csv`
- `threshold_sensitivity.csv`
- `functional_form_sensitivity.csv`
- `numeric_consistency_report.json`

Display rounding is applied only after calculation. Rounded values are not reused as computational inputs.
