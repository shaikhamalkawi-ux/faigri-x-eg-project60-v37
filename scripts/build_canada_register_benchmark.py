#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, hashlib
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'external_evidence/canada_ai_register/greatnorth_ai_register_transport_copy.csv'
OUT = ROOT / 'external_evidence/canada_ai_register'
FIG = ROOT / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

OFFICIAL_DATASET_URL = 'https://open.canada.ca/data/dataset/fcbc0200-79ba-4fa4-94a6-00e32facea6b'
OFFICIAL_RESOURCE_URL = 'https://open.canada.ca/data/dataset/fcbc0200-79ba-4fa4-94a6-00e32facea6b/resource/369f6f34-148a-42ed-b581-8c164e941a89'
TRANSPORT_URL = 'https://huggingface.co/datasets/GreatNorthCollective/greatnorth-ai-register/raw/main/data/processed/greatnorth_ai_register.csv'

FIELDS = [
    ('description', 'System description', 'description_ai_system_en'),
    ('primary_users', 'Primary users', 'ai_system_primary_users_en'),
    ('developer_type', 'Developer type', 'developed_by_en'),
    ('status', 'Lifecycle status', 'ai_system_status_en'),
    ('capabilities', 'AI capabilities', 'ai_system_capabilities_en'),
    ('data_sources', 'Data sources', 'data_sources_en'),
    ('personal_info', 'Personal-information indicator', 'involves_personal_information'),
    ('notification', 'AI notification indicator', 'notification_ai'),
    ('results', 'Reported system results', 'ai_system_results_en'),
]


def read_rows():
    with SRC.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def clean(v):
    if v is None: return ''
    return re.sub(r'\s+', ' ', str(v)).strip()


def normalize_status(v):
    v=clean(v).lower()
    if not v: return 'Not reported'
    if 'production' in v: return 'In production'
    if 'development' in v: return 'In development'
    if 'retired' in v or 'service' in v: return 'Retired'
    if v == 'none': return 'Not reported'
    return clean(v).title()


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

rows = read_rows()
flat=[]
for row in rows:
    raw=json.loads(row['raw_record'])
    rec={
        'AI_Register_ID': clean(raw.get('ai_register_id')),
        'System_Name': clean(raw.get('name_ai_system_en')),
        'Government_Organization': clean(raw.get('government_organization')),
        'Description': clean(raw.get('description_ai_system_en')),
        'Primary_Users': clean(raw.get('ai_system_primary_users_en')),
        'Developed_By': clean(raw.get('developed_by_en')),
        'Vendor_Information': clean(raw.get('vendor_information')),
        'Lifecycle_Status': normalize_status(raw.get('ai_system_status_en')),
        'Status_Date': clean(raw.get('status_date')),
        'Capabilities': clean(raw.get('ai_system_capabilities_en')),
        'Data_Sources': clean(raw.get('data_sources_en')),
        'Involves_Personal_Information': clean(raw.get('involves_personal_information')),
        'Personal_Information_Banks': clean(raw.get('personal_information_banks_en')),
        'AI_Notification': clean(raw.get('notification_ai')),
        'Reported_Results': clean(raw.get('ai_system_results_en')),
        'Official_Dataset_URL': row['source_url'],
        'Official_Resource_URL': row['source_resource_url'],
        'Source_License': row['source_license'],
        'Retrieved_At': row['retrieved_at'],
    }
    rec['Education_Training_Subset'] = 'Yes' if (
        'Canada School of Public Service' in rec['Government_Organization']
        or rec['AI_Register_ID'] in {'2526-CSA-ASC-002','2526-RCMP-GRC-010'}
    ) else 'No'
    flat.append(rec)

flat_fields=list(flat[0].keys())
write_csv(OUT/'canada_gc_ai_register_flat_412.csv', flat, flat_fields)
subset=[r for r in flat if r['Education_Training_Subset']=='Yes']
write_csv(OUT/'canada_gc_ai_register_education_training_subset.csv', subset, flat_fields)

# Field completeness overall and subset.
field_rows=[]
for code,label,key in FIELDS:
    for scope, data in [('Full register',flat),('Education/training subset',subset)]:
        n=len(data); non=sum(bool(r[{ 
            'description':'Description','primary_users':'Primary_Users','developer_type':'Developed_By','status':'Lifecycle_Status','capabilities':'Capabilities','data_sources':'Data_Sources','personal_info':'Involves_Personal_Information','notification':'AI_Notification','results':'Reported_Results'}[code]]) and not (code=='status' and r['Lifecycle_Status']=='Not reported') for r in data)
        field_rows.append({'Scope':scope,'Field_Code':code,'Field':label,'Nonempty_Count':non,'Total':n,'Percent':round(100*non/n,3)})
