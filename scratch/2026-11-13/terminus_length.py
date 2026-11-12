#!/usr/bin/env python3
"""Stream length from each USGS glacier outline to the gauge: along the mapped path from the recent ice front to the gauge
(the `reach` layer of shapefiles/nhd.gpkg, nhd_reach.py), the distance from the gauge to the first point inside that
year's outline, with the drop over it on the USGS survey DEM. An outline that does not reach the path ends above it.

    ./terminus_length.py
"""
import os

import geopandas as gpd
import networkx as nx
import numpy as np
import rasterio
from shapely.geometry import Point

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
EXT = os.path.join(ROOT, "data", "external", "GlacierDEM")
SITES = {"wolverine": ("Wolverine", (60.36999097, -148.8988085), "EasternKenai_20150813_DEM/EasternKenai_20150813_DEM.tif"),
         "gulkana": ("Gulkana", None, "Deltas_20160830_DEM/Deltas_20160830_DEM.tif")}


def gauge_point(site):
    import yaml
    c = yaml.safe_load(open(os.path.join(ROOT, "domains", f"{site}.yaml")))
    lat, lon = (float(x) for x in str(c["pour_point"]).split("/"))
    return Point(lon, lat)


def main():
    o = gpd.read_file(os.path.join(EXT, "USGS_Glacier_Boundaries_shp", "USGS_Glacier_Boundaries.shp"))
    for site, (name, _, dem) in SITES.items():
        gpkg = os.path.join(ROOT, "data", f"domain_{name}", "shapefiles", "nhd.gpkg")
        reach = gpd.read_file(gpkg, layer="reach")
        crs = reach.estimate_utm_crs()
        line = reach.to_crs(crs).geometry.iloc[0]
        g = gpd.GeoSeries([gauge_point(site)], crs=4326).to_crs(crs).iloc[0]
        if line.project(g) > line.length / 2:   # orient the path from the gauge
            from shapely.geometry import LineString
            line = LineString(list(line.coords)[::-1])
        s = np.arange(0, line.length, 5.0)
        pts = gpd.GeoSeries([line.interpolate(x) for x in s], crs=crs)
        with rasterio.open(os.path.join(EXT, dem)) as r:
            pr = pts.to_crs(r.crs)
            z = np.array([v[0] for v in r.sample([(p.x, p.y) for p in pr])], float)
        print(f"{site}: path {line.length:.0f} m from the gauge ({z[0]:.0f} m) to the recent front ({z[-1]:.0f} m)")
        print("  year  length (m)  drop (m)")
        og = o[o.Glacier.str.contains(name)].to_crs(crs)
        for y, poly in sorted(zip(og.Year, og.geometry)):
            inside = pts.within(poly).values
            if inside.any():
                i = int(np.argmax(inside))
                print(f"  {int(y)}  {s[i]:9.0f}  {z[i] - z[0]:8.0f}")
            else:
                print(f"  {int(y)}  > {line.length:7.0f}  (front above the path)")


if __name__ == "__main__":
    main()
