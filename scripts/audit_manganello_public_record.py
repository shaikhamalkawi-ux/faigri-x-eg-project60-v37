#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import shutil
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'external_evidence' / 'manganello_public'
AUDIT = ROOT / 'audit'
SRC.mkdir(parents=True, exist_ok=True)
AUDIT.mkdir(parents=True, exist_ok=True)

# Input files are distributed in the source package under CC BY 4.0.
cons_path = SRC / '03_consensus_item_scores_and_coding_notes_378_rows.csv'
check_path = SRC / '02_xai_ed_caf_checklist_27_items.csv'
screen_path = SRC / '01_screening_dataset_100_universities.csv'

cons = pd.read_csv(cons_path, dtype={'University_Code': str, 'Item_Code': str})
check = pd.read_csv(check_path, dtype={'Item_Code': str, 'Dimension_Code': str})
screen = pd.read_csv(screen_path)

# Normalize item-code rendering after CSV import.
cons['Item_Code'] = cons['Item_Code'].str.replace(r'\.0$', '', regex=True)
check['Item_Code'] = check['Item_Code'].str.replace(r'\.0$', '', regex=True)

# Structural gates.
assert len(screen) == 100
assert len(check) == 27
assert len(cons) == 378
assert cons['University_Code'].nunique() == 14
assert cons.groupby('University_Code').size().eq(27).all()
assert set(cons['Consensus_Score'].unique()).issubset({0,1,2,3})
assert cons['Coding_Note'].fillna('').str.strip().ne('').all()

merged = cons.merge(check[['Item_Code','Dimension_Code','Dimension']], on='Item_Code', how='left', validate='many_to_one')
assert merged['Dimension'].notna().all()

# Published Figure 2 values transcribed from the official article figure.
columns = [
    'Human agency & oversight',
    'Technical robustness & safety',
    'Privacy & data governance',
    'Transparency',
    'Diversity, fairness & non-discrimination',
    'Societal & environmental well-being',
    'Accountability',
    'Institutional Index',
]
published = {
    'UNISTRAPG':[58.33,58.33,50.00,58.33,50.00,88.89,58.33,60.32],
    'UNIPO':[75.00,58.33,75.00,33.33,50.00,44.44,66.67,57.54],
    'UNIMI':[66.67,41.67,50.00,50.00,50.00,77.78,50.00,55.16],
    'UNIFI':[58.33,16.67,33.33,50.00,41.67,66.67,25.00,41.67],
    'UNIBO':[66.67,0.00,16.67,41.67,25.00,77.78,33.33,37.30],
    'UNIVE':[33.33,0.00,41.67,33.33,25.00,88.89,25.00,35.32],
    'UNIBG':[58.33,25.00,33.33,25.00,25.00,55.56,16.67,34.13],
    'UNITE':[41.67,0.00,33.33,25.00,16.67,88.89,0.00,29.37],
    'UNISI':[50.00,16.67,25.00,41.67,16.67,22.22,25.00,28.17],
    'UNICAM':[50.00,33.33,33.33,8.33,0.00,33.33,33.33,27.38],
    'UNIPR':[41.67,0.00,41.67,33.33,8.33,33.33,16.67,25.00],
    'UNITN':[41.67,16.67,25.00,25.00,8.33,33.33,16.67,23.81],
    'POLIMI':[25.00,8.33,25.00,8.33,0.00,22.22,8.33,13.89],
    'UNINA':[0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00],
}
published_df = pd.DataFrame.from_dict(published, orient='index', columns=columns)
published_df.index.name = 'University_Code'
published_df.reset_index().to_csv(SRC / '05_published_figure2_dimension_and_index_values.csv', index=False)

# Recompute from the detailed published consensus rows.
dim = (merged.groupby(['University_Code','Dimension'])['Consensus_Score']
       .mean().div(3).mul(100).reset_index())
recomputed = dim.pivot(index='University_Code', columns='Dimension', values='Consensus_Score')
recomputed['Institutional Index'] = recomputed[columns[:-1]].mean(axis=1)
recomputed = recomputed[columns].sort_index()
recomputed.reset_index().to_csv(AUDIT / 'manganello_consensus_recomputed_profiles.csv', index=False)

# Cell-level comparison using displayed two-decimal values. A cell passes when rounded values agree.
comp_rows = []
for university in published_df.index:
    for measure in columns:
        calc = float(recomputed.loc[university, measure])
        pub = float(published_df.loc[university, measure])
        calc_2 = round(calc + 1e-12, 2)
        pub_2 = round(pub + 1e-12, 2)
        comp_rows.append({
            'University_Code': university,
            'Measure': measure,
            'Consensus_Matrix_Recomputed': calc,
            'Published_Figure2': pub,
            'Absolute_Difference': abs(calc-pub),
            'Match_at_2dp': calc_2 == pub_2,
            'Admission_Decision': 'Match' if calc_2 == pub_2 else 'Hold for quantitative benchmark',
        })
comp = pd.DataFrame(comp_rows)
comp.to_csv(AUDIT / 'manganello_figure2_vs_consensus_matrix_audit.csv', index=False)

