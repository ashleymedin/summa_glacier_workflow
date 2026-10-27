import sys, os, shutil, subprocess, re
tag, val = sys.argv[1], sys.argv[2]
S=os.path.dirname(os.path.abspath(__file__)); R=f"{S}/tol_{tag}"
shutil.rmtree(R, ignore_errors=True); os.makedirs(f"{R}/output"); os.makedirs(f"{R}/state")
shutil.copytree(f"{S}/wolida4/inputs", f"{R}/inputs", symlinks=False)
shutil.copy(f"{S}/wolida4/state/coldState.nc", f"{R}/state/")
def row(n): return n.ljust(25)+" | "+val.rjust(12)+" | "+"0.0".rjust(12)+" | "+"0.1".rjust(12)
rows="\n".join(row(n) for n in ("absTolMatric","absTolAquifr","absTolWatVeg"))
p=f"{R}/inputs/localParamInfo.txt"; s=open(p).read()
s=re.sub(r"^(lowerBoundHead [^\n]*)(?=\n)", lambda m: m.group(1)+"\n"+rows, s, count=1, flags=re.M); open(p,"w").write(s)
c=open(f"{S}/wolida4/config.toml").read().replace("/wolida4/", f"/tol_{tag}/")
c=re.sub(r"^n_samples = .*", "n_samples = 16", c, flags=re.M); open(f"{R}/config.toml","w").write(c)
subprocess.run(["caffeinate","-i","mpirun","-np","5","/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute_opt.exe","-c","config.toml"],cwd=R,stdout=open(f"{R}/run.log","w"),stderr=subprocess.STDOUT)
