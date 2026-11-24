#!/usr/bin/env python3
"""Give each GRU of a domain split by split_grus.py a stream HRU and its own reach of a mizuRoute network.

Each GRU's reach is its YAML `grus:` entry's NHD `stream` inside the GRU: length (m), slope (the fall over the length, on the
geographic surface DEM), mean elevation and mid-point; its width is wscale x sqrt(upstream area), as mizuRoute makes it, and it
drains to the reach of the GRU named by the entry's `to` (0: the outlet). The stream HRU of a GRU takes its lowest land HRU's
parameters, soil and forcing (add_stream_hru.py --gru, once per GRU, in turn). Writes <output>/summa_inputs/{attributes,
coldState,trialParams}.nc and forcingFileList.txt, the forcing months to <output>/forcing and <output>/topology.nc.

    ./add_stream_grus.py domains/slate_creek.yaml <settings> <forcing> <output> --first-month 2004-10 --last-month 2026-07
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import geopandas as gpd
import numpy as np
import rasterio
from netCDF4 import Dataset
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, unary_union

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))


def trace(c, r):
    """The line through `points` (lon, lat), on along the NHD flowlines from their nearest point to `to`, less the water bodies it
    crosses where `lakes: false`."""
    nhd = os.path.join(c["project_dir"], "shapefiles", "nhd.gpkg")
    xy = lambda p: gpd.GeoSeries([Point(*p)], crs=4326).to_crs(c["utm_crs"]).iloc[0]
    flow = gpd.read_file(nhd, layer="flowlines").to_crs(c["utm_crs"]).explode(index_parts=False).geometry
    flow = [LineString([q[:2] for q in g.coords]) for g in flow]
    start, end = xy(r["points"][-1]), xy(r["to"])
    last = min(flow, key=lambda g: g.distance(end))
    end = last.interpolate(last.project(end))
    line = min(flow, key=lambda g: g.distance(start))
    path = [(p.x, p.y) for p in map(xy, r["points"])]
    d = line.project(start)
    while True:
        stop = line.project(end) if line.distance(end) < 1 else line.length
        path += [line.interpolate(d).coords[0]] + [q for q in line.coords if d < line.project(Point(q)) < stop] + [line.interpolate(stop).coords[0]]
        if line.distance(end) < 1:
            break
        tail = Point(line.coords[-1])
        line = min((g for g in flow if Point(g.coords[0]).distance(tail) < 1), key=lambda g: g.length, default=None)
        if line is None:
            raise SystemExit(f"the NHD flowlines end before {r['to']}")
        d = 0.0
    out = LineString(path)
    if r.get("lakes") is not False:
        return out
    water = gpd.read_file(nhd, layer="waterbodies").to_crs(c["utm_crs"]).geometry
    water = water[water.area < 1e6]  # not the icefield's ice masses
    return out.difference(unary_union(list(water) + list(yaml_lakes(c))))


def yaml_lakes(c):
    """The YAML's `lakes:`, outlines (lon, lat) of water the NHD lacks, in the domain's UTM."""
    return gpd.GeoSeries([Polygon(q) for q in c.get("lakes", [])], crs=4326).to_crs(c["utm_crs"])


def gru_line(c, k):
    """The reach of GRU k in the domain's UTM: its NHD stream inside the GRU."""
    project, name, crs = c["project_dir"], c["domain"], c["utm_crs"]
    r = c["grus"][k - 1].get("reach")
    if r:  # points of the stream above NHD's (`points`), then NHD's flowlines downstream from the last of them to `to`
        return trace(c, r)
    gru = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{name}_GRUs.shp")).to_crs(crs).set_index("GRU_ID").loc[k].geometry
    flow = gpd.read_file(os.path.join(project, "shapefiles", "nhd.gpkg"), layer="flowlines").to_crs(crs)
    line = unary_union(flow[flow.gnis_name == c["grus"][k - 1]["stream"]].geometry).intersection(gru)
    return linemerge(line) if line.geom_type == "MultiLineString" else line


def reach_parts(c, k, tol=10.0):
    """The reach of GRU k, and its parts within tol m of the NHD flowlines and off them."""
    line = gru_line(c, k)
    near = gpd.read_file(os.path.join(c["project_dir"], "shapefiles", "nhd.gpkg"), layer="flowlines").to_crs(c["utm_crs"]).geometry.buffer(tol).union_all()
    return line, line.intersection(near), line.difference(near)


