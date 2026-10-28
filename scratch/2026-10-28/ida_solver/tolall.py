"""All IDA tolerances moved together; usage: tolall.py <tag> <tol|be> <n_samples> <n_ranks> <exe>
Runs the bundled gulkana_wolverine calibration setup in its own directory, one variant per call; reports total CPU time."""
import sys, os, shutil, subprocess, re, time
tag, val, ns, nr, exe = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
T = "/Users/amedin/Research/SummaSundials/summa/utils/test/test_calibration"
S = os.path.dirname(os.path.abspath(__file__)); R = f"{S}/tolall_{tag}"
shutil.rmtree(R, ignore_errors=True); os.makedirs(f"{R}/output"); os.makedirs(f"{R}/state")
shutil.copytree(f"{T}/gulkana_wolverine/summa_inputs", f"{R}/inputs")
shutil.copy(f"{T}/gulkana_wolverine/summa_inputs/coldState.nc", f"{R}/state/")
if val != "be":
    p = f"{R}/inputs/modelDecisions.txt"; s = open(p).read()
    s = re.sub(r"^num_method\s+homegrown", "num_method                      ida      ", s, count=1, flags=re.M)
    open(p, "w").write(s)
    names = [f"{k}Tol{v}" for v in ("TempCas", "TempVeg", "WatVeg", "TempSoilSnow", "WatSnow", "Matric", "Aquifr") for k in ("rel", "abs")]
    rows = "\n".join(n.ljust(25) + " | " + val.rjust(12) + " | " + "0.0".rjust(12) + " | " + "0.1".rjust(12) for n in names)
    p = f"{R}/inputs/localParamInfo.txt"; s = open(p).read()
    s = re.sub(r"^(lowerBoundHead [^\n]*)(?=\n)", lambda m: m.group(1) + "\n" + rows, s, count=1, flags=re.M)
    open(p, "w").write(s)
c = open(f"{T}/wolverine_run/config.toml").read()
c = c.replace(f"{T}/gulkana_wolverine/summa_inputs/", f"{R}/inputs/").replace(f"{T}/wolverine_run/", f"{R}/")
c = re.sub(r"^n_samples = .*", f"n_samples = {ns}", c, flags=re.M)
open(f"{R}/config.toml", "w").write(c)
t0 = time.time()
r = subprocess.run(["/usr/bin/time", "-p", "mpirun", "-np", nr, exe, "-c", "config.toml"], cwd=R,
                   stdout=open(f"{R}/run.log", "w"), stderr=open(f"{R}/time.log", "w"))
print(tag, "exit", r.returncode, "wall %.0f s" % (time.time() - t0)); print(open(f"{R}/time.log").read()[-120:])
