#!/usr/bin/env python3
"""The multiplier glenAFactor (f_A) on Glen's rate factor a basin's ITS_LIVE speeds imply, from a run of the basin.

With no sliding the shallow-ice surface speed is linear in A at a given geometry, so a run at f_A implies
f_A * median(observed) / median(modelled) over its ice. The modelled speed is the SIA speed of each year's annual
surface (output *_annual.nc) over the run's bed (attributes.nc), on the flow grid of the basin's largest glacier, which
is the grid acquire_velocity.py fetches ITS_LIVE onto. Cells count where the ice is over --min-thick (20 m) thick and
the ITS_LIVE error under --max-err (10 m yr-1). A year counts only where the median observed speed over the ice is at
least --min-ratio (2.5) times the median on the ice-free cells within 400 m of it, the speed the mosaic shows where
nothing moves; each observed speed has that noise floor taken off in quadrature. The pooled ratio over the years that
count gives the implied f_A, if at least --min-years (3) count. A geometry evolves with A, so rerun at the implied value until it implies itself (one
step is usually within 10%). A basin with too few years that count prints none and takes the region's value.

    ./glen_factor.py runs/wolverine_general data/domain_Wolverine/observations/storage/velocity/itslive_annual.npz
"""

import argparse
import glob
import os
import re

import netCDF4 as nc4
import numpy as np
from scipy.ndimage import distance_transform_edt

A0, N, RHO, G, YR = 2.4e-24, 3, 917.0, 9.80616, 365.25 * 86400


def run_f_a(settings):
    """The run's glenAFactor from its basinParamInfo.txt (1 when it is not listed, SUMMA's fallback)."""
    with open(os.path.join(settings, "basinParamInfo.txt")) as f:
        for line in f:
            if line.split("|")[0].strip() == "glenAFactor":
                return float(line.split("|")[1])
    return 1.0


def model_speeds(run, settings):
    """{water year: (SIA speed at the run's f_A in m yr-1, ice thickness)} on the largest glacier's grid, and its mask."""
    with nc4.Dataset(os.path.join(settings, "attributes.nc")) as d:
        nx, ny = np.asarray(d["nx"][:, 0]).astype(int), np.asarray(d["ny"][:, 0]).astype(int)
        g = int(np.argmax(nx * ny))
        bed = np.asarray(d["bed_elev"][:ny[g], :nx[g], g, 0], float)
        mask = np.asarray(d["glacierMask"][:ny[g], :nx[g], g, 0]) == 1
        dx = float(np.asarray(d["dx"][:]).flat[0])
    f_a, out = run_f_a(settings), {}
    for path in sorted(glob.glob(os.path.join(run, "output", "*_annual.nc"))):
        if "spinup" in os.path.basename(path):
            continue
        with nc4.Dataset(path) as d:
            times = nc4.num2date(d["time"][:], d["time"].units)
            for i, t in enumerate(times):
                s = np.asarray(d["surface_elev"][i, :ny[g], :nx[g], g, 0], float)
                h = np.where(mask, np.maximum(s - np.asarray(d["debris_thick"][i, :ny[g], :nx[g], g, 0], float) - bed, 0), 0)
                gy, gx = np.gradient(s, dx)
                u = 2 * A0 * f_a / (N + 1) * (RHO * G) ** N * h ** (N + 1) * np.hypot(gx, gy) ** N * YR
                out[t.year - 1 if (t.month, t.day) == (1, 1) else t.year] = (u, h)
    return f_a, out, mask, dx


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("run", help="run folder with output/*_annual.nc")
    p.add_argument("velocity", help="itslive_annual.npz of acquire_velocity.py")
    p.add_argument("--settings", help="folder with attributes.nc and basinParamInfo.txt (default <run>_settings, else <run>/summa_inputs)")
    p.add_argument("--min-thick", type=float, default=20.0)
    p.add_argument("--max-err", type=float, default=10.0)
    p.add_argument("--min-ratio", type=float, default=2.5)
    p.add_argument("--min-years", type=int, default=3)
    a = p.parse_args()
    settings = a.settings or next(s for s in (a.run.rstrip("/") + "_settings", os.path.join(a.run, "summa_inputs")) if os.path.isdir(s))
    f_a, model, mask, dx = model_speeds(a.run, settings)
    o = np.load(a.velocity)
    ground = ~mask & (distance_transform_edt(~mask) * dx <= 400.0)
    obs, mod = [], []
    print(f"{a.run}: run at f_A {f_a:g}\n year  ground  ice obs  ice model  ratio  used")
    for i, y in enumerate(o["years"]):
        if int(y) not in model:
            continue
        u, h = model[int(y)]
        v, e = o["v"][i], o["v_error"][i]
        ok = (h > a.min_thick) & np.isfinite(v) & (e < a.max_err)
        floor = np.nanmedian(v[ground & np.isfinite(v)])
        used = ok.any() and np.median(v[ok]) >= a.min_ratio * floor
        if used:
            obs.append(np.sqrt(np.maximum(v[ok] ** 2 - floor ** 2, 0)))
            mod.append(u[ok])
        print(f" {int(y)}  {floor:6.1f}  {np.median(v[ok]) if ok.any() else np.nan:7.1f}  {np.median(u[ok]) if ok.any() else np.nan:9.1f}"
              f"  {np.median(v[ok]) / floor if ok.any() else np.nan:5.1f}  {'yes' if used else 'no'}")
    if len(obs) < a.min_years:
        print(f"implied f_A: none ({len(obs)} years above the noise floor); take the region's value")
        return
    obs, mod = np.concatenate(obs), np.concatenate(mod)
    print(f"implied f_A: {f_a * np.median(obs) / np.median(mod):.2f} over {len(obs)} cell-years")


if __name__ == "__main__":
    main()
