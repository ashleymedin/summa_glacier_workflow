#!/usr/bin/env python3
"""How well the calibration constrains each searched parameter: over every completed trial of a case's calibration, the
rank correlation of the parameter (log for log-searched ones) with each objective, and the spread of the best 10% of
trials (by the sum of their objective ranks) as a fraction of the search range (1 = spread over all of it).

    identifiability.py wolverine_added gulkana_added wolverine_general gulkana_general
"""
import os
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
rows = {}
for case in sys.argv[1:]:
    with nc.Dataset(f"{RUNS}/{case}/calibration/output/{case}_run0001_calibration.nc") as d:
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)
        names = ["".join(c.decode() for c in np.ma.filled(t, b"") if c) for t in d["target_name"][:]]
        ok = np.all(np.isfinite(obj), axis=1)
        if "trial_failed" in d.variables:
            ok &= np.ma.filled(d["trial_failed"][:], 0) == 0
        ranks = pd.DataFrame(obj[ok]).rank().sum(axis=1).values
        best = ranks <= np.quantile(ranks, 0.1)
        for v in d.variables.values():
            if v.dimensions != ("sample",) or "lower_bound" not in v.ncattrs():
                continue
            x = np.ma.filled(v[:].astype(float), np.nan)[ok]
            lo, hi = v.lower_bound, v.upper_bound
            if getattr(v, "transformation", "") == "log":
                x, lo, hi = np.log10(x), np.log10(lo), np.log10(hi)
            u = (x - lo) / (hi - lo)
            r = {f"r_{n[:12]}": pd.Series(u).corr(pd.Series(obj[ok][:, k]), method="spearman") for k, n in enumerate(names)}
            q = np.quantile(u[best], [0.05, 0.95])
            rows[(case, v.name)] = dict(**r, best_spread=q[1] - q[0], best_median=np.median(u[best]))
t = pd.DataFrame(rows).T
pd.set_option("display.width", 220)
print(t.round(2).to_string())
