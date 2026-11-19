#!/usr/bin/env python3
"""Yearly WGMS glacier-wide balance against the simulated one (m w.e.) for rerun folders, with the mean bias by period.

    amce_bias.py runs/gulkana_general/calibration_rerun_1119r4/sample_440_aligned ...
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from plot_setup_runs import aligned  # noqa: E402

cols = {}
for d in sys.argv[1:]:
    m = aligned(os.path.join(d, "output"))["wgms_amce"].dropna()
    cols[os.path.basename(os.path.dirname(d)) + "/" + os.path.basename(d)] = m.sim - m.obs
    cols["obs"] = m.obs
t = pd.DataFrame(cols)
t.index = t.index.year
print((t / 1000).round(2).to_string() if t.abs().max().max() > 50 else t.round(2).to_string())
for p, s in (("cal", t.index <= 2015), ("held", t.index > 2015)):
    print(p, "mean sim-obs", t[s].drop(columns="obs").mean().round(0).to_dict())
