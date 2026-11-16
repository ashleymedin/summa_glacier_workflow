#!/usr/bin/env python3
"""Calibrate a setup over its calibrate.py domain search plus the rain-snow threshold and range, then sweep each
parameter one at a time from the calibrated compromise to its lower and upper bound: which parameters move the
scores near a good fit?

  calibrate  NSGA-II (--population x --generations) into runs/<case>/calibration_phase
  sweep      the front member nearest the ideal after scaling each objective by its front range, then that member with
             each parameter at its lower and at its upper bound, each a pinned single trial in runs/<case>/oat/<name>
  report     each parameter's change of each score from the compromise at its two bounds

    oat.py calibrate wolverine_general --ranks 10
    oat.py sweep wolverine_general --jobs 9
    oat.py report wolverine_general
"""

import argparse
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import screen  # noqa: E402
from screen import RUNS, PHASE, file_bounds  # noqa: E402
from calibrate import calibration_file, config_text, periods, run_driver, search_for, searched_names  # noqa: E402

CHAIN = ("theta_res", "critSoilWilting", "critSoilTranspire", "fieldCapacity", "theta_sat")


def search(case):
    s = search_for(case, "domain")
    return dict(s, params=list(s["params"]) + list(PHASE), bounds=dict(s["bounds"], **PHASE))


def calibrate(case, population, generations, ranks):
    run_dir = os.path.join(RUNS, case)
    settings = os.path.join(run_dir, "summa_inputs")
    work = os.path.join(run_dir, "calibration_phase")
    cal0, cal1 = periods(case)[:2]
    text = config_text(case, run_dir, settings, work, cal0, cal1, cal0, cal1, "nsga2", population * generations,
                       population, temperature=False, search=search(case))
    run_driver(work, text, settings, ranks)


def compromise(case):
    path = calibration_file(os.path.join(RUNS, case, "calibration_phase"))
    with nc4.Dataset(path) as d:
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)
        front = (np.asarray(d["pareto_front"][:]) == 1) & np.isfinite(obj).all(axis=1)
        names = [n for n in searched_names(search(case)) if n in d.variables]
        f = obj[front]
        span = np.maximum(np.ptp(f, axis=0), 1e-9)
        i = np.flatnonzero(front)[np.argmin(np.hypot((f[:, 0].max() - f[:, 0]) / span[0], (f[:, 1] - f[:, 1].min()) / span[1]))]
        return {n: float(d[n][i]) for n in names}, obj[i]


def variants(case):
    """(name, values): the compromise, then each parameter at each bound; a chain member moves only inside its
    neighbours, by at least 0.03."""
    base, _ = compromise(case)
    s = search(case)
    settings = os.path.join(RUNS, case, "summa_inputs")
    out = [("compromise", base)]
    for p in base:
        b, _, at = p.partition("@")
        lo, hi = s["bounds"].get(p) or file_bounds(settings, p)
        if b in CHAIN:
            k = CHAIN.index(b)
            near = lambda j: base.get(f"{CHAIN[j]}@{at}" if at else CHAIN[j])  # noqa: E731
            if k > 0:
                lo = max(lo, near(k - 1) + 0.03)
            if k < len(CHAIN) - 1:
                hi = min(hi, near(k + 1) - 0.03)
        for tag, v in (("lo", lo), ("hi", hi)):
            out.append((f"{p}_{tag}", dict(base, **{p: float(v)})))
    return out


def sweep(case, jobs):
    s = search(case)
    vs = variants(case)
    with open(os.path.join(RUNS, case, "oat_variants.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant"] + list(vs[0][1]))
        w.writerows([[n] + list(v.values()) for n, v in vs])
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda nv: screen.run_one(case, s, nv[0], nv[1], folder="oat"), vs))


def report(case):
    vs = variants(case)
    res = {}
    for n, _ in vs:
        try:
            with nc4.Dataset(calibration_file(os.path.join(RUNS, case, "oat", f"sample_{n}"))) as d:
                res[n] = np.ma.filled(d["objective"][0].astype(float), np.nan)[:2]
                targets = [t.strip() for t in d["objective"].target.split(",")][:2]
        except (SystemExit, OSError):
            res[n] = np.array([np.nan, np.nan])
    base_vals, cal_obj = compromise(case)
    c = res["compromise"]
    print(f"{case}: compromise {targets[0]} {c[0]:.4f}, {targets[1]} {c[1]:.1f} (calibration file {cal_obj})")
    rows = []
    for p in base_vals:
        lo, hi = res[f"{p}_lo"], res[f"{p}_hi"]
        dk = np.nanmax(np.abs([lo[0] - c[0], hi[0] - c[0]]))
        dm = np.nanmax(np.abs([lo[1] - c[1], hi[1] - c[1]]))
        rows.append((p, base_vals[p], lo[0] - c[0], hi[0] - c[0], lo[1] - c[1], hi[1] - c[1], dk, dm))
    rows.sort(key=lambda r: -(r[6] / 0.05 + r[7] / max(c[1], 1) / 0.25))
    with open(os.path.join(RUNS, case, "oat_report.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["parameter", "compromise", f"d{targets[0]}_lo", f"d{targets[0]}_hi", f"d{targets[1]}_lo", f"d{targets[1]}_hi"])
        w.writerows([r[:6] for r in rows])
    print(f"{'parameter':<28}{'value':>11}{'dKGE lo':>9}{'dKGE hi':>9}{'dRMSE lo':>10}{'dRMSE hi':>10}")
    for r in rows:
        print(f"{r[0]:<28}{r[1]:>11.4g}{r[2]:>+9.3f}{r[3]:>+9.3f}{r[4]:>+10.1f}{r[5]:>+10.1f}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("calibrate", "sweep", "report"))
    p.add_argument("case")
    p.add_argument("--population", type=int, default=32)
    p.add_argument("--generations", type=int, default=15)
    p.add_argument("--ranks", type=int, default=10)
    p.add_argument("--jobs", type=int, default=9)
    a = p.parse_args()
    if a.mode == "calibrate":
        calibrate(a.case, a.population, a.generations, a.ranks)
    elif a.mode == "sweep":
        sweep(a.case, a.jobs)
    else:
        report(a.case)


if __name__ == "__main__":
    main()
