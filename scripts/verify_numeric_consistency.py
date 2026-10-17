#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
case = pd.read_csv(DATA / 'case_results_with_topsis.csv')
mandatory = pd.read_csv(DATA / 'mandatory_safeguard_matrix.csv')
source = pd.read_csv(DATA / 'source_registry.csv')
long = pd.read_csv(DATA / 'criterion_score_matrix_long.csv')
functional = pd.read_csv(DATA / 'functional_form_sensitivity.csv')
breaks = pd.read_csv(DATA / 'upper_band_breakpoint_analysis.csv')
risk_sens = pd.read_csv(DATA / 'risk_posture_sensitivity.csv')
threshold = pd.read_csv(DATA / 'threshold_sensitivity.csv')
assertions = json.loads((DATA / 'calculation_assertions.json').read_text(encoding='utf-8'))
checks = {}

# Core equations.
g_expected = case[['P', 'F', 'T', 'H', 'L']].astype(float).mean(axis=1)
s_expected = g_expected * np.exp(-0.75 * case['R'].astype(float))
g_error = float(np.max(np.abs(g_expected - case['G_equal'])))
s_error = float(np.max(np.abs(s_expected - case['S_lambda_0.75'])))
checks['governance_readiness'] = {'max_abs_error': g_error, 'passed': g_error < 1e-12}
checks['risk_adjustment'] = {'max_abs_error': s_error, 'passed': s_error < 1e-12}

# Veto product and record-origin fields.
applicable = mandatory[mandatory.get('Applicability_Status', pd.Series('Applicable', index=mandatory.index)).eq('Applicable')].copy()
applicable['m_ij'] = pd.to_numeric(applicable['m_ij']).astype(int)
veto = applicable.groupby('Case_ID')['m_ij'].prod().astype(int)
reported = case.set_index('Case_ID')['Veto_Pass'].map({'Yes': 1, 'No': 0}).astype(int)
origin_fields = ['Record_Origin', 'Original_or_Reconstructed', 'Reconstruction_Basis', 'Evidence_Admission_Standard', 'Missingness_Category', 'Missingness_Code', 'Evidence_Note', 'Evidence_Location', 'Applicability_Status']
origin_complete = all(field in mandatory.columns and mandatory[field].notna().all() for field in origin_fields)
checks['veto_matrix'] = {
    'rows': int(len(mandatory)),
    'mismatch_count': int((veto != reported).sum()),
    'record_origin_fields_complete': bool(origin_complete),
    'passed': bool((veto == reported).all() and len(mandatory) == 50 and origin_complete),
}

# Scope and result counts.
public = case[case['Case_Type'] == 'Public-evidence case']
protocol = case[case['Case_Type'] != 'Public-evidence case']
checks['scope'] = {
    'public_cases': int(len(public)),
    'protocol_cases': int(len(protocol)),
    'source_records': int(len(source)),
    'criterion_rows': int(len(long)),
    'passed': bool(len(public) == 11 and len(protocol) == 1 and len(source) == 38 and len(long) == 72),
}
checks['public_counts'] = {
    'baseline': public['Zone_no_risk'].value_counts().to_dict(),
    'risk_adjusted': public['Risk_Zone_0.75'].value_counts().to_dict(),
    'mandatory_evidence_documented': int((public['Evidence_Status'] == 'Mandatory evidence documented').sum()),
    'veto_hold': int((public['Veto_Pass'] == 'No').sum()),
    'passed': bool(
        (public['Zone_no_risk'] == 'Upper').sum() == 5
        and (public['Risk_Zone_0.75'] == 'Upper').sum() == 0
        and (public['Evidence_Status'] == 'Mandatory evidence documented').sum() == 2
        and (public['Veto_Pass'] == 'No').sum() == 9
    ),
}

# TOPSIS exact recomputation with six equal weights.
cols = ['P', 'F', 'T', 'H', 'L', 'R']
X = public[cols].astype(float).to_numpy()
norms = np.sqrt((X ** 2).sum(axis=0))
V = X / norms * (1 / 6)
positive = np.concatenate([V[:, :5].max(axis=0), [V[:, 5].min()]])
negative = np.concatenate([V[:, :5].min(axis=0), [V[:, 5].max()]])
dplus = np.sqrt(((V - positive) ** 2).sum(axis=1))
dminus = np.sqrt(((V - negative) ** 2).sum(axis=1))
cc = dminus / (dplus + dminus)
cc_error = float(np.max(np.abs(cc - public['TOPSIS_CC'].to_numpy())))
c01 = public.loc[public.Case_ID == 'C01'].iloc[0]
c02 = public.loc[public.Case_ID == 'C02'].iloc[0]
checks['topsis'] = {
    'dimensions': 6,
    'weight_each': 1 / 6,
    'weight_sum': 1.0,
    'max_abs_error': cc_error,
    'protocol_included_count': int(protocol['TOPSIS_included'].eq('Yes').sum()),
    'shared_tie': bool(c01.TOPSIS_rank == c02.TOPSIS_rank == 2),
    'passed': bool(cc_error < 1e-12 and protocol['TOPSIS_CC'].isna().all() and c01.TOPSIS_rank == c02.TOPSIS_rank == 2),
}

# Robustness checks.
upper = functional[(functional.Case_Type == 'Public-evidence case') & (functional.Band == 'Upper')].groupby('Functional_Form').size().to_dict()
checks['functional_form'] = {
    'public_upper_counts': upper,
    'tested_forms': sorted(functional.Functional_Form.unique().tolist()),
    'passed': bool(len(upper) == 0 and functional.Functional_Form.nunique() == 3),
}
critical = float(breaks['Critical_Lambda_Leaving_Upper'].max())
checks['upper_breakpoint'] = {
    'max_critical_lambda': critical,
    'expected': 0.15820250361750854,
    'passed': abs(critical - 0.15820250361750854) < 1e-12,
}
row016 = risk_sens[(risk_sens.Case_Set == 'Public-evidence case') & (np.isclose(risk_sens.Lambda, 0.16))].iloc[0]
checks['transition_range'] = {'lambda_0_16_upper': int(row016.Upper), 'passed': int(row016.Upper) == 0}
checks['threshold_grid'] = {
    'rows': int(len(threshold)),
    'veto_hold_constant': sorted(threshold['Public_Total_Veto_Hold'].unique().tolist()),
    'passed': bool(len(threshold) == 4 and set(threshold['Public_Total_Veto_Hold']) == {9}),
}
checks['assertions'] = {
    'score_bounds_pass': bool(assertions['score_bounds_pass']),
    'safeguards_binary_pass': bool(assertions['safeguards_binary_pass']),
    'c12_excluded': bool(assertions['c12_excluded_from_public_topsis']),
    'rounded_values_used_as_inputs': bool(assertions['rounded_values_used_as_inputs']),
    'passed': bool(
        assertions['score_bounds_pass']
        and assertions['safeguards_binary_pass']
        and assertions['c12_excluded_from_public_topsis']
        and not assertions['rounded_values_used_as_inputs']
        and assertions.get('chained_near_tie_test', False)
        and assertions.get('not_applicable_rows_excluded_from_veto_product', False)
    ),
}
checks['overall_passed'] = all(
    value.get('passed', False)
    for value in checks.values()
    if isinstance(value, dict) and 'passed' in value
)
out = DATA / 'numeric_consistency_report.json'
out.write_text(json.dumps(checks, indent=2), encoding='utf-8')
print(json.dumps({'overall_passed': checks['overall_passed'], 'report': str(out)}, indent=2))
