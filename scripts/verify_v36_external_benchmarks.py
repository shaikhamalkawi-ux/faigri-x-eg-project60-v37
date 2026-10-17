#!/usr/bin/env python3
from pathlib import Path
import csv, json, re
ROOT=Path(__file__).resolve().parents[1]

def rows(path):
    with path.open(newline='',encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

flat=rows(ROOT/'external_evidence/canada_ai_register/canada_gc_ai_register_flat_412.csv')
subset=rows(ROOT/'external_evidence/canada_ai_register/canada_gc_ai_register_education_training_subset.csv')
fields=rows(ROOT/'external_evidence/canada_ai_register/canada_register_field_completeness.csv')
status=rows(ROOT/'external_evidence/canada_ai_register/canada_register_status_distribution.csv')
edu=rows(ROOT/'external_evidence/educause/educause_ai_procurement_quickpoll_extract.csv')
sources=rows(ROOT/'data/source_registry.csv')
main=(ROOT/'main.tex').read_text(encoding='utf-8')
supp=(ROOT/'supplementary_evidence_audit.tex').read_text(encoding='utf-8')

def one(indicator):
    return next(float(r['Percent']) for r in edu if r['Indicator']==indicator)

def status_count(scope,label):
    return next(int(r['Count']) for r in status if r['Scope']==scope and r['Lifecycle_Status']==label)

def field_count(scope,code):
    r=next(r for r in fields if r['Scope']==scope and r['Field_Code']==code)
    return int(r['Nonempty_Count']), int(r['Total'])

checks={
 'canada_412':len(flat)==412,
 'canada_subset_33':len(subset)==33,
 'source_registry_38':len(sources)==38,
 'full_status_counts':status_count('Full register','In development')==182 and status_count('Full register','In production')==160 and status_count('Full register','Retired')==28 and status_count('Full register','Not reported')==42,
 'subset_status_counts':status_count('Education/training subset','In development')==9 and status_count('Education/training subset','In production')==21 and status_count('Education/training subset','Not reported')==3,
 'description_412':field_count('Full register','description')==(412,412),
 'primary_users_410':field_count('Full register','primary_users')==(410,412),
 'educause_values':all([one('Current procurement processes account for AI products')==49,one('Changes planned to account for AI products')==10,one('Ongoing review after initial procurement')==36,one('Institutional data security reviewed')==86,one('Legal and regulatory compliance reviewed')==86,one('Algorithmic bias reviewed')==30,one('Teaching and learning professionals included in procurement')==58,one('Technology professionals included in procurement')==94,one('Cybersecurity/data privacy professionals included')==85,one('Opaque contract terms are a top challenge')==21]),
 'main_has_canada_412':'412 records from 43 organizations' in main,
 'main_has_educause_36':'36\\% report ongoing review' in main,
 'main_has_registry_38':'38-record source registry' in main,
 'supp_has_registry_38':'38-record source registry' in supp,
 'figures_present':all((ROOT/f'figures/{n}').exists() for n in ['fig7_canada_register_field_completeness.pdf','fig8_canada_register_status_distribution.pdf']),
 'outreach_present':(ROOT/'outreach/outreach_status_register.csv').exists(),
}
report={'checks':checks,'overall_passed':all(checks.values())}
out=ROOT/'audit/v36_external_benchmark_verification.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['overall_passed'] else 1)
