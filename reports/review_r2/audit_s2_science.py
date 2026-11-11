"""Read-only audit of published R2 S2 fields plus independent exhaustive small-H checks.
Run with the project virtualenv; pass project directory as argv[1] if relocated.
This checks record consistency and expected grid shape, not independent truth for all saved predictions.
"""
import itertools
import json
import random
import sys
from pathlib import Path
from collections import Counter
from causalguard.runner import load_run
from causalguard.schema import Evidence, HypothesisClass, Intervention, Pred, Query
from causalguard.versionspace import candidate_class, build_version_space, network_from_choice, exact_query_counts, predict

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]
r=load_run(ROOT/'runs/S2-dev-v2')
counts=Counter()
for iid,o in r['results'].items():
 for reg,bs in o['regimes'].items():
  for b,x in bs.items():
   qs=x['queries']; counts['cells']+=1
   assert sum(q['kind']=='intervention' for q in qs)==16,(iid,reg,b,'intervention_shape')
   assert sum(q['kind']=='state' for q in qs)==8,(iid,reg,b,'state_shape')
   for q in qs:
    if q['num'] is None:
     counts['empty_queries']+=1
     continue
    num,den=int(q['num']),int(q['den']);counts['counted_queries']+=1
    assert 0<=num<=den
    assert q['tie']==(2*num==den)
    assert q['vs_majority']==(None if q['tie'] else int(2*num>den))
    assert q['p']==num/den
    assert q['verdict']==('refuted' if num==0 else 'entailed' if num==den else 'underdetermined')

rng=random.Random(604)
cls=candidate_class(2,2)
vs=build_version_space(Evidence(2,()),HypothesisClass(2,2))
nets=[network_from_choice(cls,list(c)) for c in itertools.product(range(cls.size),repeat=2)]
ivs=[Intervention(),Intervention('initial_edit',((0,1),(1,0))),Intervention('persistent_clamp',((0,0),)),Intervention('persistent_clamp',((0,1),(1,0)))]
targets=[Pred.or_(Pred.lit(0,0),Pred.lit(0,1)),Pred.and_(Pred.lit(0,1),Pred.lit(1,0)),Pred.not_(Pred.or_(Pred.lit(0,0),Pred.lit(1,1))),Pred.lit(1,0)]
n=0
for iv,h,tgt in itertools.product(ivs,range(4),targets):
 q=Query.point(rng.randrange(4),2,iv,h,tgt)
 a=exact_query_counts(vs,q); b=(sum(predict(net,q) for net in nets),len(nets))
 assert a==b,(iv,h,tgt,a,b)
 n+=1

s=json.loads((ROOT/'reports/development_r2/s2_v2_summary.json').read_text())
fpr=[]
for g in s['design_simulation_revised_primary']['grid']:
 z=g['null']
 fpr.append({'N':g['N_total'],'lower_tail':z['p_lower_gt_0'],'upper_tail':z['p_upper_lt_0'],'two_sided':z['p_lower_gt_0']+z['p_upper_lt_0']})
print(json.dumps({'record_audit':{'run_id':r['plan']['run_id'],'worlds':len(r['results']),**dict(counts),'shape_errors':0,'internal_consistency_errors':0},'exhaustive_check':{'n':2,'kmax':2,'networks':len(nets),'queries':n,'horizons':[0,1,2,3],'rng_seed':604,'mismatches':0},'sizing_null_false_positive_rates':fpr},indent=2))
