"""Two-year drift check: run a built *_added case from its 2004-10 cold start to 2006-09 with daily layer states; usage: run_drift.py <gulkana|wolverine> <exe>"""
import sys, os, re, shutil, subprocess
name, exe = sys.argv[1:3]
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.abspath(f"{H}/../../.."); R = f"{H}/{name}"; I = f"{R}/summa_inputs"
shutil.rmtree(R, ignore_errors=True); shutil.copytree(f"{W}/runs/{name}_added", R)
src = open(f"{W}/tests/{name}_run/config.toml").read()
c = src[:src.index("[calibration]")]
fp = open(f"{R}/forcing_path.txt").read().strip().rstrip("/")
c = re.sub(r'^start_time = .*', 'start_time = "2004-10-01 00:00"', c, flags=re.M)
c = re.sub(r'^end_time   = .*', 'end_time   = "2006-09-30 23:00"', c, flags=re.M)
c = re.sub(r'^write_timeseries = .*', 'write_timeseries = true', c, flags=re.M)
c = re.sub(r'^work_path = .*', f'work_path = "{R}/output"', c, flags=re.M)
c = re.sub(r'^settings_path = .*', f'settings_path = "{I}/"', c, flags=re.M)
c = re.sub(r'^forcing_path  = .*', f'forcing_path  = "{fp}/"', c, flags=re.M)
c = re.sub(r'^state_path    = .*', f'state_path    = "{R}/state/"', c, flags=re.M)
c = re.sub(r'^output_path   = .*', f'output_path   = "{R}/output/"', c, flags=re.M)
for d in ("output", "state"): os.makedirs(f"{R}/{d}")
shutil.copy(f"{I}/coldState.nc", f"{R}/state/")
oc = open(f"{I}/outputControl.txt").read().rstrip("\n") + "\n! drift check\n"
open(f"{I}/outputControl.txt", "w").write(oc + "".join(f"{v} | 24\n" for v in ["nSnow", "DOMarea", "mLayerTemp", "mLayerVolFracIce", "mLayerVolFracLiq", "mLayerDepth", "scalarSWE", "scalarGlceWE", "basin__GlacierArea"] if not re.search(rf"^{v}\b", oc, re.M)))
open(f"{R}/config.toml", "w").write(c)
sys.exit(subprocess.run(["caffeinate", "-i", exe, "-c", "config.toml"], cwd=R, stdout=open(f"{R}/run.log", "w"), stderr=subprocess.STDOUT).returncode)
