"""Debris domain share of the glacier on 1 Jan each year, and the main-glacier debris budget from the DBRDIAG prints."""
import glob, sys, re
import numpy as np, pandas as pd, netCDF4 as nc
EXP = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/gulkana_debris_diagnosis/exp"

def share(run):
    f = glob.glob(f"{run}/output/*sample*_day.nc")[0]
    d = nc.Dataset(f)
    t = pd.DatetimeIndex(nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False))
    a = np.array(d["DOMarea_mean"][:]); a[a < -9000] = np.nan
    ty = np.array(d["domType"][:])
    dbr = np.nansum(np.where((ty == 4)[None], a, 0), axis=(1, 2)) / 1e6
    gl = np.nansum(np.where(np.isin(ty, [2, 3, 4])[None], a, 0), axis=(1, 2)) / 1e6
    s = pd.DataFrame({"debris_km2": dbr, "glacier_km2": gl}, index=t)
    s = s.groupby(s.index.year).first(); s.loc[s.index.max() + 1] = [dbr[-1], gl[-1]]
    s["share"] = s.debris_km2 / s.glacier_km2
    return s.round(2)

def budget(run):
    rows, seen = [], set()
    for line in open(f"{run}/run.log"):
        if "DBRDIAG post" in line and " 100570 " in line and line not in seen:
            seen.add(line); v = line.rsplit("=", 1)[1].split()
            if len(v) < 8: continue
            rows.append(dict(nDebris=int(v[2]), vol=float(v[3]), vEmerg=float(v[4]), vRock=float(v[5]), vClear=float(v[6]), nClear=int(v[7])))
    return pd.DataFrame(rows)

for name in sys.argv[1:]:
    run = f"{EXP}/{name}"
    print("==", name); print(share(run).T.to_string())
    b = budget(run)
    if len(b): print(b.to_string())
