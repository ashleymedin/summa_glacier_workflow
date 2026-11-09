#!/usr/bin/env python3
"""Screen whether each calibrated parameter earns its place, from a calibration's own trials.

For each searched parameter: the share of its search range the Pareto front spans (in the search space, so on a log
scale for a log parameter), and its standardized coefficient in a regression of each objective's ranks on the ranks of
every parameter and the trial's birth generation, over the trials that ran. The generation is in the regression since
NSGA-II moves every parameter toward the front together, which alone would correlate each with the scores. A parameter
whose front spans most of its range and whose coefficients are small is a candidate to fix at its default or a measured
value. Writes <case>/calibration/param_screen.csv and prints the table.

    ./param_screen.py wolverine_general wolverine_added gulkana_general gulkana_added
"""
import csv
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
from scipy.stats import rankdata

RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs"))


def screen(case, name="calibration"):
    with nc4.Dataset(sorted(glob.glob(os.path.join(RUNS, case, name, "output", "*_calibration.nc")))[0]) as d:
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)
        targets = [t.strip() for t in d["objective"].target.split(",")]
        ran = np.asarray(d["trial_failed"][:]) == 0
        front = np.asarray(d["pareto_front"][:]) == 1
        gen = np.asarray(d["birth_generation"][:], float)
        names, cols, rows = [], [], []
        for v in d.variables.values():
            if "sampled" not in v.ncattrs() or v.sampled != 1:
                continue
            x = np.asarray(v[:], float)
            lo, hi = v.lower_bound, v.upper_bound
            if v.transformation == "log":
                x, lo, hi = np.log10(x), np.log10(lo), np.log10(hi)
            span = (x[front].max() - x[front].min()) / (hi - lo) if front.any() else np.nan
            names.append(v.name)
            cols.append(x)
            rows.append({"parameter": v.name, "front_span": span})
    z = lambda a: (rankdata(a) - rankdata(a).mean()) / (rankdata(a).std() or 1.0)
    rng = np.random.default_rng(0)
    noise = {}
    for k, t in enumerate(targets):
        ok = ran & np.isfinite(obj[:, k])
        X = np.column_stack([z(c[ok]) for c in cols] + [z(gen[ok]), np.ones(ok.sum())])
        beta = np.linalg.lstsq(X, z(obj[ok, k]), rcond=None)[0]
        for r, b in zip(rows, beta):
            r[f"beta_{t}"] = b
        # the coefficient a column of no effect gets: a permuted copy of each parameter added to the regression
        null = [np.linalg.lstsq(np.column_stack([X, z(rng.permutation(c[ok]))]), z(obj[ok, k]), rcond=None)[0][-1]
                for c in cols for _ in range(5)]
        noise[t] = np.percentile(np.abs(null), 95)
    rows.sort(key=lambda r: -max(abs(r[f"beta_{t}"]) for t in targets))
    for r in rows:
        r["beyond_noise"] = any(abs(r[f"beta_{t}"]) > noise[t] for t in targets)
    with open(os.path.join(RUNS, case, name, "param_screen.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{case}: {int(ran.sum())} trials ran, front {int(front.sum())}; noise |beta| (95th pct of permuted): "
          + ", ".join(f"{t} {noise[t]:.3f}" for t in targets))
    print(f"  {'parameter':26s} {'front span':>10s} " + " ".join(f"{'beta ' + t:>20s}" for t in targets))
    for r in rows:
        print(f"  {r['parameter']:26s} {r['front_span']:10.2f} " + " ".join(f"{r['beta_' + t]:20.2f}" for t in targets)
              + ("" if r["beyond_noise"] else "   within noise"))
    return rows


if __name__ == "__main__":
    for c in sys.argv[1:]:
        screen(c)
