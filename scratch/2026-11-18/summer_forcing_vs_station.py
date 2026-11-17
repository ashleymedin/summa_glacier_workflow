#!/usr/bin/env python3
"""Each stake summer's balance error against the forcing and the off-glacier weather station over the same window.

    summer_forcing_vs_station.py wolverine_added:472:990 gulkana_added:468:1480

For each summer (spring stake date to fall stake date, from the rerun's aligned pairs over WY2006-2026): the
simulated minus observed summer balance; positive degree-days and summer precipitation at the station, and in the
forcing at the HRU nearest the station's elevation, lapsed to it at 6.5 K/km; the forcing's mean shortwave. Then the
correlation of the error with each, and with the forcing-minus-station PDD.
"""
import glob
import os
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, WF)
from plot_setup_runs import aligned  # noqa: E402

DOMAIN = {"wolverine": "Wolverine", "gulkana": "Gulkana"}


def station(basin, elev):
    """Daily mean temperature (C) and precipitation (mm) at a station, UTC days."""
    frames = []
    for f in sorted(glob.glob(f"{WF}/data/domain_{DOMAIN[basin]}/observations/stations/{elev}/LVL2/*.csv")):
        d = pd.read_csv(f, na_values=["NA", "", "NaN"])
        tcol = next((c for c in ("site_temp", "site_temp_USGS", "site_temp_WMO") if c in d), None)
        pcol = next((c for c in ("Precip_Weighing_Incremental", "Precip_Stage_Incremental") if c in d), None)
        if tcol is None or "UTC_time" not in d:  # daily summaries carry no UTC clock
            continue
        frames.append(pd.DataFrame({"T": pd.to_numeric(d[tcol], errors="coerce").values,
                                    "P": pd.to_numeric(d[pcol], errors="coerce").values if pcol else np.nan},
                                   index=pd.to_datetime(d["UTC_time"], format="mixed")))
    s = pd.concat(frames).sort_index()
    s = s[~s.index.duplicated()]
    s.loc[(s["T"] < -60) | (s["T"] > 40), "T"] = np.nan
    s.loc[(s["P"] < 0) | (s["P"] > 100), "P"] = np.nan
    hr = pd.DataFrame({"T": s["T"].resample("1h").mean(), "P": s["P"].resample("1h").sum(min_count=1)})
    day = pd.DataFrame({"T": hr["T"].resample("1D").mean(), "P": hr["P"].resample("1D").sum(min_count=18)})
    day.loc[hr["T"].resample("1D").count() < 18, "T"] = np.nan  # days mostly missing
    return day


def forcing(case, elev):
    """Daily T (C, lapsed to the station), precipitation (mm) and shortwave (W m-2) at the HRU nearest the station."""
    path = open(f"{WF}/runs/{case}/forcing_path.txt").read().strip() if os.path.exists(f"{WF}/runs/{case}/forcing_path.txt") else None
    a = nc.Dataset(f"{WF}/runs/{case}/summa_inputs/attributes.nc")
    z = np.asarray(a["elevation"][:], float)
    i = int(np.argmin(np.abs(z - elev)))
    files = sorted(glob.glob(os.path.join(path, "*.nc")))
    parts = []
    for f in files:
        with nc.Dataset(f) as d:
            t = pd.to_datetime(nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                           only_use_python_datetimes=True))
            parts.append(pd.DataFrame({"T": d["airtemp"][:, i] - 273.15 + 0.0065 * (z[i] - elev),
                                       "P": d["pptrate"][:, i] * 3600, "SW": d["SWRadAtm"][:, i]}, index=t))
    h = pd.concat(parts).sort_index()
    return h.resample("1D").agg({"T": "mean", "P": "sum", "SW": "mean"}), z[i]


for spec in sys.argv[1:] if __name__ == "__main__" else []:
    case, sample, elev = spec.split(":")
    basin, elev = case.split("_")[0], int(elev)
    mb = aligned(f"{WF}/runs/{case}/calibration_rerun/sample_{sample}_aligned/output")["mass_balance"]
    st = station(basin, elev)
    fo, zh = forcing(case, elev)
    rows = []
    dates = list(mb.index)
    for k in range(1, len(dates)):
        a, b = dates[k - 1], dates[k]
        if not (3 <= a.month <= 6 and 7 <= b.month <= 10 and (b - a).days < 200):
            continue  # a summer: spring date to fall date
        w = slice(a.normalize(), b.normalize())
        s, f = st.loc[w], fo.loc[w]
        cover = s["T"].notna().mean()
        rows.append({"summer": b.year, "days": (b - a).days, "err": mb.sim[b] - mb.obs[b], "obs": mb.obs[b],
                     "pdd_st": s["T"].clip(lower=0).sum() / cover if cover > 0.8 else np.nan,
                     "pdd_fo": f["T"].clip(lower=0).sum(),
                     "P_st": s["P"].sum() / s["P"].notna().mean() if s["P"].notna().mean() > 0.8 else np.nan, "P_fo": f["P"].sum(),
                     "SW_fo": f["SW"].mean()})
    df = pd.DataFrame(rows).set_index("summer")
    df["pdd_diff"] = df.pdd_fo - df.pdd_st
    print(f"== {case} {sample}: station {elev} m, forcing HRU at {zh:.0f} m lapsed to it")
    print(df.round(0).to_string())
    print("  correlation of the summer error with:")
    for c in ("obs", "pdd_st", "pdd_fo", "pdd_diff", "P_st", "P_fo", "SW_fo"):
        ok = df[[c, "err"]].dropna()
        if len(ok) > 4:
            print(f"    {c:9s} r {ok[c].corr(ok.err):+.2f}  (n {len(ok)})")
    ok = df[["pdd_st", "pdd_fo"]].dropna()
    print(f"  station vs forcing PDD: r {ok.pdd_st.corr(ok.pdd_fo):.2f}, mean {ok.pdd_st.mean():.0f} vs {ok.pdd_fo.mean():.0f} (n {len(ok)})")
