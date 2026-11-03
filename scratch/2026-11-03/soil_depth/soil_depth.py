#!/usr/bin/env python3
"""Upland soil depth test on wolverine_general at default parameters: 8 upland soil layers to 1, 2 or 4 m.

Each depth starts from the case's spun-up state with its upland layers resized, cycles WY2005 --cycles times, then runs
WY2006-2015 with hourly output. Run one depth per process:

    ./soil_depth.py run 1     (then 2, 4)
    ./soil_depth.py score
"""

import datetime
import glob
import os
import re
import shutil
import subprocess
import sys
import time

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "../../.."))
sys.path.insert(0, os.path.join(WF, "runs"))
from calibrate import SUMMA_DIR, config_text  # noqa: E402

CASE = "wolverine_general"
PROFILES = {1: [0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.2, 0.2],
            2: [0.025, 0.075, 0.15, 0.25, 0.25, 0.35, 0.4, 0.5],
            4: [0.025, 0.075, 0.15, 0.25, 0.5, 0.5, 1.0, 1.5]}
CYCLES = 10


def resize(path, dz):
    """Upland domains (no glacier ice) take the thicknesses dz for their top 8 soil layers below any snow; the
    thermal-only bedrock layers under them keep their bottom, the first taking up the change."""
    with nc4.Dataset(path, "r+") as d:
        ns, nsn, ng = (np.asarray(d[k][:]).reshape(d[k].shape[-2:]) for k in ("nSoil", "nSnow", "nGlce"))
        depth, height = d["mLayerDepth"][:], d["iLayerHeight"][:]
        for h, j in zip(*np.nonzero((ns >= 8) & (ng == 0))):
            k, n = int(nsn[h, j]), int(ns[h, j])
            change = float(np.sum(depth[k:k + 8, h, j])) - float(np.sum(dz))
            depth[k:k + 8, h, j] = dz
            height[k + 1:k + 9, h, j] = np.cumsum(dz)
            if n > 8:
                depth[k + 8, h, j] += change
            print(f"hru {h} dom {j}: soil {np.sum(dz):g} m, column to {float(np.sum(depth[k:k + n, h, j])):.1f} m")
        d["mLayerDepth"][:], d["iLayerHeight"][:] = depth, height


def summa(work, config):
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(config)
    with open(os.path.join(work, "run.log"), "w") as log:
        return subprocess.run([os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute.exe"), "-c",
                               os.path.join(work, "config.toml"), "-r", "e"], cwd=work, stdout=log, stderr=subprocess.STDOUT).returncode


def toml(run_dir, settings, work, start, end, write):
    c = config_text(CASE, run_dir, settings, work, start, end, start, end, "dds", 1, 1, temperature=False)
    c = c[:c.index("\n[calibration]")]
    c = re.sub(r"^use_mizuroute .*", "use_mizuroute    = false", c, flags=re.M)
    return re.sub(r"^write_timeseries .*", f"write_timeseries = {'true' if write else 'false'}", c, flags=re.M)


def run(depth):
    src = os.path.join(WF, "runs", CASE)
    run_dir = os.path.join(HERE, f"d{depth}m")
    shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(os.path.join(src, "summa_inputs"), os.path.join(run_dir, "summa_inputs"))
    shutil.copy(os.path.join(src, "forcing_path.txt"), run_dir)
    settings = os.path.join(run_dir, "summa_inputs")
    resize(os.path.join(settings, "coldState.nc"), PROFILES[depth])
    spin, main = os.path.join(run_dir, "spin"), os.path.join(run_dir, "main")
    for w in (spin, main):
        os.makedirs(os.path.join(w, "output"))
        os.makedirs(os.path.join(w, "state"))
    config = toml(run_dir, settings, spin, "2004-10-01", "2005-09-30", False)
    current = os.path.join(settings, "coldState.nc")
    for k in range(CYCLES):
        for f in glob.glob(os.path.join(spin, "state", "*")) + glob.glob(os.path.join(spin, "output", "*")):
            os.remove(f)
        shutil.copy(current, os.path.join(spin, "state", "coldState.nc"))
        if summa(spin, config):
            raise SystemExit(f"{depth} m: spin-up cycle {k + 1} failed; see {spin}/run.log")
        restart = sorted(glob.glob(os.path.join(spin, "*", "*restart*.nc")))[-1]
        current = os.path.join(run_dir, f"cycle_{k % 2}.nc")
        shutil.copy(restart, current)
    shutil.copy(current, os.path.join(main, "state", "coldState.nc"))
    t0 = time.time()
    status = summa(main, toml(run_dir, settings, main, "2005-10-01", "2015-09-30", True))
    print(f"{depth} m: WY2006-2015 {'failed' if status else 'done'} in {(time.time() - t0) / 3600:.2f} h")


def kge(s, o):
    return 1 - np.sqrt((np.corrcoef(s, o)[0, 1] - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)


def score():
    with nc4.Dataset(os.path.join(WF, "data/domain_Wolverine/observations/calibration/USGS_15236900_daily_flow.nc")) as d:
        t = nc4.num2date(d["time"][:], d["time"].units)
        obs = {(x.year, x.month, x.day): float(q) for x, q in zip(t, d["q_obs"][:]) if np.isfinite(q)}
    print("depth  KGE    mean obs/sim   Oct-Nov obs/sim   Apr-May obs/sim   Jun-Aug obs/sim (m3 s-1)   summer peak, days from 1 May, obs/sim")
    for depth in sorted(PROFILES):
        main = os.path.join(HERE, f"d{depth}m", "main")
        files = [f for f in glob.glob(os.path.join(main, "output", "*timestep*.nc"))]
        if not files:
            continue
        with nc4.Dataset(os.path.join(HERE, f"d{depth}m", "summa_inputs", "attributes.nc")) as a:
            area = float(np.sum(a["HRUarea"][:]))
        with nc4.Dataset(files[0]) as d:
            tt = nc4.num2date(d["time"][:], d["time"].units)
            q = np.asarray(d["averageRoutedRunoff"][:]).reshape(len(tt), -1)[:, 0] * area
        days = {}
        for x, v in zip(tt, q):
            x = x - datetime.timedelta(hours=9, seconds=1)  # gauge days are UTC-9, values stamped at the hour's end
            days.setdefault((x.year, x.month, x.day), []).append(v)
        keys = [k for k in days if k in obs and len(days[k]) == 24]
        s = np.array([np.mean(days[k]) for k in keys]); o = np.array([obs[k] for k in keys])
        m = np.array([k[1] for k in keys])
        w, sp, su = np.isin(m, (10, 11)), np.isin(m, (4, 5)), np.isin(m, (6, 7, 8))
        doy = lambda v: np.mean([np.argmax([v[i] for i, k in enumerate(keys) if k[0] == y and k[1] in (5, 6, 7, 8, 9, 10)]) for y in range(2006, 2016)])
        print(f"{depth} m   {kge(s, o):.2f}   {o.mean():5.2f}/{s.mean():5.2f}    {o[w].mean():5.2f}/{s[w].mean():5.2f}      {o[sp].mean():5.2f}/{s[sp].mean():5.2f}       "
              f"{o[su].mean():5.2f}/{s[su].mean():5.2f}                {doy(o):5.0f}/{doy(s):5.0f}")


if __name__ == "__main__":
    run(int(sys.argv[2])) if sys.argv[1] == "run" else score()
