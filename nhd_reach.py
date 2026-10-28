#!/usr/bin/env python3
"""A glacier's ice front, the stream path from it to the gauge, and its length, for the plots and the stream HRU.

The ice front (`terminus` layer of shapefiles/nhd.gpkg) is found from the ArcticDEM strips (the YAML's small_meltout dems, else terminus_strips):
inside the start outline of the domain's largest glacier, the cell nearest the gauge in a patch of at least --min-cells cells that is still ice at the end
of the strips: its surface (median of the strips from 2019) stands more than --thickness m above the bed and is still lowering (a trend since
2014 below --lowering m yr-1). Ice that melted out during the record also lowered, but its surface has reached the bed.
The YAML's `terminus` [lon, lat] overrides it, and it is checked against the NHD and the late imagery in the plots.

The path (`reach` layer, the polyline from the front to the gauge; `reach_mapped`, the part NHD maps) is the shortest one along the NHD
flowlines (acquire_nhd.py) between the vertices nearest the front and the gauge, with the unmapped stretches at both ends joined straight.
Its length is printed beside the model reach (stream: length in cases.yaml), which should agree. NHD has no channel width; that has to come
from imagery or the gauge's field measurements.

    ./nhd_reach.py domains/wolverine.yaml
"""

import argparse
import glob
import os

import geopandas as gpd
import networkx as nx
import numpy as np
import rasterio
import yaml
from scipy import ndimage
from shapely.geometry import LineString, Point
from shapely.ops import substring

from domain_config import load_config
from glacier_rasters import height_trend, strip_heights

HERE = os.path.dirname(os.path.abspath(__file__))


def strips_of(c):
    path = (c.get("small_meltout") or {}).get("dems") or c.get("terminus_strips")
    return sorted(glob.glob(os.path.join(HERE, path, "*.tif"))) if path else []


def terminus(c, crs, lowering=-0.3, min_cells=20, thickness=5.0):
    """The ice front as a point in crs, and how it was found."""
    project, name = c["project_dir"], c["domain"]
    if c.get("terminus"):
        return gpd.GeoSeries([Point(*c["terminus"])], crs=4326).to_crs(crs).iloc[0], "YAML terminus"
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id.tif")) as r:
        gid = r.read(1)
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_bedrock_elv.tif")) as r:
        bed = r.read(1).astype(float)
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv.tif")) as r:
        elev, tr = r.read(1).astype(float), r.transform
        ids, counts = np.unique(gid[gid > 0], return_counts=True)
        main = gid == ids[np.argmax(counts)]
        paths = strips_of(c)
        how = "cell of the start outline nearest the gauge"
        keep = main
        if paths:
            years, heights = strip_heights(elev, gid > 0, r, paths)
            if len(years):
                with np.errstate(all="ignore"):
                    late = np.nanmedian(heights[years >= 2019], axis=0)
                active = main & (height_trend(years, heights) < lowering) & (late - bed > thickness)
                label, n = ndimage.label(active, structure=np.ones((3, 3)))
                big = [k for k in range(1, n + 1) if (label == k).sum() >= min_cells]
                if big:
                    keep = np.isin(label, big)
                    how = f"cell nearest the gauge that is still ice and lowering in {len(years)} strips"
    lat, lon = (float(v) for v in c["pour_point"].split("/"))
    rows, cols = np.nonzero(keep)
    xs, ys = tr * (cols + 0.5, rows + 0.5)
    k = np.argmin(((np.array(xs) - lon) * np.cos(np.radians(lat))) ** 2 + (np.array(ys) - lat) ** 2)
    x, y = xs[k], ys[k]
    return gpd.GeoSeries([Point(x, y)], crs=4326).to_crs(crs).iloc[0], how


def model_reach_length(c):
    """The stream length (m) the model's cases give this domain's reach, or None."""
    with open(os.path.join(HERE, "cases.yaml")) as f:
        cases = yaml.safe_load(f)
    name = c["domain"].lower()
    found = [v["stream"]["length"] for v in cases.values() if v.get("domain", "").replace("_general", "") == name and "stream" in v]
    found += [m["stream"]["length"] for v in cases.values() for m in v.get("merge", []) if m.get("domain") == name and "stream" in m]
    return max(found) if found else None


def cut_from_gauge(line, length):
    """The part of the polyline `line` (front to gauge) within `length` m of the gauge; beyond the front it is continued straight."""
    rev = LineString(list(line.coords)[::-1])
    if length <= rev.length:
        return substring(rev, 0, length)
    xy = list(rev.coords)
    a, b = np.array(xy[-2]), np.array(xy[-1])
    d = (b - a) / np.hypot(*(b - a))
    return LineString(xy + [tuple(b + d * (length - rev.length))])


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--lowering", type=float, default=-0.3, help="surface trend (m yr-1) below which ice is taken as still lowering")
    p.add_argument("--thickness", type=float, default=5.0, help="m the late surface stands above the bed for the cell to be ice")
    p.add_argument("--min-cells", type=int, default=20, help="cells of a lowering patch for it to count")
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
    top, how = terminus(c, crs, a.lowering, a.min_cells, a.thickness)
    near = lambda pt: tuple(nodes[np.argmin(np.hypot(nodes[:, 0] - pt.x, nodes[:, 1] - pt.y))])
    start, end = near(top), near(gauge)
    path = nx.shortest_path(graph, start, end, weight="weight")
    mapped = nx.shortest_path_length(graph, start, end, weight="weight")
    gaps = (float(np.hypot(start[0] - top.x, start[1] - top.y)), float(np.hypot(end[0] - gauge.x, end[1] - gauge.y)))
    full = LineString([(top.x, top.y)] + path + [(gauge.x, gauge.y)])
    gpd.GeoDataFrame({"length_m": [full.length], "mapped_m": [mapped], "gap_top_m": [gaps[0]], "gap_gauge_m": [gaps[1]],
                      "straight_m": [float(top.distance(gauge))]}, geometry=[full], crs=crs).to_file(nhd, layer="reach", driver="GPKG")
    gpd.GeoDataFrame({"length_m": [mapped]}, geometry=[LineString(path)], crs=crs).to_file(nhd, layer="reach_mapped", driver="GPKG")
    gpd.GeoDataFrame({"how": [how]}, geometry=[top], crs=crs).to_file(nhd, layer="terminus", driver="GPKG")
    print(f"{name}: ice front by {how}; stream path to the gauge {full.length:.0f} m (NHD maps {mapped:.0f} m, {gaps[0]:.0f} m unmapped at the "
          f"front and {gaps[1]:.0f} m at the gauge; {top.distance(gauge):.0f} m straight); model reach {model_reach_length(c)} m")


if __name__ == "__main__":
    main()
