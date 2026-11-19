#!/usr/bin/env python3
"""Krishnanand et al. (2026) mean summer on-glacier wind, u = 0.268 |T| / slope10, at Gulkana Site B against its 2024 AWS and the
forcing's wind there. T is the forcing's mean June-September 2024 air temperature (deg C) at the HRU nearest Site B, lapsed to the
station; slope10 the slope (m/m) at the station of Copernicus GLO-30 averaged to 10 km, from a 3x3 window.

    krishnanand_wind.py
"""
import glob
import os

import netCDF4 as nc
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SITE = dict(lat=63.28551, lon=-145.41034, z=1682.0)
JJAS = [6, 7, 8, 9]


def slope10(lat, lon, tile):
    with rasterio.open(tile) as s:
        f = round(10000 / (abs(s.transform.a) * 111320 * np.cos(np.radians(lat))))  # cells per 10 km east-west
        fy = round(10000 / (abs(s.transform.e) * 110574))
        z = s.read(1, out_shape=(s.height // fy, s.width // f), resampling=Resampling.average).astype(float)
        t = s.transform * s.transform.scale(s.width / z.shape[1], s.height / z.shape[0])
    dx, dy = abs(t.a) * 111320 * np.cos(np.radians(lat)), abs(t.e) * 110574
    gy, gx = np.gradient(z, dy, dx)  # central differences: a 3x3 window
    r, c = ~t * (lon, lat)  # column, row
    return float(np.hypot(gx, gy)[int(c), int(r)])


aws = pd.read_csv(f"{WF}/data/domain_Gulkana/observations/campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv",
                  skiprows=[1, 2], parse_dates=["TIMESTAMP"], index_col="TIMESTAMP")
u_obs = pd.to_numeric(aws.WS_ms_Avg, errors="coerce")
t_obs = pd.to_numeric(aws.AirTC_Avg, errors="coerce")
months = u_obs[u_obs.index.month.isin(JJAS)]
print(f"Site B AWS {months.index.min():%d %b}-{months.index.max():%d %b %Y}: wind {months.mean():.2f} m/s, air {t_obs[t_obs.index.month.isin(JJAS)].mean():.2f} C")
s = slope10(SITE["lat"], SITE["lon"], glob.glob(f"{WF}/data/external/Copernicus_GLO30/*N63_00_W146*.tif")[0])
print(f"slope10 at Site B {s:.3f} m/m ({np.degrees(np.arctan(s)):.1f} deg)")
for label, d in [("added", "data/domain_Gulkana/forcing/SUMMA_input/station_corrected"), ("general", "data/domain_Gulkana_general/forcing/SUMMA_input")]:
    parts = []
    for f in sorted(glob.glob(f"{WF}/{d}/*_2024??.nc")):
        with nc.Dataset(f) as x:
            tt = pd.to_datetime(nc.num2date(x["time"][:], x["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True))
            parts.append(pd.DataFrame({"T": np.array(x["airtemp"][:, 1]) - 273.15, "U": np.array(x["windspd"][:, 1])}, index=tt))
    fr = pd.concat(parts)
    fr = fr[fr.index.isin(months.index.round("h")) | fr.index.month.isin(JJAS)]
    fr = fr[fr.index.month.isin(JJAS) & (fr.index >= months.index.min()) & (fr.index <= months.index.max())]
    u_pred = 0.268 * abs(fr["T"].mean()) / s
    print(f"{label:8s} forcing at HRU 2: T {fr['T'].mean():.2f} C, wind {fr['U'].mean():.2f} m/s; Krishnanand u {u_pred:.2f} m/s "
          f"(obs {months.mean():.2f}); u_pred / forcing {u_pred / fr['U'].mean():.2f}, obs / forcing {months.mean() / fr['U'].mean():.2f}")
