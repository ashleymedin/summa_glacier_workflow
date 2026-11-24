#!/usr/bin/env python3
"""Run members of the cheap lemon_grus calibration over WY2006-WY2026 as lemon_grus_test.py's flat run, with the trial's parameters (runs/lemon_grus/test/m<sample>)."""
import os, shutil, subprocess, sys
W = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); T = f"{W}/runs/lemon_grus/test"
EXE = os.path.expanduser("~/Research/SummaSundials/summa_wetprecip/bin/summa_sundials_mizuroute.exe"); procs = []
for s in sys.argv[1:]:
    d = f"{T}/m{s}"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d + "/output"); os.makedirs(d + "/state")
    shutil.copytree(f"{T}/flat/settings", d + "/settings"); shutil.copy(d + "/settings/coldState.nc", d + "/state/coldState.nc")
    shutil.copy(f"{W}/runs/lemon_grus/cheap/output/lemon_grus_run0001_sample{s}_trialParams.nc", d + "/settings/trialParams.nc")
    open(d + "/config.toml", "w").write(open(f"{T}/flat/config.toml").read().replace(f"{T}/flat", d))
    procs.append(subprocess.Popen([EXE, "-c", d + "/config.toml", "-r", "e"], cwd=d, stdout=open(d + "/run.log", "w"), stderr=subprocess.STDOUT))
print([p.wait() for p in procs])
