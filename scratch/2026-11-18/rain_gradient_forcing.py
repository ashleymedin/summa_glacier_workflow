#!/usr/bin/env python3
"""Copy of an added-data case's station-corrected forcing with the stakes' precipitation gradient carried above the top gauge
outside the stake intervals, where the gauges alone set the precipitation (mostly summer rain).

Each HRU above the highest gauge has pptrate x (1 + gamma (z_hru - z_gauge) (1 - w_m)), with gamma the case's precipElevGrad
and w_m the month's stake-snowfall weight from corrections.csv (1 in winter, where the stake ratios already set the snowfall).

    rain_gradient_forcing.py wolverine_added 990 runs/wolverine_added/forcing/raingrad
    rain_gradient_forcing.py gulkana_added 1725 runs/gulkana_added/forcing/raingrad
"""
import csv
import glob
import os
import re
import shutil
import sys

import netCDF4 as nc
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
case, z_gauge, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
src = open(f"{RUNS}/{case}/forcing_path.txt").read().strip()
gamma = float(re.search(r"^precipElevGrad\s*\|\s*([\d.eE+-]+)", open(f"{RUNS}/{case}/summa_inputs/localParamInfo.txt").read(), re.M).group(1))
rows = list(csv.reader(open(f"{src}/corrections.csv")))
z = np.array([float(r[1]) for r in rows[1:] if r and r[0].isdigit()])
w = np.array([float(x) for x in next(r for r in rows if r and r[0] == "pptrate_stake_snowfall_weight")[1:13]])
mult = 1 + gamma * np.maximum(0.0, z - z_gauge)[None, :] * (1 - w)[:, None]  # (month, hru)
print(f"gamma {gamma}, HRU elevations {np.round(z)}; JJA multipliers {np.round(mult[5:8].mean(0), 3)}")
os.makedirs(out, exist_ok=True)
for f in sorted(glob.glob(f"{src}/*.nc")):
    g = os.path.join(out, os.path.basename(f))
    shutil.copy(f, g)
    m = int(re.search(r"(\d{6})\.nc$", f).group(1)[4:])
    with nc.Dataset(g, "a") as d:
        d["pptrate"][:] = d["pptrate"][:] * mult[m - 1][None, :]
shutil.copy(f"{src}/corrections.csv", out)
