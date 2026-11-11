#!/usr/bin/env python3
"""Times one month's hourly pressure-level request at the CDS (Wolverine's grid, January 2015).

    python scratch/2026-11-11/levels/time_request.py
"""
import os
import time

import cdsapi

HERE = os.path.dirname(os.path.abspath(__file__))
t0 = time.time()
cdsapi.Client().retrieve("reanalysis-era5-pressure-levels", {
    "product_type": ["reanalysis"],
    "variable": ["temperature", "geopotential", "specific_humidity", "u_component_of_wind", "v_component_of_wind"],
    "pressure_level": ["700", "750", "775", "800", "825", "850", "875", "900", "925", "950", "975", "1000"],
    "year": ["2015"], "month": ["01"], "day": [f"{d:02d}" for d in range(1, 32)],
    "time": [f"{h:02d}:00" for h in range(24)], "area": [60.5, -149.0, 60.25, -148.75],
    "data_format": "netcdf", "download_format": "unarchived"}, os.path.join(HERE, "test_201501.nc"))
print(f"done in {(time.time() - t0) / 60:.1f} min")
