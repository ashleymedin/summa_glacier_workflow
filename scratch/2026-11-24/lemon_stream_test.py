#!/usr/bin/env python3
"""lemon_stream (one GRU, all glacier water through the lake) and lemon_stream_grus (three), WY2016-WY2026 at the default parameters on the
white-ice SUMMA, routed, from each case's spun-up state; runs in <case>/test."""
import os, re, shutil, subprocess, sys
W = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, W + "/runs"); os.chdir(W + "/runs")
from calibrate import config_text
EXE = os.environ["SUMMA_DIR"] + "/bin/summa_sundials_mizuroute.exe"
procs = []
for case in sys.argv[1:] or ("lemon_stream", "lemon_stream_grus"):
    run = f"{W}/runs/{case}"; d = run + "/test"; shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d + "/output"); os.makedirs(d + "/state")
    shutil.copy(run + "/summa_inputs/coldState.nc", d + "/state/")
    shutil.copytree(run + "/summa_inputs", d + "/settings")
    with open(d + "/settings/outputControl.txt", "a") as f:
        for v in ("scalarStreamTemp", "averageRoutedRunoffTemp", "glacierRoutedRunoff", "scalarStreamInflow", "scalarStreamOutflow"):
            f.write(f"{v} | day | mean\n")
    c = config_text(case, run, d + "/settings", d, "2015-10-01", "2026-07-31", "2015-10-01", "2026-07-31", "dds", 1, 1, temperature=True)
    c = c[:c.index("\n[calibration]")].replace("write_timeseries = false", "write_timeseries = true").replace("write_Qreach = false", "write_Qreach = true")
    open(d + "/config.toml", "w").write(c)
    procs.append(subprocess.Popen([EXE, "-c", d + "/config.toml", "-r", "e"], cwd=d, stdout=open(d + "/run.log", "w"), stderr=subprocess.STDOUT))
print([p.wait() for p in procs])
