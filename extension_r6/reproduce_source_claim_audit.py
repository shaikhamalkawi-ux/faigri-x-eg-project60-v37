#!/usr/bin/env python3
"""Reproduce a bounded source/claim audit; never infer safeguards from field presence.

Requires the exact R5 private snapshots in --raw-dir. No network requests are made.
The manually authored interpretations remain explicitly distinct from executable QA.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys, unicodedata
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent

def normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())

def approx(n0: int, n1: int, p0: float, p1: float) -> dict:
    d=p1-p0
    se=math.sqrt(p0*(1-p0)/n0+p1*(1-p1)/n1)
    if se<=0: raise ValueError('Nonpositive standard error')
    z=d/se
    return {'difference_pp':100*d,'se':se,'z':z,'p_two_sided':math.erfc(abs(z)/math.sqrt(2)),
            'ci95_low_pp':100*(d-1.96*se),'ci95_high_pp':100*(d+1.96*se)}

def rounded_events(n: int, rate: float) -> list[int]:
    # Displayed percentages have one decimal place: +/- 0.05 percentage point.
    lo,hi=rate-0.0005,rate+0.0005
    return [k for k in range(n+1) if lo <= k/n < hi]

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows: raise ValueError('No data rows')
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run(raw: Path, out: Path) -> dict:
    if out.exists(): raise ValueError('Output already exists; choose a new directory to preserve prior runs')
    try:
        from bs4 import BeautifulSoup
        import fitz
    except ImportError as exc:
        raise RuntimeError('Install beautifulsoup4 and PyMuPDF in your environment') from exc
    manifest=json.loads((HERE/'R5_SOURCE_BINARY_MANIFEST_SHA256.json').read_text())
    claims=list(csv.DictReader((HERE/'source_claim_trace.csv').open(encoding='utf-8')))
    if len(manifest)!=17 or len({r['source_id'] for r in manifest})!=17:
        raise ValueError('Manifest does not contain the locked 17 unique snapshots')
    if len(claims)!=16 or len({r['trace_id'] for r in claims})!=16:
        raise ValueError('Trace schema/count changed')
    if len({r['source_id'] for r in claims})!=9: raise ValueError('Selected source set changed')
    source_texts={}; page_texts={}; source_checks=[]
    for r in manifest:
        p=raw/r['filename']
        if not p.is_file(): raise ValueError('Missing source '+r['filename'])
        b=p.read_bytes(); h=hashlib.sha256(b).hexdigest()
        if h!=r['sha256'] or len(b)!=r['bytes']:
            raise ValueError('SOURCE_HASH_MISMATCH '+r['source_id'])
        if r['mime']=='application/pdf':
            if not b.startswith(b'%PDF-'): raise ValueError('Invalid PDF')
            doc=fitz.open(stream=b,filetype='pdf')
            pages=[page.get_text() for page in doc]; page_texts[r['source_id']]=pages
            text='\n'.join(pages); title='PDF: '+r['filename']
        else:
            soup=BeautifulSoup(b,'html.parser')
            title=soup.title.get_text(' ',strip=True) if soup.title else ''
            for tag in soup(['script','style','nav','header','footer']):tag.decompose()
            text=soup.get_text(' ',strip=True)
            if 'access denied' in normalized(title) or 'captcha' in normalized(title):
                raise ValueError('Access-block page instead of source '+r['source_id'])
        source_texts[r['source_id']]=text
        source_checks.append({'source_id':r['source_id'],'filename':r['filename'],'bytes':len(b),
                              'sha256':h,'hash_pass':True,'document_title':title})
    anchor_checks=[]
    for r in claims:
        sid=r['source_id']
        if sid not in source_texts: raise ValueError('Unarchived source used in trace '+sid)
        if r['pdf_pages']=='html': text=source_texts[sid]
        else:
            pages=page_texts[sid]
            indices=[int(x)-1 for x in r['pdf_pages'].split('|')]
            if any(i<0 or i>=len(pages) for i in indices):raise ValueError('Invalid PDF locator')
            text='\n'.join(pages[i] for i in indices)
        for anchor in r['anchor_checks'].split('|'):
            passed=normalized(anchor) in normalized(text)
            anchor_checks.append({'trace_id':r['trace_id'],'source_id':sid,'locator':r['locator'],
                                  'anchor':anchor,'present':passed})
    missing=[r for r in anchor_checks if not r['present']]
    if missing: raise ValueError('SOURCE_LOCATOR_CHECK_FAILED '+json.dumps(missing))
    stats=[]; sens=[]
    for outcome,p0,p1 in [('Persistence',.759,.773),('GPA_above_2',.678,.691)]:
        a=approx(3327,3327,p0,p1)
        stats.append({'outcome':outcome,'n_control_assumed':3327,'n_test_assumed':3327,
                      'displayed_control_rate':p0,'displayed_test_rate':p1,**a})
        x0=rounded_events(3327,p0);x1=rounded_events(3327,p1)
        probs=[approx(3327,3327,k0/3327,k1/3327)['p_two_sided'] for k0 in x0 for k1 in x1]
        sens.append({'outcome':outcome,'possible_control_events':';'.join(map(str,x0)),
                     'possible_test_events':';'.join(map(str,x1)),'event_pairs':len(probs),
                     'p_min':min(probs),'p_max':max(probs),
                     'all_p_above_005_unadjusted':all(p>.05 for p in probs)})
    summary={'audit':'R6 bounded source-to-claim extension','raw_snapshots_checked':17,
             'raw_sha_pass':sum(r['hash_pass'] for r in source_checks),
             'analyst_authored_traces':16,'selected_source_objects':9,
             'locator_anchor_checks':len(anchor_checks),'locator_anchor_pass':sum(r['present'] for r in anchor_checks),
             'original_core_rescored':False,'new_veto_decisions':0,
             'semantic_intercoder_validation_performed':False,
             'statistical_method':'Illustrative unadjusted independent-proportion normal approximation; Wald CI; displayed rounded values and n assumed.',
             'inferential_boundary':'The original inferential method and analysis denominators are unavailable. This is not reproduction or refutation of the original trial analysis.',
             'source_boundary':'Byte integrity and lexical anchors do not establish independent semantic validation or control effectiveness.'}
    out.mkdir(parents=True)
    write_csv(out/'binary_integrity.csv',source_checks);write_csv(out/'locator_checks.csv',anchor_checks)
    write_csv(out/'unadjusted_summary_check.csv',stats);write_csv(out/'rounding_sensitivity.csv',sens)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
    (out/'OUTPUT_SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return summary

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-dir',type=Path,required=True,help='Directory containing exact R5 source filenames')
    p.add_argument('--out-dir',type=Path,required=True,help='New output directory; never overwritten')
    a=p.parse_args()
    try: result=run(a.raw_dir,a.out_dir)
    except (ValueError,RuntimeError,OSError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);return 1
    print(json.dumps(result,indent=2,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
