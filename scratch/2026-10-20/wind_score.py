"""Scores of the windExposure sweep: 2016-2022 KGE and mass-balance RMSE, glacier summer melt and area."""
import glob, os
import numpy as np, xarray as xr
R = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs"
for case, s in (("gulkana_corrected", 384), ("wolverine_corrected", 469)):
    print(case, s)
    for w in ("cal", 0.45, 0.6, 0.77, 1.0):
        out = f"{R}/{case}/calibration_paper1_rerun/sample_{s}_wexp{w}/output"
        try:
            c = xr.open_dataset(f"{out}/{case}_calibration.nc")
            obj = c.objective.values.ravel()
            d = xr.open_dataset(glob.glob(f"{out}/*sample000001_day.nc")[0])
        except (FileNotFoundError, IndexError) as e:
            print(f"  {w}: missing"); continue
        wexp = float([l.split("|")[2] for l in open(f"{out}/../../sample_{s}_wexp{w}_settings/localParamInfo.txt")
                      if l.startswith("windExposure")][0])
        t = d.time.to_index()
        jja = t.month.isin([6, 7, 8]) & (t.year >= 2016)
        a = d.DOMarea_mean.fillna(0)
        melt = float(((d.scalarGlacierMelt_mean.fillna(0) * a).sum(["hru", "dom"])[jja].sum()) * 86400 / 7 / float(a.isel(time=0).sum()))
        area = d.basin__GlacierArea_mean.isel(gru=0).values
        print(f"  windExposure {wexp:.3f}: objective {np.round(obj, 3)}  JJA glacier melt {melt:.0f} mm/yr basin  "
              f"glacier area {area[0]/1e6:.2f} -> {area[-1]/1e6:.2f} km2")
