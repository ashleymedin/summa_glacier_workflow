#!/usr/bin/env python3
"""Hypervolume of the non-dominated front of all trials born by each NSGA-II generation, per seed and merged, rounds 8 and 9.
Objectives: discharge KGE (max) and mass-balance RMSE (min); one reference point per case shared by every run, so values compare.

    hv_by_gen.py
"""
import glob
import os

import netCDF4 as nc
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs")
CASES = ["wolverine_general", "gulkana_general", "wolverine_added", "gulkana_added"]
ROUNDS = {"r8": ["calibration_1123r8", "calibration_s43_1123r8"], "r9": ["calibration", "calibration_s43"]}
REPORT = [1, 3, 5, 8, 10, 12, 15]


def load(case, name):
    f = sorted(glob.glob(os.path.join(RUNS, case, name, "output", "*_calibration.nc")))[0]
    with nc.Dataset(f) as d:
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)
        gen = np.asarray(d["birth_generation"][:])
        ok = np.isfinite(obj).all(axis=1) & (np.asarray(d["trial_failed"][:]) == 0)
    return obj[ok, 0], obj[ok, 1], gen[ok]


def hv(k, m, ref):
    """Area dominated by the points (k high, m low) and bounded by ref = (k_ref, m_ref)."""
    keep = (k > ref[0]) & (m < ref[1])
    pts = sorted(zip(-k[keep], m[keep]))  # ascending -k = descending k
    area, m_best = 0.0, ref[1]
    for i, (nk, mm) in enumerate(pts):
        m_best = min(m_best, mm)
        k_next = -pts[i + 1][0] if i + 1 < len(pts) else ref[0]
        area += (-nk - k_next) * (ref[1] - m_best)
    return area


for case in CASES:
    data = {(r, n): load(case, n) for r, names in ROUNDS.items() for n in names
            if glob.glob(os.path.join(RUNS, case, n, "output", "*_calibration.nc"))}
    allk = np.concatenate([v[0] for v in data.values()]); allm = np.concatenate([v[1] for v in data.values()])
    ref = (np.percentile(allk, 25), np.percentile(allm, 75))
    print(f"\n{case}  (reference KGE {ref[0]:.3f}, RMSE {ref[1]:.0f} mm; hypervolume in KGE x mm)")
    print(f"{'run':28s} {'trials':>6s} " + " ".join(f"g{g:>4d}" for g in REPORT))
    for r, names in ROUNDS.items():
        rows = [(n, data[(r, n)]) for n in names if (r, n) in data]
        if len(rows) == 2:
            rows.append(("merged", tuple(np.concatenate([x[i] for _, x in rows]) for i in range(3))))
        for n, (k, m, g) in rows:
            vals = [hv(k[g <= G], m[g <= G], ref) if (g <= G).any() and g.max() >= G else np.nan for G in REPORT]
            print(f"{r + ' ' + n:28s} {len(k):6d} " + " ".join(f"{v:5.1f}" for v in vals))
