import sys, os, shutil, subprocess, time, re, signal
name, edits = sys.argv[1], sys.argv[2:]   # edits: "file:regex=>repl"
S=os.path.dirname(os.path.abspath(__file__)); R=f"{S}/var_{name}"
shutil.rmtree(R, ignore_errors=True)
os.makedirs(f"{R}/output"); os.makedirs(f"{R}/state")
shutil.copytree(f"{S}/wolida4/inputs", f"{R}/inputs", symlinks=False)
shutil.copy(f"{S}/wolida4/state/coldState.nc", f"{R}/state/")
for e in edits:
    f, rx = e.split(":",1); a,b = rx.split("=>")
    p=f"{R}/inputs/{f}"; s=open(p).read(); s2=re.sub(a,b,s,flags=re.M); assert s!=s2, e; open(p,"w").write(s2)
c=open(f"{S}/wolida4/config.toml").read().replace("/wolida4/", f"/var_{name}/")
open(f"{R}/config.toml","w").write(c)
T=float(os.environ.get("T","360"))
env=dict(os.environ)
pr=subprocess.Popen(["caffeinate","-i","mpirun","-np","2","/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute_opt.exe","-c","config.toml"],cwd=R,env=env,stdout=open(f"{R}/run.log","w"),stderr=subprocess.STDOUT,start_new_session=True)
t0=time.time(); last=None
while time.time()-t0<T and pr.poll() is None:
    time.sleep(10)
try: os.killpg(pr.pid, signal.SIGTERM)
except Exception: pass
logs=sorted(os.listdir(f"{R}/output/logs")) if os.path.isdir(f"{R}/output/logs") else []
out=[]
for l in logs:
    t=open(f"{R}/output/logs/{l}").read().strip().split("\n")[-1]; out.append(t.strip())
print(name, "elapsed %.0f"%(time.time()-t0), "last dates:", out, "exit", pr.returncode)
