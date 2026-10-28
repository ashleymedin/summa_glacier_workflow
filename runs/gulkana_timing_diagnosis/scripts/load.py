"""Load Gulkana rerun daily outputs and the gauge into pandas frames."""
import glob, os
import numpy as np, pandas as pd, netCDF4 as nc

RUNS = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs"
DATA = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_Gulkana"
TRIALS = {"451": f"{RUNS}/gulkana_corrected/calibration_rerun/sample_451",
          "411": f"{RUNS}/gulkana_corrected/calibration_rerun/sample_411",
          "189": f"{RUNS}/gulkana_raw/pilot_rerun/sample_189"}
TOTAREA = 26.62e6  # model basin area (m2), sum of HRUarea

def obs():
    d = nc.Dataset(f"{DATA}/observations/calibration/USGS_15478040_daily_flow.nc")
    t = nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    s = pd.Series(np.array(d["q_obs"][:]), index=(pd.DatetimeIndex(t) - pd.Timedelta("1D")).normalize())
    return s.dropna()

def sim(trial):
    f = glob.glob(TRIALS[trial] + "/output/*sample000001_day.nc")[0]
    d = nc.Dataset(f)
    t = nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    idx = pd.DatetimeIndex(t).normalize() - pd.Timedelta("1D")
    out = {}
    h = nc.Dataset(glob.glob(TRIALS[trial] + "/output/*sample000001_timestep.nc")[0])
    th = pd.DatetimeIndex(nc.num2date(h["time"][:], h["time"].units, only_use_cftime_datetimes=False)) - pd.Timedelta("9h")
    out["averageRoutedRunoff"] = pd.Series(np.array(h["averageRoutedRunoff"][:, 0]), index=th).resample("1D").mean().reindex(idx)
    for v in ["glacierRoutedRunoff", "basin__SurfaceRunoff", "basin__AquiferBaseflow",
              "basin__GlacierMassChange", "basin__GlacierArea"]:
        out[v] = pd.Series(np.array(d[v + "_mean"][:, 0]), index=idx)
    dom = {}
    for v in ["scalarSWE", "scalarRainfall", "scalarSnowfall", "scalarGlacierMelt", "scalarAquiferStorage", "DOMarea"]:
        a = np.array(d[v + "_mean"][:]); a[a < -9000] = np.nan
        dom[v] = a
    dom["domType"] = np.array(d["domType"][:])
    return pd.DataFrame(out), dom, idx
