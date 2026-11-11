import json, tempfile, subprocess, sys, os, signal, time
from pathlib import Path
from causalguard.runner import Run, make_plan
from causalguard.testing_fixtures import hung_with_child

def alive(pid):
    try: os.kill(pid,0); return True
    except ProcessLookupError: return False

def main():
    if len(sys.argv)>1:
        tmp=Path(sys.argv[1]); p=make_plan('kill','FIXTURE',{}, [('item', {'pidfile':str(tmp/'pids')})])
        Run('kill',p,runs_root=tmp).execute(hung_with_child,workers=1,timeout_s=60)
        return
    tmp=Path(tempfile.mkdtemp(prefix='causalguard_r2_parentkill_review_'))
    parent=subprocess.Popen([sys.executable,__file__,str(tmp)], start_new_session=True, stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    wpid=cpid=None
    try:
        deadline=time.time()+10
        while not (tmp/'pids').exists() and time.time()<deadline: time.sleep(.02)
        wpid,cpid=map(int,(tmp/'pids').read_text().split())
        os.killpg(parent.pid,signal.SIGKILL); parent.wait(); time.sleep(.4)
        print(json.dumps({'case':'parent_group_sigkill','parent_returncode':parent.returncode,'worker_alive':alive(wpid),'grandchild_alive':alive(cpid),'worker_pid':wpid,'child_pid':cpid,'fixture_root':str(tmp)}))
    finally:
        if wpid and alive(wpid): os.killpg(wpid,signal.SIGKILL)
        if parent.poll() is None: parent.kill(); parent.wait()
        time.sleep(.3)
        print(json.dumps({'cleanup_worker_alive':alive(wpid),'cleanup_child_alive':alive(cpid)}))
if __name__=='__main__': main()
