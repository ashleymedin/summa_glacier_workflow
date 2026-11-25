#!/usr/bin/env python3
"""The balanced front member (1-based sample) of a lemon_grus calibration folder: nearest (1 - KGE, RMSE of each balance / 500 mm) to zero among those of KGE 0.75 or more; it is linked as lemon_stream_grus/calibration_pin."""
import os, sys, numpy as np
from netCDF4 import Dataset
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../../runs"); from calibrate import HERE, calibration_file
c = os.path.join(HERE, sys.argv[1])
with Dataset(calibration_file(c)) as d:
    o = np.ma.filled(d["objective"][:].astype(float), np.nan); front = np.flatnonzero((np.asarray(d["pareto_front"][:]) == 1) & (o[:, 0] >= 0.75))
x = np.column_stack([1 - o[:, 0], o[:, 1:] / 500.0]); s = np.sqrt((x ** 2).sum(axis=1)); i = front[np.nanargmin(s[front])]
p = os.path.join(HERE, "lemon_stream_grus", "calibration_pin")
if os.path.islink(p): os.remove(p)
os.symlink(c, p); print(i + 1)
