#!/usr/bin/env python3
"""Global sensitivity screen: which of a setup's searched parameters move its calibration scores at all?

  run     a Latin hypercube of --n parameter sets over the case's calibrate.py search (default domain) plus the rain-snow
          threshold and range, each run as a pinned single trial (as calibrate.py evaluate does) over the case's
          calibrate years against its real targets; --jobs at once, each on two MPI ranks
  report  per parameter and target: the Spearman rank correlation and the correlation ratio (share of the score's
          variance explained by the parameter's quintile means), each against the 95th percentile of a permutation null

Work goes to runs/<case>/screen/sample_<i>.

    screen.py run wolverine_general --n 100 --jobs 10
    screen.py report wolverine_general
"""

import argparse
import csv
import glob
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
sys.path.insert(0, RUNS)
from calibrate import (SUMMA_DIR, calibration_file, config_text, periods, pin_settings, search_for,  # noqa: E402
                       searched_names)

PHASE = {"tempCritRain": (272.16, 274.16), "tempRangeTimestep": (0.5, 5.0)}
CHAIN_GAPS = {"critSoilWilting": (0.05, 0.25), "critSoilTranspire": (0.35, 0.25), "fieldCapacity": (0.65, 0.30)}


def file_bounds(settings, name):
    base = name.split("@")[0]
    for f in ("localParamInfo.txt", "basinParamInfo.txt"):
        for line in open(os.path.join(settings, f)):
            if "|" in line and not line.lstrip().startswith("!") and line.split("|")[0].strip() == base:
                v = [float(x.strip().replace("d", "e")) for x in line.split("|")[2:4]]
                return v[0], v[1]
    raise SystemExit(f"{name}: no bounds in {settings}")


def design(case, n, seed):
    """The search with the phase parameters, and n Latin-hypercube parameter sets over it; the chain's middle members
    are drawn in order inside (theta_res, theta_sat)."""
    settings = os.path.join(RUNS, case, "summa_inputs")
    search = search_for(case, "domain")
    search = dict(search, params=list(search["params"]) + list(PHASE), bounds=dict(search["bounds"], **PHASE))
    names = searched_names(search)
    rng = np.random.default_rng(seed)
    u = (np.argsort(rng.random((n, len(names))), axis=0) + rng.random((n, len(names)))) / n
    samples = [dict() for _ in range(n)]
    for j, p in enumerate(names):
        if p.split("@")[0] in CHAIN_GAPS:
            continue
        lo, hi = search["bounds"].get(p) or file_bounds(settings, p)
        log = p in search["logs"]
        for i in range(n):
            x = np.exp(np.log(lo) + u[i, j] * (np.log(hi) - np.log(lo))) if log else lo + u[i, j] * (hi - lo)
            samples[i][p] = float(x)
    for j, p in enumerate(names):
        base, _, at = p.partition("@")
        if base in CHAIN_GAPS:
            a0, w = CHAIN_GAPS[base]
            res, sat = f"theta_res@{at}" if at else "theta_res", f"theta_sat@{at}" if at else "theta_sat"
            for i in range(n):
                lo, hi = samples[i][res], samples[i][sat]
                samples[i][p] = float(lo + (hi - lo) * (a0 + w * u[i, j]))
    return search, names, samples


def run_one(case, search, i, values, folder="screen"):
    run_dir = os.path.join(RUNS, case)
    work = os.path.join(run_dir, folder, f"sample_{i}")
    if os.path.exists(os.path.join(work, "done")):
        return
    settings = work + "_settings"
    pin_settings(os.path.join(run_dir, "summa_inputs"), settings, values)
    cal0, cal1 = periods(case)[:2]
    text = config_text(case, run_dir, settings, work, cal0, cal1, cal0, cal1, "dds", 1, 1, temperature=False,
                       search=search, pinned=values)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state"))
    open(os.path.join(work, "config.toml"), "w").write(text)
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute_opt.exe")
    with open(os.path.join(work, "run.log"), "w") as log:
        status = subprocess.run(["mpirun", "-np", "2", exe, "-c", os.path.join(work, "config.toml")],
                                stdout=log, stderr=subprocess.STDOUT).returncode
    shutil.rmtree(settings, ignore_errors=True)
    for f in glob.glob(os.path.join(work, "output", "*trialParams*.nc")):
        os.remove(f)
    open(os.path.join(work, "done"), "w").write(str(status))
    print(f"{case} sample {i} exit {status}", flush=True)