def reaches(c, wscale):
    """{gru: dict(length, slope, elevation, latitude, longitude, down, width, donor)} from the GRUs, NHD and the surface DEM."""
    project, name = c["project_dir"], c["domain"]
    crs = c["utm_crs"]
    hrus = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{name}_HRUs_elevation.shp"))
    dem = rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_elv.tif"))
    out = {}
    for k, g in enumerate(c["grus"], start=1):
        line = gru_line(c, k)
        pts = [line.interpolate(f, normalized=True) for f in np.linspace(0, 1, 101)]
        ll = gpd.GeoSeries(pts, crs=crs).to_crs(dem.crs)
        z = np.array([v[0] for v in dem.sample([(p.x, p.y) for p in ll])], float)
        mid = gpd.GeoSeries([line.interpolate(0.5, normalized=True)], crs=crs).to_crs(4326).iloc[0]
        lowest = hrus[hrus.GRU_ID == k].sort_values("elev_mean").iloc[0]
        out[k] = dict(length=float(line.length), slope=float((np.percentile(z, 95) - np.percentile(z, 5)) / line.length),
                      elevation=float(z.mean()), latitude=mid.y, longitude=mid.x, down=int(g.get("to", 0)),
                      land=float(hrus[hrus.GRU_ID == k].HRU_area.sum()), donor=int(lowest.HRU_ID))
    up = {}
    def upstream(k):
        if k not in up:
            up[k] = out[k]["land"] + sum(upstream(j) for j in out if out[j]["down"] == k)
        return up[k]
    for k in out:
        out[k]["width"] = wscale * np.sqrt(upstream(k))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML with grus:")
    p.add_argument("settings", help="directory of the domain's attributes, cold state, trial parameters and forcingFileList.txt")
    p.add_argument("forcing", help="directory of its monthly forcing files")
    p.add_argument("output")
    p.add_argument("--attributes", default="attributes.nc")
    p.add_argument("--cold-state", default="coldState.nc")
    p.add_argument("--trial-params", default="trialParams.nc")
    p.add_argument("--first-month", required=True)
    p.add_argument("--last-month", required=True)
    p.add_argument("--wscale", type=float, default=0.001, help="mizuRoute wscale, m m-1")
    a = p.parse_args()
    c = load_config(a.config)
    net = reaches(c, a.wscale)
    settings, forcing = a.settings, a.forcing
    names = dict(attributes=a.attributes, cold=a.cold_state, trial=a.trial_params)
    with tempfile.TemporaryDirectory() as tmp:
        for k, r in net.items():
            step = os.path.join(tmp, f"gru{k}")
            subprocess.run([sys.executable, os.path.join(HERE, "add_stream_hru.py"), settings, forcing, step,
                            "--attributes", names["attributes"], "--cold-state", names["cold"], "--trial-params", names["trial"],
                            "--first-month", a.first_month, "--last-month", a.last_month, "--gru", str(k),
                            "--donor-hru", str(r["donor"]), "--length", f"{r['length']:.1f}", "--slope", f"{r['slope']:.5f}",
                            "--width", f"{r['width']:.3f}", "--elevation", f"{r['elevation']:.1f}",
                            "--latitude", f"{r['latitude']:.5f}", "--longitude", f"{r['longitude']:.5f}"], check=True)
            settings, forcing = os.path.join(step, "summa_inputs"), os.path.join(step, "forcing")
            names = dict(attributes="attributes.nc", cold="coldState.nc", trial="trialParams.nc")
        os.makedirs(os.path.join(a.output, "summa_inputs"), exist_ok=True)
        for f in ("attributes.nc", "coldState.nc", "trialParams.nc", "forcingFileList.txt"):
            shutil.copy(os.path.join(settings, f), os.path.join(a.output, "summa_inputs", f))
        if os.path.exists(os.path.join(a.output, "forcing")):
            shutil.rmtree(os.path.join(a.output, "forcing"))
        shutil.copytree(forcing, os.path.join(a.output, "forcing"))
    segs = sorted(net)
    with Dataset(os.path.join(a.output, "topology.nc"), "w", format="NETCDF4") as d:
        d.createDimension("hru", len(segs))
        d.createDimension("seg", len(segs))
        for name, dim, val, dtype, units in (("hruId", "hru", segs, "i8", "-"),
                                             ("area", "hru", [net[k]["land"] + net[k]["length"] * net[k]["width"] for k in segs], "f8", "m2"),
                                             ("hruToSegId", "hru", segs, "i8", "-"),
                                             ("segId", "seg", segs, "i8", "-"),
                                             ("downSegId", "seg", [net[k]["down"] for k in segs], "i8", "-"),
                                             ("length", "seg", [net[k]["length"] for k in segs], "f8", "m"),
                                             ("slope", "seg", [net[k]["slope"] for k in segs], "f8", "-")):
            v = d.createVariable(name, dtype, (dim,))
            v.units = units
            v[:] = val
        d.description = "one reach per GRU, written by add_stream_grus.py"
    for k in segs:
        r = net[k]
        print(f"GRU {k} reach -> {r['down']}: {r['length']:.0f} m long, {r['width']:.1f} m wide, slope {r['slope']:.4f}, "
              f"{r['elevation']:.0f} m, donor HRU {r['donor']}")


if __name__ == "__main__":
    main()
