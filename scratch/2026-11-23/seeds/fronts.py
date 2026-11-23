#!/usr/bin/env python3
"""Pareto fronts of repeated calibrations of one case: front size, hypervolume against a common reference (KGE 0, the
worst RMSE of all runs), the balanced pick of post_cal.py, a fixed-scale balanced pick (KGE and RMSE each scaled by the
union front's span) and the balanced trial's parameters; then the merged front and which run each member came from.

    fronts.py gulkana_added calibration_1120r5b calibration calibration_seed43 calibration_seed44
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np

RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs"))


def load(case, name):
    f = sorted(glob.glob(f"{RUNS}/{case}/{name}/output/*_calibration.nc"))[0]
    with nc4.Dataset(f) as d:
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)
        pars = {v: np.asarray(d[v][:]) for v, x in d.variables.items()
                if x.dimensions == ("sample",) and getattr(x, "sampled", 0) == 1}
    return obj, pars


def front(obj):
    ok = np.flatnonzero(np.isfinite(obj).all(1))
    k, m = obj[ok, 0], obj[ok, 1]
    keep = [i for i in range(len(ok)) if not np.any((k >= k[i]) & (m <= m[i]) & ((k > k[i]) | (m < m[i])))]
    return ok[keep]


def hypervolume(k, m, ref):
    o = np.argsort(-k)
    hv, best = 0.0, ref[1]
    for i in o:
        if m[i] < best:
            hv += (k[i] - ref[0]) * (best - m[i])
            best = m[i]
    return hv


def balanced(k, m, sk, sm):
    return int(np.argmin(np.hypot((k.max() - k) / sk, (m - m.min()) / sm)))


case, names = sys.argv[1], sys.argv[2:]
runs = {n: load(case, n) for n in names}
fr = {n: front(o) for n, (o, _) in runs.items()}
allk = np.concatenate([runs[n][0][fr[n], 0] for n in names])
allm = np.concatenate([runs[n][0][fr[n], 1] for n in names])
ref = (0.0, max(np.nanmax(runs[n][0][:, 1]) for n in names))
u = front(np.column_stack([allk, allm]))
sk, sm = np.ptp(allk[u]), np.ptp(allm[u])
print(f"reference KGE 0, RMSE {ref[1]:.0f}; union front KGE span {sk:.3f}, RMSE span {sm:.0f}")
for n in names:
    obj, pars = runs[n]
    i = fr[n]
    k, m = obj[i, 0], obj[i, 1]
    b = i[balanced(k, m, np.ptp(k) or 1, np.ptp(m) or 1)]
    fb = i[balanced(k, m, sk, sm)]
    print(f"{n:24s} front {len(i):2d}  HV {hypervolume(k, m, ref):7.1f}  KGE {k.min():.3f}-{k.max():.3f}  RMSE {m.min():4.0f}-{m.max():4.0f}"
          f"  balanced {b+1} ({obj[b,0]:.3f}, {obj[b,1]:.0f})  fixed-scale {fb+1} ({obj[fb,0]:.3f}, {obj[fb,1]:.0f})")
src = np.concatenate([[n] * len(fr[n]) for n in names])
smp = np.concatenate([fr[n] for n in names])
print("merged front (KGE, RMSE, run, sample):")
for j in u[np.argsort(-allk[u])]:
    print(f"  {allk[j]:.3f} {allm[j]:5.0f}  {src[j]} {smp[j]+1}")
print("balanced trials' parameters:")
pn = sorted(runs[names[0]][1])
print("  " + " ".join(f"{p[:10]:>10s}" for p in pn))
for n in names:
    obj, pars = runs[n]
    i = fr[n]
    b = i[balanced(obj[i, 0], obj[i, 1], np.ptp(obj[i, 0]) or 1, np.ptp(obj[i, 1]) or 1)]
    print(f"  {n}: " + " ".join(f"{pars[p][b]:10.3g}" if p in pars else f"{'-':>10s}" for p in pn))
