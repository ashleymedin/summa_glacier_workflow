#!/usr/bin/env python3
"""Grid twin of the rain-snow split: can the two snowfall multipliers make up a wrong threshold or range?

The truth is twin.py's phase experiment (multipliers 0.9 upland and 1.4 glacier, threshold 273.66 K, range 3 K), made
with twin_profile.py truth. Each split pins the threshold and range and runs every node of an 8 x 8 multiplier grid
(the truth is a node) as a pinned single trial against the synthetic observations, so the best fit at each split is
exact rather than an NSGA-II estimate.

    twin_grid.py run wolverine_general --jobs 5
    twin_grid.py report wolverine_general
"""

import argparse
import csv
import glob
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-16"))
import twin  # noqa: E402

SPLITS = {"default": (273.16, 2.0), "cold1K": (272.66, 3.0), "narrow": (273.66, 1.0), "truth": (273.66, 3.0)}
UPLAND = np.round(0.30 + 0.15 * np.arange(8), 2)
GLACIER = np.round(0.80 + 0.15 * np.arange(8), 2)


def run_one(case, split, up, gl):
    work, settings, obs = twin.paths(case, "phase")
    tc, tr = SPLITS[split]
    run = os.path.join(work, f"grid_{split}", f"u{up:.2f}_g{gl:.2f}")
    if os.path.exists(os.path.join(run, "done")):
        return
    pinned = {"frozenPrecipMultip@upland": (up, up), "frozenPrecipMultip@glacier": (gl, gl),
              "tempCritRain": (tc, tc), "tempRangeTimestep": (tr, tr)}
    text = twin.config(case, "phase", run, settings, obs, 1, 1, pinned)
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "output"))
    os.makedirs(os.path.join(run, "state"))
    shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(run, "state"))
    open(os.path.join(run, "config.toml"), "w").write(text)
    exe = os.path.join(twin.SUMMA_DIR, "bin", "summa_sundials_mizuroute_opt.exe")
    with open(os.path.join(run, "run.log"), "w") as log:
        status = subprocess.run(["mpirun", "-np", "2", exe, "-c", os.path.join(run, "config.toml")],
                                stdout=log, stderr=subprocess.STDOUT).returncode
    for f in glob.glob(os.path.join(run, "output", "*trialParams*.nc")):
        os.remove(f)
    open(os.path.join(run, "done"), "w").write(str(status))
    print(f"{case} {split} {up:.2f} {gl:.2f} exit {status}", flush=True)


def run(case, jobs):
    tasks = [(s, u, g) for s in SPLITS for u in UPLAND for g in GLACIER]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda t: run_one(case, *t), tasks))


def report(case):
    work, _, _ = twin.paths(case, "phase")
    rows = []
    print(f"{case}: truth upland 0.9, glacier 1.4, threshold 273.66 K, range 3 K")
    for split, (tc, tr) in SPLITS.items():
        res = []
        for u in UPLAND:
            for g in GLACIER:
                try:
                    obj, _ = twin.objectives(os.path.join(work, f"grid_{split}", f"u{u:.2f}_g{g:.2f}"))
                    res.append((u, g, obj[0, 0], obj[0, 1]))
                    rows.append((split, tc, tr, u, g, obj[0, 0], obj[0, 1]))
                except (SystemExit, OSError):
                    pass
        if not res:
            continue
        r = np.array(res)
        k, m = np.argmax(r[:, 2]), np.argmin(r[:, 3])
        # the node nearest the ideal (KGE 1, RMSE 0) with RMSE scaled by 500 mm w.e.
        c = np.argmin(np.hypot(1 - r[:, 2], r[:, 3] / 500))
        print(f"{split:<8} {tc:.2f} K {tr:.1f} K ({len(r)} nodes): best KGE {r[k, 2]:.4f} at {r[k, 0]:.2f}/{r[k, 1]:.2f} "
              f"(rmse {r[k, 3]:.0f}); best rmse {r[m, 3]:.0f} at {r[m, 0]:.2f}/{r[m, 1]:.2f} (KGE {r[m, 2]:.4f}); "
              f"joint {r[c, 2]:.4f}/{r[c, 3]:.0f} at {r[c, 0]:.2f}/{r[c, 1]:.2f}")
    with open(os.path.join(work, "grid.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", "tempCritRain", "tempRangeTimestep", "upland", "glacier", "kge", "rmse"])
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("run", "report"))
    p.add_argument("case")
    p.add_argument("--jobs", type=int, default=5)
    a = p.parse_args()
    run(a.case, a.jobs) if a.mode == "run" else report(a.case)


if __name__ == "__main__":
    main()