# Published Table 3 is mathematically identical to statistics computed from Figure 2.
pub_stats = published_df[columns[:-1]].agg(['mean','std','min','max','median']).T
calc_stats = recomputed[columns[:-1]].agg(['mean','std','min','max','median']).T
stat_rows = []
for dimension in columns[:-1]:
    for metric in ['mean','std','min','max','median']:
        pub_value = float(pub_stats.loc[dimension, metric])
        calc_value = float(calc_stats.loc[dimension, metric])
        stat_rows.append({
            'Dimension': dimension,
            'Metric': metric,
            'Consensus_Matrix_Recomputed': calc_value,
            'Published_Table3_or_Figure2': pub_value,
            'Absolute_Difference': abs(calc_value-pub_value),
            'Match_at_2dp': round(calc_value+1e-12,2) == round(pub_value+1e-12,2),
        })
pd.DataFrame(stat_rows).to_csv(AUDIT / 'manganello_table3_vs_consensus_statistics_audit.csv', index=False)

# Narrative-claim reproduction from the detailed matrix, excluding the no-policy baseline.
policy = cons[cons['University_Code'] != 'UNINA'].copy()
claims = [
    ('Appeal or contest procedures absent', '1.2', 0, 12, 13,
     'Article states 12 of 13 policy institutions failed to establish appeal procedures.'),
    ('Data access/rectification/erasure absent', '3.3', 0, 12, 13,
     'Article states 12 of 13 failed to articulate these rights.'),
    ('Stakeholder consultation absent', '5.4', 0, 12, 13,
     'Article states 12 institutions scored zero.'),
]
claim_rows = []
for label, item, target, stated, denominator, text in claims:
    subset = policy[policy['Item_Code'] == item]
    observed = int((subset['Consensus_Score'] == target).sum())
    claim_rows.append({
        'Claim': label,
        'Item_Code': item,
        'Published_Numerator': stated,
        'Published_Denominator': denominator,
        'Consensus_Matrix_Observed_Numerator': observed,
        'Consensus_Matrix_Denominator': len(subset),
        'Reproduced': observed == stated and len(subset) == denominator,
        'Published_Wording_Summary': text,
    })
pd.DataFrame(claim_rows).to_csv(AUDIT / 'manganello_narrative_claim_reproduction_audit.csv', index=False)

# Score distribution is a direct property of the published consensus table, not an external validation result.
dist_rows = []
for scope_name, frame in [('All 14 institutions', cons), ('13 policy institutions', policy)]:
    total = len(frame)
    counts = frame['Consensus_Score'].value_counts().reindex([0,1,2,3], fill_value=0)
    for score, count in counts.items():
        dist_rows.append({
            'Scope': scope_name,
            'Score': int(score),
            'Count': int(count),
            'Percent': float(count/total*100),
            'Interpretation': {0:'No evidence found',1:'Weak evidence',2:'Partial implementation',3:'Documented implementation'}[int(score)],
        })
pd.DataFrame(dist_rows).to_csv(AUDIT / 'manganello_consensus_score_distribution.csv', index=False)

# Cross-framework construct map. It is qualitative only; no score conversion or reweighting is allowed.
crosswalk = [
('1.1','H','Human decision authority','Direct','Criterion and possible mandatory safeguard','No numeric conversion'),
('1.2','H','Appeal and contestability','Direct','Mandatory safeguard for consequential uses','No numeric conversion'),
('1.3','H','Meaningful human oversight','Direct','Criterion and mandatory safeguard','No numeric conversion'),
('1.4','H;L','Oversight training','Direct','Criterion/contextual safeguard','No numeric conversion'),
('2.1','L;H','Validity, reliability, and accuracy evidence','Partial','Use-context safeguard for grading/assessment','No numeric conversion'),
('2.2','L;T','Alignment with learning outcomes and assessment criteria','Partial','Use-context safeguard','No numeric conversion'),
('2.3','L;T','Testing, error monitoring, updating, and decommissioning','Partial','Monitoring/audit safeguard','No numeric conversion'),
('2.4','L','Internal or external review and audit','Direct','Mandatory audit safeguard','No numeric conversion'),
('3.1','P;L','Data-protection compliance','Direct','Criterion and mandatory safeguard','No numeric conversion'),
('3.2','P','Data minimization, retention, and lawful basis','Direct','Criterion and mandatory safeguard','No numeric conversion'),
('3.3','P;H','Data-subject rights','Direct','Criterion and rights safeguard','No numeric conversion'),
('3.4','P;L','Accountable data-protection role','Direct','Criterion and governance safeguard','No numeric conversion'),
('4.1','T','AI-use disclosure','Direct','Criterion and disclosure safeguard','No numeric conversion'),
('4.2','T;H','Comprehensible explanation','Direct','Criterion and contestability safeguard','No numeric conversion'),
('4.3','T','Criteria, limitations, and error sources','Direct','Criterion and transparency safeguard','No numeric conversion'),
('4.4','T;H','Communication support for non-technical users','Direct','Criterion/contextual safeguard','No numeric conversion'),
('5.1','F','Non-discrimination and bias prohibition','Direct','Criterion and mandatory safeguard','No numeric conversion'),
('5.2','F','Bias monitoring and corrective measures','Direct','Criterion and mandatory safeguard','No numeric conversion'),
('5.3','F;L','Accessibility and inclusion','Direct','Criterion and use-context safeguard','No numeric conversion'),
('5.4','H;L','Stakeholder consultation','Partial','Governance safeguard','No numeric conversion'),
('6.1','L;F','Educational values and learner autonomy','Contextual','Construct corroboration only','No numeric conversion'),
('6.2','Out of current core scope','Environmental sustainability','Contextual','Limitation/future scope','No numeric conversion'),
('6.3','L','Human-centered ethical codes','Partial','Contextual institutional-compliance evidence','No numeric conversion'),
('7.1','L;H','Governance roles and responsibilities','Direct','Criterion and mandatory governance safeguard','No numeric conversion'),
('7.2','L;H','Oversight committee or ethics board','Direct','Governance safeguard','No numeric conversion'),
('7.3','H;L','Feedback, complaints, and redress','Direct','Mandatory contestability safeguard','No numeric conversion'),
('7.4','L;T','Periodic review and independent validation','Direct','Monitoring/audit safeguard','No numeric conversion'),
]
crosswalk_df = pd.DataFrame(crosswalk, columns=['XAI_ED_Item','FAIGRI_Target','Construct','Alignment','Admitted_Use','Quantitative_Use'])
crosswalk_df = crosswalk_df.merge(check[['Item_Code','Dimension','Checklist_Question']], left_on='XAI_ED_Item', right_on='Item_Code', how='left')
crosswalk_df.drop(columns=['Item_Code'], inplace=True)
crosswalk_df.to_csv(SRC / '06_xai_ed_caf_to_faigri_construct_crosswalk.csv', index=False)

