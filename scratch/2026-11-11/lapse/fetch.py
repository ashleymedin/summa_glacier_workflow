#!/usr/bin/env python3
"""ERA5 monthly means over both basins for the lapse-rate test: 2 m temperature and surface geopotential, and
temperature and geopotential on the pressure levels spanning the basins, WY2005-2025.

    python scratch/2026-11-11/lapse/fetch.py
"""
import os

import cdsapi

HERE = os.path.dirname(os.path.abspath(__file__))
AREA = [64.5, -150.5, 59.5, -144.0]   # N, W, S, E
YEARS = [str(y) for y in range(2004, 2026)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]
c = cdsapi.Client()
c.retrieve("reanalysis-era5-single-levels-monthly-means",
           {"product_type": ["monthly_averaged_reanalysis"], "variable": ["2m_temperature", "geopotential"],
            "year": YEARS, "month": MONTHS, "time": ["00:00"], "area": AREA, "data_format": "netcdf",
            "download_format": "unarchived"}, os.path.join(HERE, "era5_sfc_monthly.nc"))
c.retrieve("reanalysis-era5-pressure-levels-monthly-means",
           {"product_type": ["monthly_averaged_reanalysis"], "variable": ["temperature", "geopotential"],
            "pressure_level": ["700", "750", "775", "800", "825", "850", "875", "900", "925", "950"],
            "year": YEARS, "month": MONTHS, "time": ["00:00"], "area": AREA, "data_format": "netcdf",
            "download_format": "unarchived"}, os.path.join(HERE, "era5_pl_monthly.nc"))
