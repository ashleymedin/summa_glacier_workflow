#!/usr/bin/env python3
"""HRU area, centre, elevation, slope and contour length from the HRU polygons and the surface DEM.

Reads shapefiles/catchment/<name>_HRUs_elevation.shp and attributes/elevation/dem/domain_<name>_elv.tif, and
writes, by HRU id, into both that shapefile (HRU_area, center_lat, center_lon, elev_mean) and
settings/SUMMA/attributes.nc (HRUarea, latitude, longitude, elevation, tan_slope, contourLength):

  area            m2, in the domain's utm_crs
  centre          polygon centroid in utm_crs, as degrees N and E
  elevation       mean DEM elevation of the cells centred in the polygon, m
  tan_slope       mean tan slope of those cells, as glacier_zonal_stats.py computes it
  contourLength   square root of the area, m, as glacier_cold_state.py gives each domain

    ./hru_attributes.py domains/gulkana.yaml
"""

import argparse
import os

import geopandas as gpd
import netCDF4 as nc4
import numpy as np
import rasterio
from rasterstats import zonal_stats

from domain_config import load_config
from glacier_zonal_stats import dem_slope_aspect


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    hru_column = c.get("hru_id_column", "HRU_ID")
    shp = os.path.join(project, "shapefiles", "catchment", c.get("catchment_shp", f"{name}_HRUs_elevation.shp"))
    attributes = os.path.join(project, "settings", "SUMMA", "attributes.nc")

    hrus = gpd.read_file(shp)
    utm = hrus.to_crs(c["utm_crs"])
    area = utm.geometry.area.values
    centre = utm.geometry.centroid.to_crs("epsg:4326")
    dem_path = os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_elv.tif")
    dem, nodata, affine, tan_slope, _ = dem_slope_aspect(dem_path)
    with rasterio.open(dem_path) as src:
        polygons = hrus.to_crs(src.crs)
    mean = lambda data, nd: np.array([s["mean"] for s in zonal_stats(polygons, data, affine=affine, stats="mean", nodata=nd)])
    elev = mean(np.where(np.isfinite(dem), dem, nodata), nodata)
    slope = mean(tan_slope, -9999.0)
    new = {"HRUarea": area, "latitude": centre.y.values, "longitude": centre.x.values, "elevation": elev,
           "tan_slope": slope, "contourLength": np.sqrt(area)}

    hrus["HRU_area"], hrus["center_lat"], hrus["center_lon"], hrus["elev_mean"] = \
        area, new["latitude"], new["longitude"], elev
    hrus.to_file(shp)

    ids = hrus[hru_column].astype(int).values
    with nc4.Dataset(attributes, "a") as ds:
        order = [int(np.where(ids == h)[0][0]) for h in np.asarray(ds["hruId"][:]).astype(int)]
        for var, values in new.items():
            old = np.asarray(ds[var][:], dtype=float)
            ds[var][:] = values[order]
            print(f"{var:14s} " + "  ".join(f"{o:.6g} -> {n:.6g}" for o, n in zip(old, values[order])))
    print(f"basin {area.sum() / 1e6:.3f} km2; wrote {shp} and {attributes}")


if __name__ == "__main__":
    main()