def run(case, n, jobs, seed):
    search, names, samples = design(case, n, seed)
    os.makedirs(os.path.join(RUNS, case, "screen"), exist_ok=True)
    with open(os.path.join(RUNS, case, "screen", "design.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample"] + names)
        for i, s in enumerate(samples):
            w.writerow([i] + [s[p] for p in names])
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda i: run_one(case, search, i, samples[i]), range(n)))


def scores(case):
    rows = list(csv.reader(open(os.path.join(RUNS, case, "screen", "design.csv"))))
    names, X = rows[0][1:], np.array([[float(x) for x in r[1:]] for r in rows[1:]])
    Y, targets = np.full((len(X), 2), np.nan), None
    for i in range(len(X)):
        work = os.path.join(RUNS, case, "screen", f"sample_{i}")
        try:
            with nc4.Dataset(calibration_file(work)) as d:
                Y[i] = np.ma.filled(d["objective"][0].astype(float), np.nan)[:2]
                targets = [t.strip() for t in d["objective"].target.split(",")][:2]
        except (SystemExit, OSError, KeyError):
            pass
    return names, X, Y, targets


def corr_ratio(x, y, bins=5):
    edges = np.quantile(x, np.linspace(0, 1, bins + 1))
    k = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, bins - 1)
    means = np.array([y[k == b].mean() for b in range(bins)])
    counts = np.array([(k == b).sum() for b in range(bins)])
    return float(np.sum(counts * (means - y.mean()) ** 2) / np.sum((y - y.mean()) ** 2))


def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def without(names, X, y, ok, drivers):
    """y less a full quadratic least-squares fit in the driver parameters, which otherwise mask the rest."""
    cols = [X[ok, names.index(d)] for d in drivers if d in names]
    if not cols:
        return y
    terms = [np.ones(ok.sum())] + cols + [a * b for i, a in enumerate(cols) for b in cols[i:]]
    A = np.column_stack(terms)
    return y - A @ np.linalg.lstsq(A, y, rcond=None)[0]


def report(case, perms=500, drivers=()):
    names, X, Y, targets = scores(case)
    ok = np.isfinite(Y).all(axis=1)
    print(f"{case}: {ok.sum()} of {len(X)} trials scored; targets {targets}")
    rng = np.random.default_rng(1)
    rows = []
    for t in range(2):
        y = Y[ok, t]
        if targets[t] != "discharge":
            y = np.log(y)  # RMSE spans orders of magnitude
        y = without(names, X, y, ok, drivers)
        null_r = np.quantile([abs(spearman(X[ok, 0], rng.permutation(y))) for _ in range(perms)], 0.95)
        null_e = np.quantile([corr_ratio(X[ok, 0], rng.permutation(y)) for _ in range(perms)], 0.95)
        for j, p in enumerate(names):
            rows.append((targets[t], p, spearman(X[ok, j], y), corr_ratio(X[ok, j], y), null_r, null_e))
    out = os.path.join(RUNS, case, "screen", "sensitivity" + ("_without_" + "_".join(d.split("@")[-1] for d in drivers) if drivers else "") + ".csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["target", "parameter", "spearman", "corr_ratio", "null95_spearman", "null95_corr_ratio"])
        w.writerows(rows)
    for t in targets:
        print(f"\n{t} (log RMSE)" if t != "discharge" else f"\n{t} (KGE)")
        for r in sorted([r for r in rows if r[0] == t], key=lambda r: -r[3]):
            flag = "*" if (abs(r[2]) > r[4] or r[3] > r[5]) else " "
            print(f"  {flag} {r[1]:<28} rho {r[2]:+.2f}  eta2 {r[3]:.2f}   (null {r[4]:.2f}, {r[5]:.2f})")
    best = np.nanargmax(np.where(ok, Y[:, 0], -np.inf))
    print(f"\nbest discharge trial {best}: {Y[best]}; median {np.nanmedian(Y, axis=0)}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("run", "report"))
    p.add_argument("case")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--jobs", type=int, default=10)
    p.add_argument("--seed", type=int, default=20261117)
    p.add_argument("--without", nargs="*", default=[], help="report: parameters whose quadratic effect is removed first")
    a = p.parse_args()
    if a.mode == "run":
        run(a.case, a.n, a.jobs, a.seed)
    else:
        report(a.case, drivers=a.without)


if __name__ == "__main__":
    main()
