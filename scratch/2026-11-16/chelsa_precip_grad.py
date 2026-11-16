#!/usr/bin/env python3
"""The precipitation lapse rate precipElevGrad (m-1) CHELSA V2.1 annual precipitation (bio12, 1981-2010) implies in a basin.

Each 30-arcsec CHELSA cell gets the mean Copernicus GLO-30 elevation within it. precipElevGrad is the relative slope,
P_dom = P_HRU [1 + g (z_dom - z_HRU)], fitted three ways: within the HRUs (P / HRU mean - 1 against z - HRU mean, pooled),
across the whole basin (slope over the basin mean), and across the cells within --buffer km of the basin.

    chelsa_precip_grad.py Wolverine Gulkana
"""

import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.warp import Resampling, reproject

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def cells(basin):
    """CHELSA precipitation (mm yr-1) and mean GLO-30 elevation on the CHELSA grid, its transform and the HRUs."""
    with rasterio.open(os.path.join(DATA, "external", "CHELSA", f"CHELSA_bio12_1981-2010_V.2.1_{basin}.tif")) as r:
        p = r.read(1).astype(float)
        p = np.where(p == r.nodata, np.nan, p * r.scales[0] + r.offsets[0])
        transform, crs, shape = r.transform, r.crs, r.shape
    dems = [rasterio.open(f) for f in glob.glob(os.path.join(DATA, "external", "Copernicus_GLO30", "*.tif"))]
    dem, dem_t = merge(dems)
    z = np.full(shape, np.nan)
    reproject(dem[0].astype(float), z, src_transform=dem_t, src_crs=dems[0].crs, dst_transform=transform, dst_crs=crs,
              resampling=Resampling.average, src_nodata=dems[0].nodata, dst_nodata=np.nan)
    hrus = gpd.read_file(os.path.join(DATA, f"domain_{basin}", "shapefiles", "catchment", f"{basin}_HRUs_elevation.shp")).to_crs(crs)
    return p, z, transform, hrus


def inside(geoms, transform, shape):
    """Cells whose centre falls in the geometries."""
    return ~geometry_mask(geoms, shape, transform, all_touched=False)


def fit(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return np.polyfit(x[ok], y[ok], 1)[0], int(ok.sum())


def report(basin, buffer_km):
    p, z, t, hrus = cells(basin)
    dz, dp, nh = [], [], []
    for _, h in hrus.iterrows():
        m = inside([h.geometry], t, p.shape) & np.isfinite(p) & np.isfinite(z)
        nh.append(int(m.sum()))
        if m.sum() > 1:
            dz.append(z[m] - z[m].mean()); dp.append(p[m] / p[m].mean() - 1)
    g_hru, n_hru = fit(np.concatenate(dz), np.concatenate(dp))
    b = inside(list(hrus.geometry), t, p.shape) & np.isfinite(p) & np.isfinite(z)
    s, n_b = fit(z[b], p[b])
    utm = hrus.estimate_utm_crs()
    ring = gpd.GeoSeries([hrus.to_crs(utm).union_all().buffer(buffer_km * 1000)], crs=utm).to_crs(hrus.crs)
    w = inside(list(ring), t, p.shape) & np.isfinite(p) & np.isfinite(z)
    sw, n_w = fit(z[w], p[w])
    print(f"{basin}: cells per HRU {nh}; basin {n_b} cells, z {np.nanmin(z[b]):.0f}-{np.nanmax(z[b]):.0f} m, "
          f"P {np.nanmin(p[b]):.0f}-{np.nanmax(p[b]):.0f} mm yr-1 (mean {p[b].mean():.0f})")
    print(f"  within HRUs ({n_hru} cells)       {g_hru:.2e} m-1")
    print(f"  across the basin ({n_b} cells)    {s / p[b].mean():.2e} m-1")
    print(f"  within {buffer_km:g} km ({n_w} cells)      {sw / p[w].mean():.2e} m-1")


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("basins", nargs="+")
    a.add_argument("--buffer", type=float, default=10.0, help="km around the basin")
    for basin in a.parse_args().basins:
        report(basin, a.parse_args().buffer)


if __name__ == "__main__":
    main()
