#!/usr/bin/env python3
"""Gulkana's corrected forcing at HRU 2 (1704 m) against the 2024 Site B AWS (1682 m), by month: wind, air
temperature, incoming shortwave, and the glacier factors' effect.

    siteb_forcing.py [forcing_dir]
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

G = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(G, "data/domain_Gulkana/forcing/SUMMA_input/station_corrected")
AWS = os.path.join(G, "data/domain_Gulkana/observations/campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv")
WIND, COOL = 0.5943, 0.7331

rows = []
for f in sorted(glob.glob(os.path.join(FRC, "*_20240[4-9].nc"))):
    with nc4.Dataset(f) as d:
        t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                        only_use_python_datetimes=True))
        j = list(np.asarray(d["hruId"][:])).index(2)
        rows.append(pd.DataFrame({"T": d["airtemp"][:, j] - 273.15, "U": d["windspd"][:, j], "SW": d["SWRadAtm"][:, j],
                                  "LW": d["LWRadAtm"][:, j]}, index=t))
frc = pd.concat(rows)
a = pd.read_csv(AWS, skiprows=[1, 2], parse_dates=["TIMESTAMP"], date_format="%m/%d/%Y %H:%M").set_index("TIMESTAMP")
a = a[["AirTC_Avg", "WS_ms_Avg", "SWUpper_Avg", "SWLower_Avg"]].apply(pd.to_numeric, errors="coerce")
a.index = a.index + pd.Timedelta(hours=9)  # AKST logger clock to UTC, as wind_exposure_from_campaign.py found
a = a.resample("h").mean()
j = pd.concat([frc, a], axis=1).dropna()
j["Tg"] = np.where(j["T"] > 0, COOL * j["T"], j["T"])
j["Ug"] = WIND * j["U"]
j["heat_frc"] = j.Ug * j.Tg.clip(lower=0)
j["heat_aws"] = j.WS_ms_Avg * j.AirTC_Avg.clip(lower=0)
g = j.groupby(j.index.month)
out = pd.DataFrame({"T_frc": g["T"].mean(), "T_glac": g.Tg.mean(), "T_aws": g.AirTC_Avg.mean(),
                    "U_frc": g.U.mean(), "U_glac": g.Ug.mean(), "U_aws": g.WS_ms_Avg.mean(),
                    "UT+_glac": g.heat_frc.mean(), "UT+_aws": g.heat_aws.mean(),
                    "SW_frc": g.SW.mean(), "SW_aws": g.SWUpper_Avg.mean(), "alb_aws": g.SWLower_Avg.sum() / g.SWUpper_Avg.sum(),
                    "hours": g.size()})
print(out.round(2).to_string())
