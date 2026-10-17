#!/usr/bin/env python3
"""Use only frozen V37 public_case_results.csv to visualize gate-vs-score divergence.
The original Fig. 3 remains unchanged and is retained in Supplementary Material.
"""
from pathlib import Path
import csv, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import sys

def main(src,figure_dir):
  src=Path(src); p=Path(figure_dir);p.mkdir(parents=True,exist_ok=True)
  with src.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
  assert len(rows)==11 and sum(r['Veto_Pass']=='Yes' for r in rows)==2
  xs=np.linspace(0,.2,2001)
  g=np.array([float(r['G_equal']) for r in rows])
  risk=np.array([float(r['R']) for r in rows])
  hold=np.array([r['Veto_Pass']=='No' for r in rows])
  upper=(g[None,:]*np.exp(-xs[:,None]*risk[None,:])>=.55)
  all_u=upper.sum(axis=1)
  held=(upper&hold[None,:]).sum(axis=1)
  documented=(upper&(~hold)[None,:]).sum(axis=1)
  assert list(map(int,(all_u[0],held[0],documented[0],all_u[-1])))==[5,3,2,0]
  assert np.all(all_u==held+documented)
  fig,ax=plt.subplots(figsize=(7.65,3.4))
  ax.step(xs,all_u,where='post',lw=2.0,color='0.12',label='All numerically Upper')
  ax.step(xs,held,where='post',lw=2.0,ls='--',color='0.37',label='Upper with Veto Hold')
  ax.step(xs,documented,where='post',lw=1.8,ls=':',color='0.55',label='Upper with documented gate')
  ax.axvline(.15818,linewidth=1.0,ls=':',color='0.8')
  ax.set(xlim=(0,.20),ylim=(-.20,6.2),xticks=np.arange(0,.201,.025),yticks=np.arange(0,7,1),
         xlabel=r'Risk-posture convention $\lambda$ (exponential attenuation)',
         ylabel='Numerically Upper public dossiers')
  ax.text(.012,5.45,'At $\\lambda$=0: 5 Upper, 3 of them on Hold',fontsize=9) if False else None
  ax.annotate('3 Upper files still on Hold at $\\lambda=0$'.replace('\\\\','\\'),xy=(0,3),xytext=(.035,4.55),
         arrowprops={'arrowstyle':'-','lw':.75,'color':'0.5'},fontsize=8,color='0.15')
  ax.legend(loc='upper right',fontsize=8,frameon=False)
  ax.grid(axis='y',alpha=.16)
  ax.spines[['right','top']].set_visible(False)
  fig.tight_layout()
  fig.savefig(p/'fig3_gate_upper_frontier.pdf',bbox_inches='tight')
  fig.savefig(p/'fig3_gate_upper_frontier.png',bbox_inches='tight',dpi=240)
  plt.close(fig)
  print('Saved fixed-case step diagnostic, no source data modified')
if __name__=='__main__':
  if len(sys.argv)!=3:raise SystemExit('usage: script source_csv figure_dir')
  main(*sys.argv[1:])
