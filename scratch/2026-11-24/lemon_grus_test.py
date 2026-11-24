#!/usr/bin/env python3
"""Run Lemon Creek WY2006-WY2026 at the default parameters on the white-ice SUMMA: one (lemon_added as built), equal (lemon_grus, one k) and
length (lemon_grus, k by glacier length). Runs in runs/lemon_grus/test/<name>; lemon_added is only read."""
import os, re, shutil, subprocess, sys
from netCDF4 import Dataset
W = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EXE = os.path.expanduser("~/Research/SummaSundials/summa_wetprecip/bin/summa_sundials_mizuroute.exe")
procs = []
for name, case in (("one", "lemon_added"), ("equal", "lemon_grus"), ("length", "lemon_grus"), ("flat", "lemon_grus")):
    if name not in (sys.argv[1:] or ("one", "equal", "length")): continue
    d = f"{W}/runs/lemon_grus/test/{name}"; shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d + "/output"); os.makedirs(d + "/state")
    src = f"{W}/runs/lemon_added/default/settings" if name == "one" else f"{W}/runs/lemon_grus/summa_inputs"
    shutil.copytree(src, d + "/settings")
    shutil.copy(f"{W}/runs/lemon_added/default/settings/outputControl.txt", d + "/settings/outputControl.txt")
    shutil.copy(d + "/settings/coldState.nc", d + "/state/coldState.nc")
    if name == "equal":  # back to basinParamInfo.txt's one k
        with Dataset(d + "/settings/trialParams.nc", "a") as t:
            for v, k in (("glacStor_kIce", 54e3), ("glacStor_kSnow", 324e3), ("glacStor_kFirn", 2070e3)): t[v][:] = k
    c = open(f"{W}/runs/lemon_added/default/config.toml").read().replace(f"{W}/runs/lemon_added/default", d)
    if case == "lemon_grus": c = c.replace("data/domain_LemonCreek/", "data/domain_LemonCreek_grus/").replace('case_name = "lemon_added"', 'case_name = "lemon_grus"')
    open(d + "/config.toml", "w").write(c)
    procs.append(subprocess.Popen([EXE, "-c", d + "/config.toml", "-r", "e"], cwd=d, stdout=open(d + "/run.log", "w"), stderr=subprocess.STDOUT))
print([p.wait() for p in procs])
