#!/usr/bin/env python3
"""The NHD stream path from a glacier's terminus to the gauge, its length, and the reach the model uses, for the plots and the stream HRU.

The terminus is the YAML's `terminus` [lon, lat], read off late imagery, else the lowest cell of the start outline of the domain's largest
glacier; the path is the shortest one along the NHD flowlines of shapefiles/nhd.gpkg (acquire_nhd.py) from the vertex nearest
the terminus to the vertex nearest the pour point. Writes the path as layer `reach` of nhd.gpkg and prints its length beside the
YAML's or cases.yaml's model reach (stream: length), which should agree. NHD has no channel width; that has to come from imagery or
the gauge's field measurements.

    ./nhd_reach.py domains/wolverine.yaml
"""

import argparse
import os

import geopandas as gpd
import networkx as nx
import numpy as np
import rasterio
import yaml
from shapely.geometry import LineString, Point

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))


def terminus(c, crs):
    """The ice front as a point in crs: the YAML's terminus [lon, lat] (from late imagery; the start outline's tongue has retreated since),
    else the lowest cell of the largest glacier's start outline."""
    project, name = c["project_dir"], c["domain"]
    if c.get("terminus"):
        return gpd.GeoSeries([Point(*c["terminus"])], crs=4326).to_crs(crs).iloc[0]
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id.tif")) as r:
        gid, tr = r.read(1), r.transform
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv.tif")) as r:
        elev = r.read(1).astype(float)
    ids, counts = np.unique(gid[gid > 0], return_counts=True)
    main = ids[np.argmax(counts)]
    z = np.where(gid == main, elev, np.inf)
    row, col = np.unravel_index(np.argmin(z), z.shape)
    x, y = tr * (col + 0.5, row + 0.5)
    return gpd.GeoSeries([Point(x, y)], crs=4326).to_crs(crs).iloc[0]


def model_reach_length(c):
    """The stream length (m) the model's cases give this domain's reach, or None."""
    stem = os.path.splitext(os.path.basename(c.get("_path", "")))[0]
    with open(os.path.join(HERE, "cases.yaml")) as f:
        cases = yaml.safe_load(f)
    name = c["domain"].lower()
    found = [v["stream"]["length"] for v in cases.values() if v.get("domain", "").replace("_general", "") == name and "stream" in v]
    found += [m["stream"]["length"] for v in cases.values() for m in v.get("merge", []) if m.get("domain") == name and "stream" in m]
    return max(found) if found else None


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    a = p.parse_args()
    c = load_config(a.config)
    project, name, crs = c["project_dir"], c["domain"], c["utm_crs"]
    nhd = os.path.join(project, "shapefiles", "nhd.gpkg")
    lines = gpd.read_file(nhd, layer="flowlines").to_crs(crs).rename(columns=str.lower)
    lines = lines[lines["ftype"].isin((460, 558))]
    graph = nx.Graph()
    for geom in lines.geometry:
        for part in getattr(geom, "geoms", [geom]):
            xy = list(part.coords)
            for u, v in zip(xy[:-1], xy[1:]):
                graph.add_edge((round(u[0], 1), round(u[1], 1)), (round(v[0], 1), round(v[1], 1)), weight=float(np.hypot(v[0] - u[0], v[1] - u[1])))
    nodes = np.array(list(graph.nodes))
    lat, lon = (float(v) for v in c["pour_point"].split("/"))
    gauge = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(crs).iloc[0]
    top = terminus(c, crs)
    near = lambda pt: tuple(nodes[np.argmin(np.hypot(nodes[:, 0] - pt.x, nodes[:, 1] - pt.y))])
    start, end = near(top), near(gauge)
    path = nx.shortest_path(graph, start, end, weight="weight")
    length = nx.shortest_path_length(graph, start, end, weight="weight")
    gap = (float(np.hypot(*(np.array(start) - [top.x, top.y]))), float(np.hypot(*(np.array(end) - [gauge.x, gauge.y]))))
    gpd.GeoDataFrame({"length_m": [length], "straight_m": [float(top.distance(gauge))]}, geometry=[LineString(path)], crs=crs).to_file(nhd, layer="reach", driver="GPKG")
    stem = os.path.splitext(os.path.basename(a.config))[0].replace("_general", "")
    with open(os.path.join(HERE, "cases.yaml")) as f:
        cases = yaml.safe_load(f)
    model = [v["stream"]["length"] for k, v in cases.items() if v.get("domain") == stem and "stream" in v]
    merged = [m["stream"]["length"] for v in cases.values() for m in v.get("merge", []) if m.get("domain") == stem and "stream" in m]
    print(f"{name}: NHD path from the terminus to the gauge {length:.0f} m (straight line {top.distance(gauge):.0f} m; vertices {gap[0]:.0f} and "
          f"{gap[1]:.0f} m from the terminus and the gauge); model reach {sorted(set(model + merged))} m")


if __name__ == "__main__":
    main()
