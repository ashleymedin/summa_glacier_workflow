#!/usr/bin/env python3
"""Glacier thinning by HRU from a run's yearly surface grids, and how well it separates the twin splits.

A run's rate for an HRU is the mean surface lowering (m/yr) between the first and last yearly grid, over the cells
of that HRU (cell2hruId) that are glacier at the first (surface above the bed by more than 1 m); Hugonnet et al.
(2021) average the same way over the RGI 2000 extent.

    thinning.py twin wolverine_general melt2     each split's nodes against the truth node's thinning
    thinning.py run <output dir> <case>          one run's rates
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import twin2  # noqa: E402

RUNS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "runs"))


def hru_rates(output_dir, case):
    f = [x for x in glob.glob(os.path.join(output_dir, "*_annual.nc")) if "spinup" not in x][0]
    with nc4.Dataset(f) as d:
        s = np.ma.filled(d["surface_elev"][:, :, :, 0, 0].astype(float), np.nan)
        t = nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    jan = [i for i, x in enumerate(t) if x.month == 1 and x.day == 1]  # the same season at both ends
    s, t = s[[jan[0], jan[-1]]], [t[jan[0]], t[jan[-1]]]
    years = (t[-1] - t[0]).days / 365.25
    with nc4.Dataset(os.path.join(RUNS, case, "summa_inputs", "attributes.nc")) as a:
        cell = np.ma.filled(a["cell2hruId"][:, :, 0, 0], -1)
        bed = np.ma.filled(a["bed_elev"][:, :, 0, 0].astype(float), np.nan)
        ids = np.asarray(a["hruId"][:])
    ice = (s[0] - bed) > 1.0
    rate = (s[-1] - s[0]) / years
    return {int(k): float(np.nanmean(rate[(cell == k) & ice])) for k in ids if ((cell == k) & ice).any()}


def twin(case, exp):
    (na, av), (nb, bv) = twin2.GRID[exp]
    truth = twin2.EXPERIMENTS_TRUTH[exp]
    ref = hru_rates(os.path.join(twin2.node_dir(case, exp, "truth", *truth), "output"), case)
    print(f"{case} {exp}: truth thinning by HRU (m/yr) " + ", ".join(f"{k}: {v:+.2f}" for k, v in ref.items()))
    rows = {}
    for split in twin2.SPLITS[exp]:
        sc = {(a, b): (k, r) for a, b, k, r in twin2.scores(case, exp, split)}
        best = None
        for (a, b), (kge, rmse) in sc.items():
            d = os.path.join(twin2.node_dir(case, exp, split, a, b), "output")
            try:
                r = hru_rates(d, case)
            except (IndexError, OSError):
                continue
            thin = float(np.sqrt(np.mean([(r[k] - ref[k]) ** 2 for k in ref])))
            dist = np.hypot((1 - kge) / 0.1, rmse / 100.0)
            row = (dist, kge, rmse, thin, a, b, r)
            if best is None or dist < best[0]:
                best = row
            rows.setdefault(split, []).append(row)
        if best:
            print(f"  {split:<7} compromise KGE {best[1]:.4f} WGMS rmse {best[2]:6.1f} -> thinning rmse {best[3]:.3f} m/yr "
                  f"({na} {best[4]:g}, {nb} {best[5]:g}; " + ", ".join(f"{k}: {v:+.2f}" for k, v in best[6].items()) + ")")
            good = [x for x in rows[split] if x[1] >= best[1] - 0.005 and x[2] <= best[2] + 25]
            print(f"          over the {len(good)} nodes that fit discharge and WGMS about as well: thinning rmse "
                  f"{min(x[3] for x in good):.3f}-{max(x[3] for x in good):.3f} m/yr")


def main():
    if sys.argv[1] == "twin":
        twin(sys.argv[2], sys.argv[3])
    else:
        print(hru_rates(sys.argv[2], sys.argv[3]))


if __name__ == "__main__":
    main()
