import sys, multiprocessing as mp, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from causalguard.runner import _worker_main

def touch(payload):
    Path(payload['marker']).write_text('scientific work started')
    time.sleep(2)
    return {}

if __name__ == '__main__':
    ctx=mp.get_context('spawn')
    root=Path(tempfile.mkdtemp(prefix='r3_start_race_'))
    outcomes=[]
    for i in range(5):
        conn,child=ctx.Pipe()
        lr,lw=ctx.Pipe(duplex=False)
        marker=root/str(i)
        proc=ctx.Process(target=_worker_main,args=(child,touch,lr,str(root/'workers.lock')))
        proc.start()
        child.close();lr.close();lw.close()
        conn.send({'marker':str(marker)})
        proc.join(10)
        outcomes.append({'marker':marker.exists(),'exit':proc.exitcode})
        conn.close()
    print(root)
    print(outcomes)
