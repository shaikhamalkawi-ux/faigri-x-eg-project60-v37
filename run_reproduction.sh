#!/usr/bin/env bash
set -euo pipefail
python scripts/reproduce_full_analysis.py
python scripts/verify_numeric_consistency.py
python editorial_diagnostics/recompute_gate_nonredundancy.py data/public_case_results.csv editorial_diagnostics
python editorial_diagnostics/build_documentary_request_queue.py data/mandatory_safeguard_matrix.csv data/public_case_results.csv editorial_diagnostics
python scripts/build_uk_atrs_public_benchmark.py
python scripts/build_canada_register_benchmark.py
printf '
PROJECT60_V37_PUBLIC_REPRO: PASS (from adjudicated inputs)
'
