# FAIGRI-X-EG: Project 60 — V37 research code and evidence extracts

**Public Project 60 V37 reproducibility repository — distinct from ITT-2026 Paper 3.**

**Repository maintainer and GitHub citation author: Ghassan Malkawi.** This repository attribution does not change the separate journal manuscript author list.

This is a separately scoped reproducibility subset for the journal manuscript
*When Is Documentary Evidence Sufficient for Higher-Risk Educational AI? A Veto-Gated Screening Protocol*.
It concerns **11 public documentary dossiers plus one synthetic protocol stress case**.
The final numerical baseline is V37. The journal paper is not yet accepted and this code
cannot establish safety, compliance, effectiveness, or institutional procurement outcomes.

## Reproduce from disclosed adjudicated inputs

Python 3.10+ with NumPy, pandas and Matplotlib:

```bash
python -m pip install -r requirements.txt
python scripts/reproduce_full_analysis.py
python scripts/verify_numeric_consistency.py
python editorial_diagnostics/recompute_gate_nonredundancy.py data/public_case_results.csv editorial_diagnostics
python editorial_diagnostics/build_documentary_request_queue.py data/mandatory_safeguard_matrix.csv data/public_case_results.csv editorial_diagnostics
```

Run in a disposable checkout: reproduction scripts may rewrite derived CSVs/figures.
`python scripts/build_uk_atrs_public_benchmark.py` and
`python scripts/build_canada_register_benchmark.py` regenerate the bounded
external benchmark from the source's admitted processed inputs.
The complete reproducibility contract is in `REPRODUCIBILITY_BOUNDARIES.md`.

## Frozen scientific boundaries

- 11 public dossiers at `lambda=0.75`: 0 Upper / 5 Review / 6 Lower;
  mandatory documented 2 / Veto Hold 9.
- The protocol stress case C12 is synthetic and never pooled into public TOPSIS.
- The separate UK ATRS eight-record and Canada 412-record layers are structured
  documentary comparisons, **not independent product or procurement validation**.
- Missing public evidence is **not proof that a safeguard is absent**.
- Scores, case decisions, weight conventions and source-to-score limits are unchanged.

## Contents

- `scripts/`: original V37 reproducibility, audits and external-benchmark builders.
- `data/`: frozen adjudicated inputs, source registries, scored outputs, sensitivity files.
- `editorial_diagnostics/`: deterministic editor-facing derived tables.
- `external_evidence/`: published source-to-construct extracts and admitted
  public-register transport copy, with original-source attribution.
- `extension_r6/`: public proposition trace and diagnostics; exact raw-source
  binary replay needs private original snapshots and is **not available publicly**.
- `figures/`: original published figures and plot assets.
- `audit/`: reproducibility and source-admission audit records.

## Licence and third-party rights

This public reproducibility release is not a blanket relicensing of all contents.
The original scripts, analysis records and figures are released for inspection
and noncommercial scholarly replication under `PUBLIC_REVIEW_PERMISSION.md`.
Government of Canada material and the Manganello CC BY source have their own
source terms; see `THIRD_PARTY_NOTICE.md` and `REPRODUCIBILITY_BOUNDARIES.md`.
Original institutional/vendor source PDFs/HTML, confidential correspondence,
private source archives, and personal author/title-page information are NOT included.

## Review anonymity

The code should be shown to double-anonymized journal reviewers via
an identity-stripped read-only mirror, **not a personal-account GitHub URL**.
Do not insert a public repository URL that exposes the author username into
an anonymous reviewer manuscript. `ANONYMOUS_REVIEW_LINK_WORKFLOW.md` explains
how to create and verify an anonymous mirror.

## Publication and status

This public repository does not claim a Zenodo DOI, external validation,
independent source-to-score recoding, third-party permission beyond stated licences,
or approval by the journal. This repository is publicly accessible at https://github.com/shaikhamalkawi-ux/faigri-x-eg-project60-v37 .
