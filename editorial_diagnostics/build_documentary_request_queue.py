#!/usr/bin/env python3
"""Exact extract of missing *documentation requests* from the frozen V37 safeguard matrix.
A missing item is a failed *documentary admission*, not a missing real-world control.
This is not new source-to-safeguard coding, not independent outcome validation.
"""
from pathlib import Path
import csv,sys,json,collections,hashlib

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main(mpath, cpath, output_dir):
    mpath=Path(mpath); cpath=Path(cpath); out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    with mpath.open(encoding='utf-8-sig',newline='') as f:m=list(csv.DictReader(f))
    with cpath.open(encoding='utf-8-sig',newline='') as f:cases=list(csv.DictReader(f))
    assert len(m)==50 and len(cases)==11
    public=[r for r in m if r['Case_ID']!='C12']; assert len(public)==46
    outputs=[]
    for case in cases:
      cid=case['Case_ID']; rows=[r for r in public if r['Case_ID']==cid]
      assert len(rows)>=4
      admitted=[r for r in rows if r['m_ij']=='1']
      missing=[r for r in rows if r['m_ij']=='0']
      assert len(rows)==len(admitted)+len(missing)
      assert all(r['Missingness_Code']=='M0' for r in admitted)
      assert all(r['Missingness_Code'] in ('M1','M2','M3','M4','M6') for r in missing)
      accepted=not missing
      assert accepted==(case['Veto_Pass']=='Yes')
      outputs.append({
       'case_id':cid, 'use_context':case['Use_Case'], 'original_veto_status':case['Evidence_Status'],
       'frozen_mandatory_rows':len(rows), 'admitted_documented_rows':len(admitted), 'not_admitted_rows':len(missing),
       'document_requests_from_frozen_item_definitions':' | '.join(r['Mandatory_Safeguard'] for r in missing) if missing else 'None required under frozen protocol',
       'missingness_codes':' | '.join(r['Missingness_Code'] for r in missing) if missing else 'M0 only',
       'practical_interpretation':'Request use-specific, current, independently reviewable artifacts for named items before re-running the local institutional screen. Not evidence that controls are absent in practice.' if missing else 'Reconfirm source currency, campus or unit authority, use scope and institutional approval; historical documentary status is not deployment clearance.'})
    assert sum(x['not_admitted_rows'] for x in outputs)==26
    assert sum(x['admitted_documented_rows'] for x in outputs)==20
    assert sum(x['not_admitted_rows']==0 for x in outputs)==2
    assert sum(x['not_admitted_rows']>0 for x in outputs)==9
    op=out/'educational_document_request_queue_frozen_v37.csv'
    with op.open('w',newline='',encoding='utf-8') as f:
      dw=csv.DictWriter(f,fieldnames=list(outputs[0]));dw.writeheader();dw.writerows(outputs)
    audit={'status':'PASS','n_source_public_safeguard_rows':46,'n_admitted_rows':20,'n_documentary_not_admitted_rows':26,
          'hold_dossiers':9,'documented_dossiers':2,'case_ids_ordered':[x['case_id'] for x in outputs],
          'missingness_code_counts':dict(collections.Counter(r['Missingness_Code'] for r in public)),
          'source_safeguard_matrix_sha256':digest(mpath),'source_case_results_sha256':digest(cpath),'output_sha256':digest(op),
          'strict_boundary':'No independent recoding. Requests are literal names of failed applicability-aware mandatory items in the V37 reconstructed safeguard matrix. Do not claim deployment control absence or make new Veto decisions.'}
    (out/'document_request_queue_assertions.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(audit,indent=2))
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: script.py safeguard_matrix.csv public_case_results.csv destdir')
    main(*sys.argv[1:])
