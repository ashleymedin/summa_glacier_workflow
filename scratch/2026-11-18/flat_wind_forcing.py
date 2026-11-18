#!/usr/bin/env python3
"""Copy of a general case's forcing with every HRU taking the lowest HRU's wind, as the added-data forcing has one
station wind on all HRUs (the general forcing's pressure-level wind rises with HRU elevation).

    flat_wind_forcing.py wolverine_general runs/wolverine_general/forcing/flatwind
"""
import glob
import os
import shutil
import sys

import netCDF4 as nc
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
case, out = sys.argv[1], sys.argv[2]
src = open(f"{RUNS}/{case}/forcing_path.txt").read().strip()
os.makedirs(out, exist_ok=True)
for f in sorted(glob.glob(f"{src}/*.nc")):
    g = os.path.join(out, os.path.basename(f))
    shutil.copy(f, g)
    with nc.Dataset(g, "a") as d:
        u = d["windspd"][:]
        d["windspd"][:] = np.repeat(u[:, :1], u.shape[1], axis=1)
