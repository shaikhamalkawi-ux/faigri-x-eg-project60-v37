#!/usr/bin/env python3
"""Post-hoc descriptive cross-tabulation of immutable V37 public-case records.

NO fitting, imputations, human coding, evidence updates or changes to original source.
The result answers when a numerical Upper band and missing mandatory documentation
co-occur for the frozen case set under the *existing* risk and threshold rule.
"""
from pathlib import Path
import csv, hashlib, json, math, sys

LAMBDAS = (0.00, 0.05, 0.10, 0.125, 0.15, 0.16, 0.25, 0.75, 1.25)
UPPER = .55
LOWER = .30


def sha256(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(2**18), b''):
            h.update(block)
    return h.hexdigest()


def main(source, dest):
    source=Path(source); dest=Path(dest); dest.mkdir(parents=True, exist_ok=True)
    with source.open(encoding='utf-8-sig', newline='') as f:
        raw=list(csv.DictReader(f))
    public=[r for r in raw if r['Case_Type']=='Public-evidence case']
    assert len(public)==11 and len(raw)==11, (len(public), len(raw))
    assert {r['Case_ID'] for r in public}=={f'C{i:02}' for i in range(1,12)}
    assert 'C12' not in {r['Case_ID'] for r in public}
    flags={r['Case_ID']:r['Veto_Pass'] for r in public}
    assert sum(v=='Yes' for v in flags.values())==2
    assert set(cid for cid,v in flags.items() if v=='Yes')=={'C02','C03'}
    for r in public:
        g=sum(float(r[col]) for col in ('P','F','T','H','L'))/5
        assert math.isclose(g,float(r['G_equal']),rel_tol=0,abs_tol=1e-14)
        assert math.isclose(g*math.exp(-.75*float(r['R'])),float(r['S_lambda_0.75']),rel_tol=0,abs_tol=1e-14)
        exp_band=('Upper' if g>=UPPER else 'Review' if g>=LOWER else 'Lower')
        assert exp_band==r['Zone_no_risk']
        s=float(r['S_lambda_0.75'])
        band=('Upper' if s>=UPPER else 'Review' if s>=LOWER else 'Lower')
        assert band==r['Risk_Zone_0.75']
    observed=[]
    for lam in LAMBDAS:
        upper=[]; review=[]; lower=[]
        for r in public:
            s=float(r['G_equal'])*math.exp(-lam*float(r['R']))
            if s>=UPPER: upper.append(r['Case_ID'])
            elif s>=LOWER: review.append(r['Case_ID'])
            else: lower.append(r['Case_ID'])
        held_upper=[c for c in upper if flags[c]=='No']
        documented_upper=[c for c in upper if flags[c]=='Yes']
        observed.append(dict(lambda_risk_posture=f'{lam:g}',upper=len(upper),review=len(review),lower=len(lower),upper_with_veto_hold=len(held_upper),upper_with_documented_evidence=len(documented_upper),upper_hold_case_ids=';'.join(held_upper) or 'none',
            interpretation='conditional demonstration; not a university authorization'))
        assert len(upper)+len(review)+len(lower)==11
    exact=[(0,5,6,0,3,2),(.05,4,7,0,2,2),(.10,4,7,0,2,2),(.125,3,8,0,1,2),(.15,2,9,0,1,1),(.16,0,11,0,0,0),(.25,0,11,0,0,0),(.75,0,5,6,0,0),(1.25,0,3,8,0,0)]
    for item, (lam,u,r,l,held,doc) in zip(observed,exact):
        assert math.isclose(float(item['lambda_risk_posture']),lam, abs_tol=1e-12)
        assert (item['upper'],item['review'],item['lower'],item['upper_with_veto_hold'],item['upper_with_documented_evidence'])==(u,r,l,held,doc),item
    assert observed[0]['upper_hold_case_ids']=='C01;C04;C07', observed[0]
    fieldnames=list(observed[0]); output=dest/'gate_upper_nonredundancy_from_frozen_v37.csv'
    with output.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fieldnames); writer.writeheader();writer.writerows(observed)
    report={
      'status':'PASS',
      'source':str(source.name),
      'source_sha256':sha256(source),
      'n_public':len(public),
      'n_synthetic_excluded':1,
      'n_frozen_documented':2,
      'n_frozen_hold':9,
      'base_lambda_no_attenuation':{'upper':5,'upper_with_hold':3,'upper_with_documented':2,'upper_hold_cases':['C01','C04','C07']},
      'declared_risk_posture_0_75':{'upper':0,'review':5,'lower':6,'total_hold':9},
      'frozen_veto_flags_unchanged':True,
      'input_scores_unchanged':True,
      'calibration_or_external_validation':'NOT CLAIMED',
      'output_sha256':sha256(output),
      'asserted_lambda_grid':len(LAMBDAS),
      'scientific_boundary':'Post-hoc arithmetic cross-tabulation on the same locked 11-dossier purposive sample; no new statistical population or human institutional outcome.'
    }
    (dest/'gate_nonredundancy_assertions.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: script.py path/to/public_case_results.csv outputdir')
    main(sys.argv[1],sys.argv[2])