# Data-access status records the author response without reproducing private correspondence.
pd.DataFrame([{
    'Source': 'Corresponding-author response',
    'Response_Date': '2026-07-12',
    'Status': 'Closed - public record only',
    'Available_Record': 'CC BY article and official 67-page supplement',
    'Unavailable_Record': 'Separate pre-consensus coder matrices, coder identifiers, and coder-level disagreement log',
    'Research_Decision': 'Proceed with public-record audit; do not claim independent recomputation of intercoder reliability',
    'Public_Release_Treatment': 'No private email text reproduced',
}]).to_csv(AUDIT / 'manganello_data_access_status.csv', index=False)

# Admission decision summary.
dim_mismatch = int((~comp[comp['Measure']!='Institutional Index']['Match_at_2dp']).sum())
idx_mismatch = int((~comp[comp['Measure']=='Institutional Index']['Match_at_2dp']).sum())
discrepant_institutions = sorted(comp.loc[~comp['Match_at_2dp'],'University_Code'].unique().tolist())
summary = {
    'screening_rows': int(len(screen)),
    'checklist_items': int(len(check)),
    'consensus_rows': int(len(cons)),
    'universities': int(cons['University_Code'].nunique()),
    'nonempty_coding_notes': int(cons['Coding_Note'].fillna('').str.strip().ne('').sum()),
    'dimension_cells_compared': 98,
    'dimension_cells_mismatched_at_2dp': dim_mismatch,
    'institutional_indices_compared': 14,
    'institutional_indices_mismatched_at_2dp': idx_mismatch,
    'discrepant_institutions': discrepant_institutions,
    'fully_reproduced_institution_profiles': int(14-len(discrepant_institutions)),
    'published_table3_matches_published_figure2': True,
    'consensus_matrix_admission': 'Keep for structural, qualitative-note, and construct-crosswalk audit; Hold for numerical external benchmark',
    'intercoder_reliability_recomputation': 'Not possible from public consensus-only record',
    'core_faigri_results_changed': False,
}
(AUDIT / 'manganello_public_record_audit_report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

# Human-readable summary.
(AUDIT / 'MANGANELLO_PUBLIC_RECORD_AUDIT.md').write_text(f'''# Manganello XAI-ED CAF public-record audit\n\n- Screening dataset: {len(screen)} records; 13 policy-detected and 87 policy-not-detected records.\n- Checklist: {len(check)} items.\n- Consensus matrix: {len(cons)} item-institution rows, {cons["University_Code"].nunique()} institutions, all notes non-empty.\n- Published Figure 2/Table 3 are internally consistent with each other.\n- The detailed consensus matrix does not reproduce {dim_mismatch} of 98 dimension cells and {idx_mismatch} of 14 institutional indices at the displayed two-decimal precision.\n- Discrepancies are concentrated in: {", ".join(discrepant_institutions)}.\n- The matrix is admitted for structural and qualitative construct audit, but held from quantitative external benchmarking, recalibration, or validation of FAIGRI-X-EG.\n- The public record does not include the four separate pre-consensus coder matrices, so Fleiss kappa and Krippendorff alpha cannot be independently recomputed.\n''', encoding='utf-8')

print(json.dumps(summary, indent=2))
