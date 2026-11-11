import json, tempfile
from pathlib import Path
from causalguard.runner import Run, make_plan, load_run
from causalguard.testing_fixtures import echo

def main():
    tmp=Path(tempfile.mkdtemp(prefix='causalguard_r2_runtime_review_'))
    p=make_plan('failure','FIXTURE',{}, [('item', {'value':1, 'fail':True})])
    run=Run('failure',p,runs_root=tmp)
    first=run.execute(echo,workers=1,timeout_s=30)
    second=Run('failure',p,runs_root=tmp,resume=True).execute(echo,workers=1,timeout_s=30)
    print(json.dumps({'case':'failure_resume','first_status':first['status'],'resume_status':second['status'],'remaining_failures':len(load_run(run.dir)['failures'])}))
    p=make_plan('identity','FIXTURE',{}, [('item', {'value':1})])
    run=Run('identity',p,runs_root=tmp)
    run.execute(echo,workers=1,timeout_s=30)
    ap=next((run.dir/'attempts').rglob('001.json'))
    a=json.loads(ap.read_text()); a['source_tree_sha256']='WRONG_SOURCE'; a['plan_sha256']='WRONG_PLAN'; a['run_id']='OTHER_RUN'
    ap.write_text(json.dumps(a))
    print(json.dumps({'case':'wrong_attempt_identity','accepted_results':load_run(run.dir)['results']}))
    pp=run.dir/'plan.json'; saved=json.loads(pp.read_text()); saved['items'][0]['payload']['value']=999; pp.write_text(json.dumps(saved))
    resumed=Run('identity',p,runs_root=tmp,resume=True)
    print(json.dumps({'case':'corrupt_stored_plan','resume_accepted':True,'stored_payload':saved['items'][0]['payload'],'requested_payload':p['items'][0]['payload']}))
    print(json.dumps({'fixture_root':str(tmp)}))
if __name__=='__main__': main()
