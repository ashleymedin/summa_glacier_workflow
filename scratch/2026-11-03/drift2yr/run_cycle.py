"""Cycle WY2005 N times from the cold state, each year restarting from the last restart file; usage: run_cycle.py <gulkana|wolverine> <exe> <N>"""
import sys, os, re, glob, shutil, subprocess
import numpy as np, xarray as xr
name, exe, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
H = os.path.dirname(os.path.abspath(__file__)); R = f"{H}/{name}_cycle"
shutil.rmtree(R, ignore_errors=True); shutil.copytree(f"{H}/{name}", R, ignore=shutil.ignore_patterns("output", "state", "run.log"))
c = open(f"{H}/{name}/config.toml").read().replace(f"{H}/{name}/", f"{R}/")
c = re.sub(r'^end_time   = .*', 'end_time   = "2005-09-30 23:00"', c, flags=re.M)
open(f"{R}/config.toml", "w").write(c)
I = f"{R}/summa_inputs"
oc = open(f"{I}/outputControl.txt").read().rstrip("\n") + "\n"
open(f"{I}/outputControl.txt", "w").write(oc)
cur = f"{H}/{name}/summa_inputs/coldState.nc"
for k in range(1, N + 1):
    for d in ("output", "state"): shutil.rmtree(f"{R}/{d}", ignore_errors=True); os.makedirs(f"{R}/{d}")
    shutil.copy(cur, f"{R}/state/coldState.nc")
    rc = subprocess.run(["caffeinate", "-i", exe, "-c", "config.toml", "-r", "e"], cwd=R, stdout=open(f"{R}/run.log", "w"), stderr=subprocess.STDOUT).returncode
    rs = sorted(glob.glob(f"{R}/output/*restart*.nc")) or sorted(glob.glob(f"{R}/state/*restart*.nc"))
    if rc or not rs: print("fail", k, rc, rs); break
    cur = f"{R}/cur_{k}.nc"; shutil.copy(rs[-1], cur)
    s = xr.open_dataset(cur); T = s.mLayerTemp.values[:, 0, :] - 273.15; z = s.mLayerDepth.values[:, 0, :]
    print(k, "ice dom 2/3 layers deeper than 1 m:", [[f"{zz:.2f}m:{tt:+.2f}" for zz, tt in zip(z[:, j], T[:, j]) if zz > 1] for j in (1, 2)], flush=True)
