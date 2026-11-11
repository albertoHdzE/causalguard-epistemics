import json, tempfile, subprocess, sys
from pathlib import Path
from causalguard.runner import Run, make_plan, load_run, read_jsonl
from causalguard.testing_fixtures import echo

def main():
    plan=make_plan('same','FIXTURE',{}, [('item', {'value':1,'sleep':1})])
    if len(sys.argv)>1:
        Run('same',plan,runs_root=Path(sys.argv[1]),resume=True).execute(echo,workers=1,timeout_s=30)
        return
    tmp=Path(tempfile.mkdtemp(prefix='causalguard_r2_concurrent_review_'))
    Run('same',plan,runs_root=tmp)
    a=subprocess.Popen([sys.executable,__file__,str(tmp)])
    b=subprocess.Popen([sys.executable,__file__,str(tmp)])
    ae=a.wait(); be=b.wait()
    lr=load_run(tmp/'same'); ev=read_jsonl(tmp/'same'/'events.jsonl')
    print(json.dumps({'exit_codes':[ae,be],'attempt_files':lr['attempts_total'],'attempt_end_events':[e for e in ev if e['event']=='attempt_end'],'results':lr['results'],'fixture_root':str(tmp)}))
if __name__=='__main__': main()
