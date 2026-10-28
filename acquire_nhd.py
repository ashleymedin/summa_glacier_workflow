#!/usr/bin/env python3
"""Fetch the USGS watershed boundaries and hydrography around a domain, for US basins, into shapefiles/nhd.gpkg.

From the National Map services (hydro.nationalmap.gov, no key), over the domain's bounding_box:

  huc12          WBD 12-digit watersheds, with `gauge` 1 on the one holding the pour point
  flowlines      NHD flowlines (large scale)
  waterbodies    NHD lakes and ponds (large scale)

one layer each of shapefiles/nhd.gpkg.

glacier_extend.py clips the basin it delineates on the bed to the gauge's HUC12 when the YAML sets `basin_within: huc12`, so a
glacier on the far side of a divide the bed puts in the wrong place is not taken into the basin, and plot_basin_setup.py draws
the streams and lakes. Outside the US these files are absent and the basin is the delineated one, with glaciers held by --gru-threshold of their cells in
it; README.md lists the national and global sources to use there (HydroBASINS, HydroRIVERS, HydroLAKES, Canada, Chile, Iceland).

    ./acquire_nhd.py domains/wolverine.yaml
"""

import argparse
import os

import certifi
import geopandas as gpd
import requests
from shapely.geometry import Point

from domain_config import load_config

BASE = "https://hydro.nationalmap.gov/arcgis/rest/services"
LAYERS = {"huc12": ("wbd", 6), "flowlines": ("nhd", 6), "waterbodies": ("nhd", 12)}


def query(service, layer, bbox):
    """The layer's features intersecting bbox (lon_min, lat_min, lon_max, lat_max), paged."""
    frames, offset = [], 0
    while True:
        params = dict(f="geojson", where="1=1", geometry=",".join(str(b) for b in bbox), geometryType="esriGeometryEnvelope",
                      inSR=4326, outSR=4326, spatialRel="esriSpatialRelIntersects", outFields="*", returnGeometry="true",
                      resultOffset=offset, resultRecordCount=1000)
        r = requests.get(f"{BASE}/{service}/MapServer/{layer}/query", params=params, timeout=180, verify=certifi.where())
        r.raise_for_status()
        features = r.json().get("features", [])
        if not features:
            break
        frames.append(gpd.GeoDataFrame.from_features(features, crs=4326))
        offset += len(features)
        if len(features) < 1000:
            break
    return gpd.GeoDataFrame(gpd.pd.concat(frames, ignore_index=True), crs=4326) if frames else gpd.GeoDataFrame(geometry=[], crs=4326)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    a = p.parse_args()
    c = load_config(a.config)
    lat1, lon0, lat0, lon1 = (float(v) for v in c["bounding_box"].split("/"))
    lat, lon = (float(v) for v in c["pour_point"].split("/"))
    out = os.path.join(c["project_dir"], "shapefiles", "nhd.gpkg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    for name, (service, layer) in LAYERS.items():
        gdf = query(service, layer, (lon0, lat0, lon1, lat1))
        if name == "huc12":
            gdf["gauge"] = [int(g.contains(Point(lon, lat))) for g in gdf.geometry]
        gdf.to_file(out, layer=name, driver="GPKG")
        print(f"{name}: {len(gdf)} features -> {out}")


if __name__ == "__main__":
    main()
