#!/usr/bin/env python3
"""Per-HRU statistics of the glacier rasters, for glacier_cold_state.py.

Reads the HRU shapefile (shapefiles/catchment/<name>_HRUs_<discretization>.shp) and writes, under
shapefiles/catchment_intersection:

  with_debris_thickness/catchment_with_debris.shp      debri_mean, mean debris thickness of the debris cells (m)
  with_domain_type/catchment_with_domain_type.shp      domType_<t>, cell count of each domain type
  with_dem_domain/catchment_with_dem_domain.shp        elv_mean_<t>, tsl_mean_<t>, asp_mean_<t>: mean elevation (m),
                                                       tan slope and circular-mean aspect (deg E of N) by domain type

and attributes/glaciers/domain_<name>_hru_id.tif, the HRU of each DEM cell (all touched). Slopes come from
the surface DEM's gradient, clipped to 1e-6..tan(80 deg); flat cells have no aspect.

    ./glacier_zonal_stats.py domains/wolverine.yaml
"""

import argparse
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from rasterstats import zonal_stats
from shapely.geometry import mapping

from domain_config import load_config


def dem_slope_aspect(dem_path):
    """Surface DEM (m, NaN off the raster), its nodata value and transform, tan slope clipped to
    1e-6..tan(80 deg) (-9999 where undefined) and aspect (deg E of N, -1 where flat)."""
    with rasterio.open(dem_path) as src:
        nodata = src.nodatavals[0] if src.nodatavals[0] is not None else -9999.0
        affine = src.transform
        dem = src.read(1, masked=True).astype(np.float64).filled(np.nan)
        cell_x, cell_y = abs(affine[0]), abs(affine[4])
        if src.crs is not None and src.crs.is_geographic:
            lat = (src.bounds.bottom + src.bounds.top) / 2
            cell_x *= 111000.0 * np.cos(np.radians(lat))
            cell_y *= 111000.0
    dy, dx = np.gradient(dem, cell_y, cell_x)
    magnitude = np.sqrt(dx * dx + dy * dy)
    max_tan = float(np.tan(np.radians(80.0)))
    tan_slope = np.minimum(np.maximum(magnitude, 1e-6), max_tan)
    tan_slope = np.where(np.isfinite(tan_slope), tan_slope, -9999.0)
    aspect = (90 - np.degrees(np.arctan2(-dy, dx))) % 360
    aspect[magnitude < 1e-6] = -1
    return dem, nodata, affine, tan_slope, aspect


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--output-dir", help="write the shapefiles and raster here instead of the domain's folders")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    glacier_dir = os.path.join(project, "attributes", "glaciers")
    inter = os.path.join(project, "shapefiles", "catchment_intersection")
    hru_column = c.get("hru_id_column", "HRU_ID")
    catchment = gpd.read_file(os.path.join(project, "shapefiles", "catchment",
                                           c.get("catchment_shp", f"{name}_HRUs_elevation.shp")))

    def out(sub, filename):
        folder = a.output_dir or os.path.join(inter, sub)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, filename)

    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_debris_thickness.tif")) as src:
        stats = zonal_stats(catchment, src.read(1), affine=src.transform, stats=["mean"], nodata=0)
    gdf = catchment.copy()
    gdf["debri_mean"] = pd.DataFrame(stats)["mean"]
    gdf.to_file(out("with_debris_thickness", "catchment_with_debris.shp"))

    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_domain_type_extend.tif")) as src:
        type_data = src.read(1)
        stats = zonal_stats(catchment, type_data, affine=src.transform, stats=["count"], categorical=True, nodata=0)
    counts = pd.DataFrame(stats).fillna(0)
    counts = counts.rename(columns=lambda x: x if x == "count" else f"domType_{int(float(x))}")
    for col in counts.columns:
        if col != "count":
            counts[col] = counts[col].astype(int)
    catchment.join(counts).to_file(out("with_domain_type", "catchment_with_domain_type.shp"))

    dem_path = os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_elv.tif")
    dem, nodata, affine, tan_slope, aspect = dem_slope_aspect(dem_path)
    has_aspect = np.isfinite(aspect) & (aspect >= 0)
    sin_a = np.where(has_aspect, np.sin(np.radians(aspect)), -9999.0)
    cos_a = np.where(has_aspect, np.cos(np.radians(aspect)), -9999.0)

    gdf = catchment.copy()
    for t in range(1, 6):
        in_type = type_data == t
        elev = np.where(in_type, dem, nodata)
        if np.all(~np.isfinite(elev) | (elev == nodata)):
            continue
        mean = lambda data, nd: pd.DataFrame(zonal_stats(catchment, data, affine=affine, stats=["mean"], nodata=nd))["mean"]
        gdf[f"elv_mean_{t}"] = mean(elev, nodata)
        gdf[f"tsl_mean_{t}"] = mean(np.where(in_type, tan_slope, -9999.0), -9999.0)
        ms, mc = mean(np.where(in_type, sin_a, -9999.0), -9999.0), mean(np.where(in_type, cos_a, -9999.0), -9999.0)
        gdf[f"asp_mean_{t}"] = [np.nan if s is None or c_ is None or np.isnan(s) or np.isnan(c_)
                                else float(np.degrees(np.arctan2(s, c_)) % 360) for s, c_ in zip(ms, mc)]
    gdf.to_file(out("with_dem_domain", "catchment_with_dem_domain.shp"))

    with rasterio.open(dem_path) as src:
        meta = src.meta.copy()
        shape = src.shape
    meta.update({"dtype": "int32", "nodata": -9999})
    hru_raster = features.rasterize([(mapping(g), h) for g, h in zip(catchment.geometry, catchment[hru_column].values)],
                                    out_shape=shape, transform=affine, fill=-9999, all_touched=True, dtype=np.int32)
    hru_path = os.path.join(a.output_dir or glacier_dir, f"domain_{name}_hru_id.tif")
    with rasterio.open(hru_path, "w", **meta) as dst:
        dst.write(hru_raster, 1)
    print(f"wrote the catchment intersections and {hru_path}")


if __name__ == "__main__":
    main()
