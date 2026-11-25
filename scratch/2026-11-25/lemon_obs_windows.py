#!/usr/bin/env python3
"""Lemon observation files for split scoring windows: _cal holds discharge to WY2015, _eval discharge WY2016-20 and balances and temperature after WY2022 (15052000 departs from Mendenhall from WY2021)."""
import os, numpy as np, xarray as xr
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/domain_LemonCreek/observations/calibration")
def keep(src, dst, var, first, last):
    with xr.open_dataset(f"{D}/{src}", decode_times=False) as d:
        d = d.load(); t = xr.decode_cf(d[["time"]]).time.values
        d[var] = d[var].where((t > np.datetime64(first)) & (t <= np.datetime64(last)))
        d[var].encoding = {"_FillValue": np.nan}; d.attrs["comment"] = str(d.attrs.get("comment", "")) + f"; kept {first} to {last}"
        d.to_netcdf(f"{D}/{dst}"); print(dst, int(np.isfinite(d[var]).sum()))
f, t, b = "USGS_15052000_daily_flow", "USGS_15052000_daily_temperature", "lemoncreek_mass_balance_seasonal_2006"
keep(f + ".nc", f + "_cal.nc", "q_obs", "2005-10-01T09", "2015-10-01T09")
keep(f + ".nc", f + "_eval.nc", "q_obs", "2015-10-01T09", "2020-10-01T09")
keep(t + ".nc", t + "_eval.nc", "t_obs", "2022-10-01T09", "2026-08-01")
with xr.open_dataset(f"{D}/{b}.nc") as d: d.load().isel(time=d.time.values > np.datetime64("2023-01-01")).to_netcdf(f"{D}/{b}_eval.nc")