# Conditional PIB completeness among Y.
for scope,data in [('Full register',flat),('Education/training subset',subset)]:
    applicable=[r for r in data if r['Involves_Personal_Information'].upper()=='Y']
    non=sum(bool(r['Personal_Information_Banks']) for r in applicable)
    field_rows.append({'Scope':scope,'Field_Code':'pib_when_pi_yes','Field':'PIB reference when personal information = Y','Nonempty_Count':non,'Total':len(applicable),'Percent':round(100*non/len(applicable),3) if applicable else ''})
write_csv(OUT/'canada_register_field_completeness.csv', field_rows, list(field_rows[0].keys()))

# By lifecycle status.
status_summary=[]
for scope,data in [('Full register',flat),('Education/training subset',subset)]:
    counts=Counter(r['Lifecycle_Status'] for r in data)
    for status,n in sorted(counts.items()):
        status_summary.append({'Scope':scope,'Lifecycle_Status':status,'Count':n,'Percent':round(100*n/len(data),3)})
write_csv(OUT/'canada_register_status_distribution.csv',status_summary,list(status_summary[0].keys()))

# Disclosure count per record (unweighted count, not readiness score).
count_rows=[]
keymap={'description':'Description','primary_users':'Primary_Users','developer_type':'Developed_By','status':'Lifecycle_Status','capabilities':'Capabilities','data_sources':'Data_Sources','personal_info':'Involves_Personal_Information','notification':'AI_Notification','results':'Reported_Results'}
for r in flat:
    flags=[]
    for code,_,_ in FIELDS:
        val=r[keymap[code]]
        present=bool(val) and not(code=='status' and val=='Not reported')
        flags.append(int(present))
    count_rows.append({'AI_Register_ID':r['AI_Register_ID'],'System_Name':r['System_Name'],'Government_Organization':r['Government_Organization'],'Lifecycle_Status':r['Lifecycle_Status'],'Education_Training_Subset':r['Education_Training_Subset'],'Structured_Disclosure_Field_Count':sum(flags),'Maximum_Defined_Fields':len(flags),'Boundary':'Unweighted presence count only; not a readiness, quality, compliance, or implementation score.'})
write_csv(OUT/'canada_register_structured_disclosure_counts.csv',count_rows,list(count_rows[0].keys()))

# Schema crosswalk to FAIGRI dimensions.
crosswalk=[
{'FAIGRI_Area':'Privacy and data governance','Canada_Register_Fields':'Data sources; personal-information indicator; personal-information bank reference','Schema_Coverage':'Partial','Reason':'The schema identifies data sources and personal-information handling, but does not require a full privacy assessment, retention rule, security control, or consent basis.','Allowed_Use':'Construct and schema-gap comparison only.'},
{'FAIGRI_Area':'Fairness and accessibility','Canada_Register_Fields':'No dedicated field','Schema_Coverage':'Not explicit','Reason':'Fairness, subgroup testing, bias mitigation, and accessibility are not dedicated register fields.','Allowed_Use':'Schema-gap finding; not evidence that controls are absent.'},
{'FAIGRI_Area':'Transparency and limitations','Canada_Register_Fields':'Description; primary users; capabilities; notification; reported results','Schema_Coverage':'Partial','Reason':'The schema supports purpose and user-facing disclosure, but does not systematically require limitations, failure modes, or explanation rights.','Allowed_Use':'Construct and schema-gap comparison only.'},
{'FAIGRI_Area':'Human review and appeal','Canada_Register_Fields':'No dedicated field','Schema_Coverage':'Not explicit','Reason':'Human review, override, appeal, and contestability are not dedicated register fields.','Allowed_Use':'Schema-gap finding; not evidence that controls are absent.'},
{'FAIGRI_Area':'Accountability and risk','Canada_Register_Fields':'Government organization; developed by; vendor information; lifecycle status; results','Schema_Coverage':'Partial','Reason':'Ownership, provenance, vendor and lifecycle are disclosed, but there is no dedicated risk assessment, accountable officer, audit, or incident field in the released schema.','Allowed_Use':'Construct and schema-gap comparison only.'},
]
write_csv(OUT/'canada_register_faigri_schema_crosswalk.csv',crosswalk,list(crosswalk[0].keys()))

