#!/usr/bin/env python3
"""Grid twins on the physics after the melt fix (Mahrt stability and 2 m height on glaciers, multi-calib 10a0664e).

melt2: can the snow albedo make up a wrong glacier wind and cooling? Truth wind 0.8, cooling 0.65, albedoMax 0.84,
       albedoDecayRate 1.5e6; each split pins wind and cooling and runs a 6 x 6 grid of albedoMax x albedoDecayRate.
snow2: can the snowfall multipliers make up a wrong precipitation gradient? Truth precipElevGrad 0.0010, upland 1.2,
       glacier 1.4; each split pins the gradient and runs a 6 x 6 grid of the two multipliers.

Every node is one pinned trial scored against twin.py's synthetic discharge and WGMS annual mass change, so the best
fit at each split is exact. Each node keeps its yearly glacier surface grids, so further targets (the Hugonnet
thinning by HRU) can be scored offline on the same runs.

    twin2.py truth wolverine_general melt2
    twin2.py run wolverine_general melt2 --jobs 5
    twin2.py report wolverine_general melt2
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
sys.path.insert(0, os.path.join(HERE, "..", "..", "2026-11-16"))
import twin  # noqa: E402

twin.EXPERIMENTS.update({
    "melt2": {"glacierWindFactor": (0.8, 0.3, 1.5), "glacierTempReduction": (0.65, 0.5, 1.0),
              "albedoMax": (0.84, 0.8, 0.9), "albedoDecayRate": (1.5e6, 2.0e5, 5.0e6)},
    "snow2": {"precipElevGrad": (0.0010, 0.0, 0.0025), "frozenPrecipMultip@upland": (1.2, 0.2, 4.0),
              "frozenPrecipMultip@glacier": (1.4, 0.2, 4.0)},
})
SPLITS = {
    "melt2": {"truth": (0.8, 0.65), "siteB": (0.59, 0.73), "strong": (1.1, 0.55), "weak": (0.5, 0.9)},
    "snow2": {"truth": (0.0010,), "chelsa": (0.0002,), "half": (0.0005,), "steep": (0.0018,)},
}
SPLIT_PARAMS = {"melt2": ("glacierWindFactor", "glacierTempReduction"), "snow2": ("precipElevGrad",)}
GRID = {
    "melt2": (("albedoMax", [0.80, 0.82, 0.84, 0.86, 0.88, 0.90]),
              ("albedoDecayRate", [2.0e5, 4.0e5, 8.0e5, 1.5e6, 3.0e6, 5.0e6])),
    "snow2": (("frozenPrecipMultip@upland", [0.6, 0.8, 1.0, 1.2, 1.6, 2.0]),
              ("frozenPrecipMultip@glacier", [0.8, 1.0, 1.2, 1.4, 1.8, 2.4])),
}
GRIDS = ["surface_elev"]
EXPERIMENTS_TRUTH = {"melt2": (0.84, 1.5e6), "snow2": (1.2, 1.4)}  # the grid node that is the truth


def node_dir(case, exp, split, a, b):
    work, _, _ = twin.paths(case, exp)
    return os.path.join(work, f"grid_{split}", f"a{a:.6g}_b{b:.6g}")


def node_settings(case, exp):
    """The truth settings with the yearly surface grids added to the output, made once."""
    work, settings, _ = twin.paths(case, exp)
    grid_settings = os.path.join(work, "settings_grid")
    if not os.path.isdir(grid_settings):
        shutil.copytree(settings, grid_settings)
        with open(os.path.join(grid_settings, "outputControl.txt"), "a") as f:
            f.writelines(["\n"] + [f"{v:<26}| annual\n" for v in GRIDS])
    return grid_settings


def run_one(case, exp, split, a, b):
    run = node_dir(case, exp, split, a, b)
    if os.path.exists(os.path.join(run, "done")):
        return
    work, _, obs = twin.paths(case, exp)
    settings = node_settings(case, exp)
    (na, _), (nb, _) = GRID[exp]
    pinned = {k: (v, v) for k, v in zip(SPLIT_PARAMS[exp], SPLITS[exp][split])}
    pinned.update({na: (a, a), nb: (b, b)})
    text = twin.config(case, exp, run, settings, obs, 1, 1, pinned)
    text = text.replace("write_timeseries = false", "write_timeseries = true")
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
    print(f"{case} {exp} {split} {a:.6g} {b:.6g} exit {status}", flush=True)


def run(case, exp, jobs, splits):
    (_, av), (_, bv) = GRID[exp]
    tasks = [(s, a, b) for s in splits for a in av for b in bv]
    node_settings(case, exp)  # once, before the jobs share it
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda t: run_one(case, exp, *t), tasks))


def scores(case, exp, split):
    """(a, b, KGE, WGMS RMSE) of every finished node of a split."""
    (_, av), (_, bv) = GRID[exp]
    rows = []
    for a in av:
        for b in bv:
            d = node_dir(case, exp, split, a, b)
            if not os.path.exists(os.path.join(d, "done")):
                continue
            try:
                obj, names = twin.objectives(d)
            except (OSError, IndexError, ValueError):
                continue
            o = dict(zip(names, obj[0]))
            rows.append((a, b, o.get("discharge", np.nan), o.get("wgms_amce", np.nan)))
    return rows


def report(case, exp):
    (na, _), (nb, _) = GRID[exp]
    truth = twin.EXPERIMENTS[exp]
    print(f"{case} {exp}: truth " + ", ".join(f"{k} {v[0]}" for k, v in truth.items()))
    out = []
    for split, vals in SPLITS[exp].items():
        r = np.array(scores(case, exp, split), float)
        if not len(r):
            continue
        ok = np.isfinite(r[:, 2]) & np.isfinite(r[:, 3])
        r = r[ok]
        # compromise: the node nearest the ideal point, each objective scaled by its range over all splits' nodes
        dist = np.hypot((1 - r[:, 2]) / 0.1, r[:, 3] / 100.0)
        i = int(np.argmin(dist))
        bk, br = int(np.nanargmax(r[:, 2])), int(np.nanargmin(r[:, 3]))
        line = (f"{split:<7} {' '.join(f'{v:g}' for v in vals):<12} best KGE {r[bk, 2]:.4f} (rmse {r[bk, 3]:6.1f}), "
                f"best rmse {r[br, 3]:6.1f} (KGE {r[br, 2]:.4f}); compromise KGE {r[i, 2]:.4f} rmse {r[i, 3]:6.1f} "
                f"{na} {r[i, 0]:g} {nb} {r[i, 1]:g}; {len(r)} nodes")
        print(line)
        out.append([split, *vals, r[i, 2], r[i, 3], r[i, 0], r[i, 1], r[bk, 2], r[br, 3]])
    work, _, _ = twin.paths(case, exp)
    with open(os.path.join(work, "grid_report.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", *SPLIT_PARAMS[exp], "kge", "rmse", na, nb, "best_kge", "best_rmse"])
        w.writerows(out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("mode", choices=("truth", "run", "report"))
    p.add_argument("case")
    p.add_argument("experiment", choices=sorted(SPLITS))
    p.add_argument("--jobs", type=int, default=5)
    p.add_argument("--splits", nargs="+")
    a = p.parse_args()
    if a.mode == "truth":
        twin.truth(a.case, a.experiment)
    elif a.mode == "run":
        run(a.case, a.experiment, a.jobs, a.splits or list(SPLITS[a.experiment]))
    else:
        report(a.case, a.experiment)


if __name__ == "__main__":
    main()
