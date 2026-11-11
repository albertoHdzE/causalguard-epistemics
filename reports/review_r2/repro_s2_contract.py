import json, tempfile, shutil, hashlib, copy
from pathlib import Path
from causalguard.runner import config_hash, item_key, load_run
import causalguard.analysis.s2_analysis as a
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'runs/S2-dev-v2'
plan=json.loads((source/'plan.json').read_text())
chosen=[]
for fam in a.SUPPORTED_ENDPOINT_V2_KEYS['families']:
 chosen.append(next(x for x in plan['items'] if x['strata'].get('label')=='realizable' and x['strata']['family']==fam))
root=Path(tempfile.mkdtemp(prefix='cg_s2_r2_contract_'))
r=root/'run'; r.mkdir(); (r/'attempts').mkdir()
plan['items']=chosen
plan['config']['populations']=[{**plan['config']['populations'][0], 'worlds_per_family': 1}]
plan['config_hash']=config_hash(plan['config'])
plan['plan_sha256']=config_hash({k:v for k,v in plan.items() if k!='plan_sha256'})
(r/'plan.json').write_text(json.dumps(plan))
for e in chosen:
 key=item_key(e['item_id']); shutil.copytree(source/'attempts'/key,r/'attempts'/key)
 for af in (r/'attempts'/key).glob('*.json'):
  ar=json.loads(af.read_text()); ar['plan_sha256']=plan['plan_sha256']; af.write_text(json.dumps(ar))
  assert ar['source_tree_sha256']==plan['source_tree_sha256']
  assert ar['run_id']==plan['run_id']
  assert ar['payload_sha256']==e['payload_sha256']
a.design_simulation=lambda *args,**kwargs: {'review_fixture':'skipped expensive sizing'}
a._figures_v2=lambda *args,**kwargs: None
# Remove one full primary endpoint from one nominally successful world.
f=next((r/'attempts'/item_key(chosen[0]['item_id'])).glob('*.json'))
rec=json.loads(f.read_text()); old=copy.deepcopy(rec)
rec['output']['regimes']['uniform_states'].pop('16')
f.write_text(json.dumps(rec))
res=a.analyze_v2([r],root/'out-missing-cell',ROOT/'configs/endpoints/S2-primary-v2.json',reps_primary=50,reps_secondary=30)
s=json.loads(Path(res['summary']).read_text())
print('MISSING_B16_CELL',json.dumps({'accounting':res['accounting'],'primary_n':res['primary']['n_worlds'],'status':res['primary']['status'],'null_B16':s['null_uniform_H']['B16|index-vs_majority']}))
# Remove 15/16 intervention queries; terminal world still accepted with one-query endpoint.
rec=copy.deepcopy(old); qs=rec['output']['regimes']['uniform_states']['16']['queries']; ints=[q for q in qs if q['kind']=='intervention']; rec['output']['regimes']['uniform_states']['16']['queries']=[q for q in qs if q['kind']!='intervention']+ints[:1]; f.write_text(json.dumps(rec))
res=a.analyze_v2([r],root/'out-short-query-grid',ROOT/'configs/endpoints/S2-primary-v2.json',reps_primary=50,reps_secondary=30)
s=json.loads(Path(res['summary']).read_text())
print('SHORT_PRIMARY_GRID',json.dumps({'accounting':res['accounting'],'primary_n':res['primary']['n_worlds'],'primary_query_total':s['ties']['primary_queries'],'expected_queries':80,'status':res['primary']['status']}))
print('fixture',root)
