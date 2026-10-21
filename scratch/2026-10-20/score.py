"""2016-2022 KGE, mass-balance RMSE and mean net balance of reruns: score.py <label prefix> <values...>."""
import glob, sys
import numpy as np, xarray as xr
R = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs"
SURVEY = {"gulkana_corrected": -979, "wolverine_corrected": -1105}   # mm w.e. a year, 2016-2022
pre, vals = sys.argv[1], sys.argv[2:]
for case, s in (("gulkana_corrected", 384), ("wolverine_corrected", 469)):
    print(f"{case} {s} (survey net {SURVEY[case]} mm/yr)")
    for v in vals:
        out = f"{R}/{case}/calibration_paper1_rerun/sample_{s}_{pre}{v}/output"
        try:
            obj = xr.open_dataset(f"{out}/{case}_calibration.nc").objective.values.ravel()
            d = xr.open_dataset(glob.glob(f"{out}/*sample000001_day.nc")[0])
        except (FileNotFoundError, IndexError, OSError):
            print(f"  {v}: missing"); continue
        m = d.basin__GlacierMassChange_mean.isel(gru=0).to_series().loc["2016":"2022"]
        print(f"  {pre}{v}: KGE {obj[0]:.3f}  MB RMSE {obj[1]:.0f} mm  net {m.mean() * 86400 * 365.25:.0f} mm/yr")
