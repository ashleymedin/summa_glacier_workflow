"""Default-parameter Wolverine IDA spinup from the cold start to <end>, one process, to bisect a spinup stall; usage: spinrun.py <tag> <exe> <end, e.g. 2016-04-20> [diag: hourly solver counters and soil states]"""
import sys, os, shutil, subprocess, re, time
tag, exe, end = sys.argv[1:4]; diag = len(sys.argv) > 4
T = "/Users/amedin/Research/SummaSundials/summa/utils/test/test_calibration"
S = os.path.dirname(os.path.abspath(__file__)); R = f"{S}/spin_{tag}"; SRC = f"{T}/gulkana_wolverine/summa_inputs"
shutil.rmtree(R, ignore_errors=True); os.makedirs(f"{R}/output"); os.makedirs(f"{R}/state")
shutil.copytree(SRC, f"{R}/inputs"); shutil.copy(f"{SRC}/coldState.nc", f"{R}/state/")
p = f"{R}/inputs/modelDecisions.txt"; s = open(p).read()
open(p, "w").write(re.sub(r"^num_method\s+homegrown", "num_method                      ida      ", s, count=1, flags=re.M))
c = open(f"{T}/gulkana_wolverine_run/config.toml").read(); c = c[:c.index("[calibration]")]
c = c.replace(SRC + "/", f"{R}/inputs/").replace(f"{T}/gulkana_wolverine_run/", f"{R}/")
c = re.sub(r'^start_time = .*', 'start_time = "2015-10-01 00:00"', c, flags=re.M)
c = re.sub(r'^end_time   = .*', f'end_time   = "{end} 00:00"', c, flags=re.M)
if diag:
    c = re.sub(r'^write_timeseries = .*', 'write_timeseries = true', c, flags=re.M)
    open(f"{R}/inputs/outputControl.txt", "a").write("".join(f"{v} | 1\n" for v in ["wallClockTime", "numSteps", "meanStepSize", "mLayerMatricHead", "mLayerVolFracIce", "mLayerVolFracLiq", "mLayerTemp", "mLayerDepth"]))
open(f"{R}/config.toml", "w").write(c)
t0 = time.time()
r = subprocess.run(["caffeinate", "-i", "/usr/bin/time", "-p", exe, "-c", "config.toml"], cwd=R, stdout=open(f"{R}/run.log", "w"), stderr=subprocess.STDOUT)
print(tag, "exit", r.returncode, "wall %.0f s" % (time.time() - t0))
