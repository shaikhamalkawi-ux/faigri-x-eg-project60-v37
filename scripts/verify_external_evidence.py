#!/usr/bin/env python3
from pathlib import Path
import csv, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]

def rows(p):
    with open(p, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

# Regenerate the official public-record audits first.
subprocess.run([sys.executable, str(ROOT/'scripts'/'audit_manganello_public_record.py')], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(ROOT/'scripts'/'build_uk_atrs_public_benchmark.py')], cwd=ROOT, check=True)
report=json.loads((ROOT/'audit'/'manganello_public_record_audit_report.json').read_text(encoding='utf-8'))
atrs=json.loads((ROOT/'audit'/'uk_atrs_public_benchmark_report.json').read_text(encoding='utf-8'))

s=rows(ROOT/'external_evidence'/'manganello_public'/'01_screening_dataset_100_universities.csv')
policy_col='public_ai_policy_detected_in_source_snapshot'
if policy_col not in s[0]:
    # Official derived screening CSV distributed by the project uses this field.
    policy_col='public_ai_policy_detected_in_source_snapshot'
yes=sum(r.get(policy_col)=='Yes' for r in s)

out={
 'screening_n':len(s),
 'policy_detected_n':yes,
 'policy_not_detected_n':len(s)-yes,
 'checklist_items':report['checklist_items'],
 'consensus_rows':report['consensus_rows'],
 'universities':report['universities'],
 'nonempty_coding_notes':report['nonempty_coding_notes'],
 'dimension_cells_mismatched_at_2dp':report['dimension_cells_mismatched_at_2dp'],
 'institutional_indices_mismatched_at_2dp':report['institutional_indices_mismatched_at_2dp'],
 'fully_reproduced_institution_profiles':report['fully_reproduced_institution_profiles'],
 'intercoder_reliability_recomputation':report['intercoder_reliability_recomputation'],
 'consensus_matrix_admission':report['consensus_matrix_admission'],
 'uk_atrs_records':atrs['registry_records'],
 'uk_atrs_cells':atrs['record_dimension_cells'],
 'uk_atrs_direct':atrs['coverage_totals']['Direct'],
 'uk_atrs_partial':atrs['coverage_totals']['Partial'],
 'uk_atrs_none':atrs['coverage_totals']['None'],
 'uk_atrs_all_five_direct':atrs['all_five_direct_records'],
 'uk_atrs_production_records':atrs['production_records'],
 'uk_atrs_production_all_five_direct':atrs['production_all_five_direct'],
 'locked_result_files_present':all((ROOT/'data'/x).exists() for x in ['case_results_with_topsis.csv','numeric_consistency_report.json','threshold_sensitivity.csv'])
}
out['evidence_admission_logic_passed']=(
    out['screening_n']==100 and yes==13 and out['checklist_items']==27 and
    out['consensus_rows']==378 and out['universities']==14 and
    out['nonempty_coding_notes']==378 and out['locked_result_files_present'] and
    out['dimension_cells_mismatched_at_2dp']==21 and
    out['institutional_indices_mismatched_at_2dp']==4 and
    out['uk_atrs_records']==8 and out['uk_atrs_cells']==40 and
    out['uk_atrs_direct']==31 and out['uk_atrs_partial']==9 and out['uk_atrs_none']==0 and
    out['uk_atrs_all_five_direct']==2 and out['uk_atrs_production_records']==4 and
    out['uk_atrs_production_all_five_direct']==0
)
(ROOT/'audit'/'external_evidence_reproduction_report.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
sys.exit(0 if out['evidence_admission_logic_passed'] else 1)
