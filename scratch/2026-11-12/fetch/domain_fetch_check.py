#!/usr/bin/env python3
"""SUMMA's DOMfetch rule (steepest-ascent path over ice, mean of the HRU's ice cells within the narrowest of
25..1600 m of the domain elevation) in Python on a case's glacier grids, to check the Fortran.

    domain_fetch_check.py <summa_inputs> <state.nc with surface_elev> HRU:ELEV ...
"""
import sys
import numpy as np, xarray as xr

inp, state = sys.argv[1:3]
a = xr.open_dataset(f"{inp}/attributes.nc")
s = xr.open_dataset(state)
doms = [(int(h), float(z)) for h, z in (x.split(":") for x in sys.argv[3:])]
sums = {d: np.zeros(8) for d in doms}; cnts = {d: np.zeros(8) for d in doms}
wins = [25, 50, 100, 200, 400, 800, 1600, 1e5]
for g in range(a.sizes["grid"]):
    nx, ny = int(a.nx[g, 0]), int(a.ny[g, 0]); dx, dy = float(a.dx[g, 0]), float(a.dy[g, 0])
    S = s.surface_elev.values[:ny, :nx, g, 0]; B = a.bed_elev.values[:ny, :nx, g, 0]
    D = s.debris_thick.values[:ny, :nx, g, 0]; M = a.glacierMask.values[:ny, :nx, g, 0]
    H = a.cell2hruId.values[:ny, :nx, g, 0]
    ice = (M == 1) & (S - D - B > 1e-3)  # thick4area is small
    fetch = np.zeros_like(S)
    cells = np.flatnonzero(ice)
    for c in cells[np.argsort(-S.ravel()[cells], kind="stable")]:
        k, j = divmod(c, nx); best, up = 0.0, None
        for dk in (-1, 0, 1):
            for dj in (-1, 0, 1):
                kn, jn = k + dk, j + dj
                if (dk or dj) and 0 <= kn < ny and 0 <= jn < nx and ice[kn, jn]:
                    d = np.hypot(dj * dx, dk * dy); r = (S[kn, jn] - S[k, j]) / d
                    if r > best: best, up = r, (kn, jn, d)
        if up: fetch[k, j] = fetch[up[0], up[1]] + up[2]
    print(f"grid {g}: {ice.sum()} ice cells, longest fetch {fetch.max():.0f} m")
    for (h, z) in doms:
        for i, w in enumerate(wins):
            m = ice & (H == h) & (np.abs(S - z) <= w)
            sums[(h, z)][i] += fetch[m].sum(); cnts[(h, z)][i] += m.sum()
for d in doms:
    i = np.flatnonzero(cnts[d] > 0)[0]
    print(f"HRU {d[0]} at {d[1]:.0f} m: fetch {sums[d][i]/cnts[d][i]:.0f} m from {cnts[d][i]:.0f} cells within {wins[i]} m")
