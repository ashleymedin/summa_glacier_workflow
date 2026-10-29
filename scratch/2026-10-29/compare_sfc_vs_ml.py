#!/usr/bin/env python3
"""Compare ERA5 single-levels 2 m temperature, dewpoint and 10 m wind with the raw_data level-137 fields (Gulkana, a month each of two seasons)."""
import os, sys, tempfile
import cdsapi, numpy as np, xarray as xr
from ecmwf.datastores import Client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from acquire_era5 import grid_area, opened, unpack
from domain_config import load_config

c = load_config("domains/gulkana.yaml")
raw = os.path.join(c["project_dir"], "forcing", "raw_data")
area = grid_area(c["project_dir"], c["domain"], raw)
u, k, _ = cdsapi.api.get_url_key_verify(None, None, None)
client = Client(url=u, key=k)

def q_from_dew(td, p):
    """Specific humidity from dewpoint (K) and pressure (Pa), the IFS Tetens over water (over ice below 250.16 K) blend."""
    e = np.where(td > 273.16, 611.21 * np.exp(17.502 * (td - 273.16) / (td - 32.19)), 611.21 * np.exp(22.587 * (td - 273.16) / (td + 0.7)))
    return 0.622 * e / (p - 0.378 * e)

for y, m in ((2008, 1), (2008, 7)):
    req = {"product_type": ["reanalysis"], "variable": ["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind", "10m_v_component_of_wind"],
           "year": [str(y)], "month": [f"{m:02d}"], "day": [f"{d:02d}" for d in range(1, 32)], "time": [f"{h:02d}:00" for h in range(24)],
           "area": area, "data_format": "netcdf", "download_format": "unarchived"}
    with tempfile.TemporaryDirectory() as w:
        f = client.submit("reanalysis-era5-single-levels", req).download(os.path.join(w, "s.download"))
        s = opened(unpack(f, w)).load()
    old = xr.open_dataset(os.path.join(raw, f"domain_Gulkana_ERA5_merged_{y}{m:02d}.nc"))
    old = old.assign_coords(time=s.time.values) if old.time.size == s.time.size else old
    print(f"## {y}-{m:02d}")
    new = {"airtemp": s["t2m"], "spechum": q_from_dew(s["d2m"], old["airpres"].values), "windspd": np.hypot(s["u10"], s["v10"])}
    for v, n in new.items():
        d = np.asarray(n, "f8") - old[v].values.astype("f8")
        print(f"{v:8s} bias {d.mean():+.3g}  rms {np.sqrt((d**2).mean()):.3g}  old mean {old[v].values.mean():.4g}  ratio {np.asarray(n).mean() / old[v].values.mean():.3f}")
