#!/usr/bin/env python3
"""Discharge KGE and seasonal and WGMS RMSE (calibration / held-out years) of rerun output folders, with their KGE parts.

    score.py runs/gulkana_added/calibration_rerun_1118r3/sample_467_aligned ...
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from plot_setup_runs import aligned  # noqa: E402


def kge(x):
    return 1 - np.sqrt((x.obs.corr(x.sim) - 1) ** 2 + (x.sim.std() / x.obs.std() - 1) ** 2 + (x.sim.mean() / x.obs.mean() - 1) ** 2)


def rmse(x):
    return np.sqrt(((x.sim - x.obs) ** 2).mean())


for d in sys.argv[1:]:
    al = aligned(os.path.join(d, "output"))
    q = al[[k for k in al if k.startswith("discharge")][0]].dropna()
    c, h = q.index < "2015-10-01", q.index >= "2015-10-01"
    line = f"{os.path.basename(d):24s} KGE {kge(q[c]):.3f}/{kge(q[h]):.3f} (r {q.obs.corr(q.sim):.2f} a {q.sim.std() / q.obs.std():.2f} b {q.sim.mean() / q.obs.mean():.2f})"
    for t in ("mass_balance", "wgms_amce"):
        if t in al:
            m = al[t].dropna()
            line += f"  {t} {rmse(m[m.index < '2015-10-01']):.0f}/{rmse(m[m.index >= '2015-10-01']):.0f}"
    print(line)
