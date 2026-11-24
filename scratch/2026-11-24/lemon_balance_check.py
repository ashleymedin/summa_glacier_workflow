#!/usr/bin/env python3
"""Seasonal balances of the default runs against the stakes, computed here: cumulative mass change between the observed extremes' neighbourhoods (60 days)."""
import netCDF4 as nc, numpy as np, glob, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
o = nc.Dataset("data/domain_LemonCreek/observations/calibration/lemoncreek_mass_balance_seasonal.nc")
b = np.array(o["time_bnds"][:]); v = np.ma.filled(o["mb_obs"][:], np.nan); day = lambda m: np.datetime64("1950-01-01") + (m // 1440).astype("timedelta64[D]")
for n, g in (("one", 0), ("flat", 2), ("flat", 0), ("flat", 1)):
    d = nc.Dataset(glob.glob(f"runs/lemon_grus/test/{n}/output/*_day.nc")[0]); t = np.array([np.datetime64(x, "D") for x in nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)])
    c = np.cumsum(np.ma.filled(d["basin__GlacierMassChange_mean"][:], 0)[:, g] * 86400)
    def ext(x, hi):
        w = np.abs(t - x) <= np.timedelta64(60, "D"); return (c[w].max() if hi else c[w].min()) if w.sum() > 60 else np.nan
    W, S = [], []
    for (a, z), y in zip(b, v):
        A, Z = day(np.array(a)), day(np.array(z))
        if A < np.datetime64("2005-10-01") - np.timedelta64(30, "D") or not np.isfinite(y): continue
        s = ext(Z, y > 0) - ext(A, y < 0)
        if np.isfinite(s): (W if y > 0 else S).append((s, y, str(Z)[:4]))
    W, S = np.array([x[:2] for x in W]), np.array([x[:2] for x in S])
    print(f"{n} GRU index {g}: winter {W.mean(0).round(0)}, summer {S.mean(0).round(0)} (model, stakes); RMSE winter {np.sqrt(((W[:,0]-W[:,1])**2).mean()):.0f} summer {np.sqrt(((S[:,0]-S[:,1])**2).mean()):.0f} all {np.sqrt((np.r_[W[:,0]-W[:,1], S[:,0]-S[:,1]]**2).mean()):.0f}; first five winters", W[:5].round(0).tolist(), "summers", S[:5].round(0).tolist())