# Summary JSON.
summary={
 'records':len(flat),'departments':len(set(r['Government_Organization'] for r in flat)),
 'education_training_subset':len(subset),
 'status_full':dict(Counter(r['Lifecycle_Status'] for r in flat)),
 'status_subset':dict(Counter(r['Lifecycle_Status'] for r in subset)),
 'personal_information_yes':sum(r['Involves_Personal_Information'].upper()=='Y' for r in flat),
 'notification_yes':sum(r['AI_Notification'].upper()=='Y' for r in flat),
 'source_dataset_url':OFFICIAL_DATASET_URL,'source_resource_url':OFFICIAL_RESOURCE_URL,
 'transport_copy_url':TRANSPORT_URL,'transport_copy_sha256':sha256(SRC),
 'boundary':'The transport copy preserves official source and license fields. The official open-data record remains authoritative. Results describe released schema completeness, not control implementation or institutional readiness.'
}
(OUT/'canada_register_benchmark_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')

# Acquisition/provenance manifest.
manifest=[{
 'Dataset':'Government of Canada AI Register MVP','Official_Dataset_URL':OFFICIAL_DATASET_URL,'Official_Resource_URL':OFFICIAL_RESOURCE_URL,'Transport_Copy_URL':TRANSPORT_URL,'Transport_Copy_File':SRC.name,'Rows':len(flat),'License':'Open Government Licence - Canada','Acquisition_Date':'2026-07-22','SHA256':sha256(SRC),'Admission_Status':'Admitted for structured disclosure and schema-gap benchmarking; excluded from validation, calibration, prevalence beyond release, and control-effectiveness claims.'
}]
write_csv(OUT/'canada_register_acquisition_manifest.csv',manifest,list(manifest[0].keys()))

# Figure 7: field completeness.
labels=[]; fullp=[]; subp=[]
for code,label,_ in FIELDS:
    labels.append(label)
    fullp.append(next(r['Percent'] for r in field_rows if r['Scope']=='Full register' and r['Field_Code']==code))
    subp.append(next(r['Percent'] for r in field_rows if r['Scope']=='Education/training subset' and r['Field_Code']==code))
y=range(len(labels))
fig,ax=plt.subplots(figsize=(8.5,5.4))
ax.barh([i-0.18 for i in y],fullp,height=0.34,label='Full register',hatch='//')
ax.barh([i+0.18 for i in y],subp,height=0.34,label='Education/training subset',hatch='..')
ax.set_yticks(list(y)); ax.set_yticklabels(labels); ax.set_xlim(0,100)
ax.set_xlabel('Records with a non-empty structured field (%)')
ax.set_title('Government of Canada AI Register: structured field coverage')
ax.legend(loc='lower right'); ax.grid(axis='x',alpha=.25); fig.tight_layout()
fig.savefig(FIG/'fig7_canada_register_field_completeness.pdf',bbox_inches='tight')
fig.savefig(FIG/'fig7_canada_register_field_completeness.png',dpi=220,bbox_inches='tight')
plt.close(fig)

# Figure 8: status distribution.
statuses=['In development','In production','Retired','Not reported']
full_counts=Counter(r['Lifecycle_Status'] for r in flat); sub_counts=Counter(r['Lifecycle_Status'] for r in subset)
fig,ax=plt.subplots(figsize=(7.4,4.5))
x=list(range(len(statuses)))
ax.bar([i-0.18 for i in x],[full_counts[s]/len(flat)*100 for s in statuses],width=.34,label='Full register',hatch='//')
ax.bar([i+0.18 for i in x],[sub_counts[s]/len(subset)*100 for s in statuses],width=.34,label='Education/training subset',hatch='..')
ax.set_xticks(x); ax.set_xticklabels(statuses,rotation=12,ha='right')
ax.set_ylabel('Records (%)'); ax.set_title('Lifecycle status in the released register')
ax.legend(); ax.grid(axis='y',alpha=.25); fig.tight_layout()
fig.savefig(FIG/'fig8_canada_register_status_distribution.pdf',bbox_inches='tight')
fig.savefig(FIG/'fig8_canada_register_status_distribution.png',dpi=220,bbox_inches='tight')
plt.close(fig)

print(json.dumps(summary,indent=2))
