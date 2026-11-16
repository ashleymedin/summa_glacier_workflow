"""Incoming longwave at Gulkana 1725 (WY2024-25) against ERA5 carried to 1,725 m four ways: the cell unscaled, the
old scaling (6.5 K/km from the forcing shapefile's elev_m), the current free-air T^4 scaling from ERA5's orography, the same from elev_m and from the basin's mean elevation (remap_forcing.py),
and TopoSCALE's (clear-sky emissivity of Konzelmann et al. 1994 from free-air vapour pressure, cloud part kept).

    /Users/amedin/miniconda3/envs/glacier/bin/python scratch/2026-11-16/lw_vs_station.py
"""
import glob, os, sys
import numpy as np
import pandas as pd
import geopandas as gpd
from netCDF4 import Dataset, num2date

sys.path.insert(0, os.getcwd())  # run from the workflow root
from remap_forcing import weights, read_levels, column, cell_elevation, relhum, CLEAR, SATVPFRZ, TFREEZE

SIGMA, Z_STN, HRU = 5.670374e-8, 1725.0, 2
D = "data/domain_Gulkana"


def vapour(rh, t):
    """Vapour pressure (Pa) from relative humidity (-) and temperature (K), as relhum's saturation curve."""
    return rh * SATVPFRZ * np.exp(17.27 * (t - TFREEZE) / (237.30 + t - TFREEZE))


def eps_clear(e, t):
    """Clear-sky emissivity, Konzelmann et al. (1994) with TopoSCALE's coefficients (e in Pa)."""
    return 0.23 + 0.43 * (e / t) ** (1.0 / 5.7)


hrus = gpd.read_file(f"{D}/shapefiles/catchment/Gulkana_HRUs_elevation.shp").sort_values("HRU_ID")
cells = gpd.read_file(f"{D}/shapefiles/forcing/forcing_ERA5.shp")
raw = sorted(p for p in glob.glob(f"{D}/forcing/raw_data/domain_Gulkana_ERA5_merged_*.nc") if "202310" <= p[-9:-3] <= "202509")
with Dataset(raw[0]) as f:
    lat, lon = f["latitude"][:], f["longitude"][:]
w = weights(hrus, lat, lon)[HRU - 1]
z_basin = np.average(hrus.elev_mean, weights=hrus.HRU_area)
zs = cell_elevation(f"{D}/forcing/raw_levels/domain_Gulkana_ERA5_orography.nc", lat, lon)
elev_m = np.zeros_like(zs)
for _, c in cells.iterrows():
    elev_m[np.argmin(abs(lat - c.lat)), np.argmin(abs(lon - c.lon))] = c.elev_m
print("cells under HRU 2: weight", np.round(w[w > 0], 3), "ERA5 surface", np.round(zs[w > 0]), "elev_m", np.round(elev_m[w > 0]))

rows = []
for path in raw:
    lpath = path.replace("raw_data", "raw_levels").replace("_merged_", "_levels_")
    nxt = lpath.replace(path[-9:-3], f"{int(path[-9:-5]) + (path[-5:-3] == '12'):04d}{int(path[-5:-3]) % 12 + 1:02d}")
    with Dataset(path) as src:
        hours = np.asarray(src["time"][:], dtype="f8")
        time = num2date(hours, src["time"].units, only_use_cftime_datetimes=False)
        f = {v: np.asarray(src[v][:], dtype="f8") for v in ("LWRadAtm", "airtemp")}
    lev = read_levels(lpath, nxt if os.path.exists(nxt) else None, hours)
    out = {k: np.zeros(len(hours)) for k in ("cell", "old", "new", "dem", "basin", "konz", "t_stn")}
    for i, j in zip(*np.nonzero(w)):
        h = lev["h"][:, :, i, j]
        at_stn, at_cell = column(h, Z_STN, zs[i, j] + CLEAR), column(h, zs[i, j], zs[i, j] + CLEAR)
        t1, t0 = at_stn(lev["t"][:, :, i, j]), at_cell(lev["t"][:, :, i, j])
        e1 = vapour(np.clip(at_stn(lev["rh"][:, :, i, j]), 0.01, 1), t1)
        e0 = vapour(np.clip(at_cell(lev["rh"][:, :, i, j]), 0.01, 1), t0)
        lw, t2 = f["LWRadAtm"][:, i, j], f["airtemp"][:, i, j]
        t_dem = column(h, elev_m[i, j], zs[i, j] + CLEAR)(lev["t"][:, :, i, j])
        t_bas = column(h, z_basin, zs[i, j] + CLEAR)(lev["t"][:, :, i, j])
        t_old = t2 - 0.0065 * (Z_STN - elev_m[i, j])
        eps1 = eps_clear(e1, t1) + lw / (SIGMA * t0 ** 4) - eps_clear(e0, t0)
        for k, v in (("cell", lw), ("old", lw * (t_old / t2) ** 4), ("new", lw * (t1 / t0) ** 4), ("dem", lw * (t1 / t_dem) ** 4), ("basin", lw * (t1 / t_bas) ** 4),
                     ("konz", eps1 * SIGMA * t1 ** 4), ("t_stn", t1 - TFREEZE)):
            out[k] += w[i, j] * v
    rows.append(pd.DataFrame(out, index=pd.DatetimeIndex(time)))
era = pd.concat(rows)

stn = pd.concat(pd.read_csv(p, parse_dates=["UTC_time"], index_col="UTC_time")
                for p in sorted(glob.glob(f"{D}/observations/stations/1725/LVL2/gulkana1725_hourly_LVL2_202[45].csv")))
both = era.join(stn[["LongwaveIn", "site_temp_USGS"]], how="inner").dropna()
both = both[(both.LongwaveIn > 100) & (both.LongwaveIn < 500)]
print(f"{len(both)} hours with station longwave, {both.index[0]:%Y-%m-%d} to {both.index[-1]:%Y-%m-%d}")

season = both.index.month.map(lambda m: {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                                         6: "JJA", 7: "JJA", 8: "JJA"}.get(m, "SON"))
cols = ["LongwaveIn", "cell", "old", "new", "dem", "basin", "konz"]
print("\nmean incoming longwave (W m-2) and hours")
tab = both.groupby(season)[cols].mean().round(1)
tab["hours"] = both.groupby(season).size()
tab["T_stn"], tab["T_era5"] = both.groupby(season).site_temp_USGS.mean().round(1), both.groupby(season).t_stn.mean().round(1)
print(tab.reindex(["DJF", "MAM", "JJA", "SON"]).to_string())
print("\nbias against station (W m-2), all hours / JJA; RMSE of daily means")
daily = both[cols].resample("D").mean().dropna()
for k in cols[1:]:
    print(f"{k:5s} {np.mean(both[k] - both.LongwaveIn):6.1f} / {np.mean((both[k] - both.LongwaveIn)[season == 'JJA']):6.1f}"
          f"   daily RMSE {np.sqrt(np.mean((daily[k] - daily.LongwaveIn) ** 2)):5.1f}")
print("\nmonthly means (W m-2)")
print(both[cols].resample("MS").mean().round(1).assign(hours=both.LongwaveIn.resample("MS").size()).to_string())
