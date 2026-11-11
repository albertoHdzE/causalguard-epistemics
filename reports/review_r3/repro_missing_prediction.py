"""Read-only R3 reproduction. Run from repository with .venv/bin/python. Never writes raw data."""
import copy
import json
from pathlib import Path
from causalguard.runner import load_run
from causalguard.analysis.s2_analysis import validate_world_v2, world_scores, _contrast, OutputDefect
ROOT=Path.cwd()
lr=load_run(ROOT/'runs/S2-dev-v2')
entries=[e for e in lr['plan']['items'] if e['payload']['population']=='realizable' and e['payload']['family']!='uniform_H' and e['strata'].get('label')=='realizable']
def score(o):
    return world_scores([q for q in o['regimes']['uniform_states']['16']['queries'] if q['kind']=='intervention'])
base=[{'family':e['payload']['family'], **score(lr['results'][e['item_id']])} for e in entries]
e=entries[0]
evidence={'repo':str(ROOT),'item_id':e['item_id'],'planned_primary_worlds':len(base),'original_contrast':_contrast(base,'index','vs_majority',100),'mutations':{}}
for mode in ('missing_first','missing_later','null_later','bool_later'):
    o=copy.deepcopy(lr['results'][e['item_id']])
    qs=[q for q in o['regimes']['uniform_states']['16']['queries'] if q['kind']=='intervention']
    q=qs[0] if mode=='missing_first' else next(q for q in qs[1:] if q['pred']['index']==q['truth'])
    if mode.startswith('missing'): q['pred'].pop('index')
    elif mode=='null_later':q['pred']['index']=None
    else:q['pred']['index']=bool(q['pred']['index'])
    try:
        v=validate_world_v2(e['item_id'],e['payload'],o)
        rows=copy.deepcopy(base);rows[0]={'family':e['payload']['family'],**score(o)}
        evidence['mutations'][mode]={'accepted':True,'primary_complete':v['primary_complete'],'world_scores':score(o),'contrast':_contrast(rows,'index','vs_majority',100)}
    except OutputDefect as exc:
        evidence['mutations'][mode]={'accepted':False,'error':str(exc)}
# Bound the finding: audit every saved ordinary regime row for required method keys/null semantics.
bad=[];n=0
for iid,o in lr['results'].items():
    for rg,bb in o['regimes'].items():
        for b,c in bb.items():
            for i,q in enumerate(c['queries']):
                n+=1
                if set(q['pred'])!={'index','bdd','dnf','circuit'} or (not c['empty'] and any(x is None for x in q['pred'].values())):
                    bad.append([iid,rg,b,i])
evidence['saved_record_audit']={'rows':n,'bad_rows':bad,'raw_records_changed':False}
p=Path('/tmp/causalguard-r3-science-review/missing_prediction_evidence.json')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(evidence,indent=2)+'\n')
print(p)
for name,m in evidence['mutations'].items():print(name,m['accepted'],m.get('primary_complete'),m.get('contrast',{}).get('n_worlds'),m.get('contrast',{}).get('estimate'))
print(evidence['saved_record_audit'])
