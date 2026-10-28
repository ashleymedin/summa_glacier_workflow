#!/usr/bin/env python3
"""Build a domain's GRU and HRUs from its basin: elevation bands of the setup's start surface, cut to the basin outline.

The GRU is the basin of glacier_extend.py (shapefiles/river_basins), whole glaciers included. The HRUs are its elevation bands, the
YAML's hru_bands (edges in m, so n edges make n+1 HRUs), else bands hru_band_size (m, default 400) wide from the lowest elevation in
the basin, as SYMFLUENCE's ELEVATION_BAND_SIZE did, numbered up from the lowest, each the union of the basin cells of the start surface (domain_<name>_glacier_elv.tif: MERIT, with the USGS survey surface on the benchmark glacier in the added-data setup, so the setups' HRUs differ) in the band, so a band can be several islands.
A 3x3 median filter on the band numbers takes the single-cell speckle out. Writes

  shapefiles/catchment/<name>_HRUs_elevation.shp   GRU_ID, HRU_ID, elevClass, with HRU_area, centre and elev_mean (hru_attributes.py
                                                   writes the true values)
  shapefiles/catchment/<name>_HRUs_GRUs.shp        the GRU, as the HRUs dissolved

hru_attributes.py then fills settings/SUMMA/attributes.nc, which needs as many HRUs as it already holds.

    ./make_hrus.py domains/wolverine.yaml
"""

import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask, shapes
from scipy.ndimage import median_filter
from shapely.geometry import shape
from shapely.ops import unary_union

from domain_config import load_config


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    basin = gpd.read_file(glob.glob(os.path.join(project, "shapefiles", "river_basins", "*.shp"))[0]).to_crs(4326)
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv.tif")) as src:
        dem, transform = src.read(1).astype(float), src.transform
        dem[dem == src.nodata] = np.nan
    inside = geometry_mask(list(basin.geometry), transform=transform, invert=True, out_shape=dem.shape) & np.isfinite(dem)
    edges = c.get("hru_bands")
    if not edges:
        lo, hi = np.nanmin(dem[inside]), np.nanmax(dem[inside])
        edges = list(np.arange(lo + c.get("hru_band_size", 400.0), hi, c.get("hru_band_size", 400.0)))
    band = np.where(inside, np.digitize(dem, edges) + 1, 0).astype(np.int16)
    smooth = median_filter(band, size=3)
    band = np.where(inside & (smooth > 0), smooth, band)
    rows = []
    for k in range(1, len(edges) + 2):
        polys = [shape(g) for g, v in shapes(band, mask=band == k, transform=transform) if v == k]
        if polys:
            rows.append({"GRU_ID": 1, "HRU_ID": len(rows) + 1, "elevClass": k, "geometry": unary_union(polys)})
    hrus = gpd.GeoDataFrame(rows, crs=4326)
    utm = hrus.to_crs(c["utm_crs"])
    hrus["HRU_area"] = utm.geometry.area.values
    centre = utm.geometry.centroid.to_crs(4326)
    hrus["center_lon"], hrus["center_lat"] = centre.x.values, centre.y.values
    hrus["elev_mean"] = [float(np.nanmean(dem[band == k])) for k in hrus["elevClass"]]
    out = os.path.join(project, "shapefiles", "catchment")
    os.makedirs(out, exist_ok=True)
    hrus.to_file(os.path.join(out, f"{name}_HRUs_elevation.shp"))
    whole = hrus.dissolve(by="GRU_ID").reset_index()
    whole["gru_to_seg"], whole["HRU_ID"], whole["hru_type"] = 1, 1, "GRU"
    whole["GRU_area"] = whole.to_crs(c["utm_crs"]).geometry.area.values
    whole[["GRU_ID", "gru_to_seg", "GRU_area", "HRU_ID", "hru_type", "elev_mean", "center_lon", "center_lat", "HRU_area", "geometry"]].to_file(
        os.path.join(out, f"{name}_HRUs_GRUs.shp"))
    print(f"{len(hrus)} HRUs from the bands {[round(e) for e in edges]} m: "
          + ", ".join(f"{r.HRU_ID}: {r.HRU_area / 1e6:.2f} km2 at {r.elev_mean:.0f} m" for r in hrus.itertuples()))


if __name__ == "__main__":
    main()
