#!/usr/bin/env python3
"""Calibration / held-out scores of a balanced trial's aligned reruns, as Figs 3-4 label them: discharge KGE and the RMSE (mm)
of each mass-balance target.

    scores.py gulkana_general calibration_rerun_1120r5b 471
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
from plot_setup_runs import kge, rmse, split, trial  # noqa: E402

case, name, sample = sys.argv[1:4]
_, ev = trial(case, name, sample)
for t, df in ev.items():
    c, h = split(df, kge if t == "discharge" else rmse)
    print(f"{case} {sample} {t}: {c:.3f} / {h:.3f}")
