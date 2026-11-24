#!/usr/bin/env python3
"""One DDS trial of cheap_snow's setup with the gru multipliers pinned (GRU 1 x0.5, GRU 2 x1.2): the exported trialParams must change in those GRUs' glaciers only."""
import os, re, shutil, subprocess, sys, glob
import numpy as np
from netCDF4 import Dataset
R = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "runs", "lemon_grus")); exe = sys.argv[1]
d = f"{R}/gru_target"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d + "/output"); os.makedirs(d + "/state")
shutil.copy(f"{R}/summa_inputs/coldState.nc", d + "/state")
c = open(f"{R}/cheap_snow/config.toml").read().replace("/cheap_snow/", "/gru_target/")
c = re.sub(r'algorithm = "\w+"', 'algorithm = "dds"', c); c = re.sub(r"n_samples = \d+", "n_samples = 1", c)
for n, v in (("1", 0.5), ("2", 1.2)):
    c = c.replace(f'"frozenPrecipMultip@glacier_gru{n}" = {{ lower = 0.4, upper = 1.5 }}', f'"frozenPrecipMultip@glacier_gru{n}" = {{ lower = {v}, upper = {v} }}')
c = c.replace('end_date   = "2010-10-02"', 'end_date   = "2010-10-02"')
open(d + "/config.toml", "w").write(c)
print(subprocess.run(["nice", "mpirun", "-np", "2", exe, "-c", d + "/config.toml"], stdout=open(d + "/run.log", "w"), stderr=subprocess.STDOUT).returncode)
a = Dataset(f"{R}/summa_inputs/trialParams.nc")["frozenPrecipMultip"][:]
for f in sorted(glob.glob(d + "/output/*trialParams.nc")):
    b = Dataset(f)["frozenPrecipMultip"][:]; print(f[-40:]); print(np.round(np.ma.filled(b / a, np.nan), 4))
