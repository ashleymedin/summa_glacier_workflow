#!/usr/bin/env python3
"""Plot a basin's setup: surface contours and hillshade, glacier outlines and the room they may advance into, the basin and its HRUs,
and the gauge, for each setup (the general domain and the added-data domain) of each basin.

One panel per basin (rows) and setup (columns), in the domain's UTM grid. Layers, from the domain folders the setup steps write:

  surface and contours   attributes/elevation/dem/domain_<name>_glacier_elv_utm.tif, every --contour metres
  glacier outlines       attributes/glaciers/domain_<name>_rgi_id.tif (the start outlines, purple)
  advance room           domain_<name>_rgi_id_extend.tif beyond them (pink), the cells a glacier may flow into
  basin, HRUs, gauge     shapefiles/river_basins, shapefiles/catchment, and the YAML's pour_point

and, with the flags, --grids (the extent of each glacier's flow-model grid), --stations (the USGS weather stations in
observations/stations; the added-data panels only) and --streams (the NHD streams and lakes of shapefiles/nhd.gpkg, acquire_nhd.py, inside the basin,
and the YAML's terminus-to-gauge windows, dashed).

    ./plot_basin_setup.py figs/setups.pdf
    ./plot_basin_setup.py figs/setups_streams.pdf --basins wolverine --setups added --streams --stations
"""

import argparse
import glob
import os

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import netCDF4 as nc4
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from rasterio.features import geometry_mask
from rasterio.warp import Resampling, reproject
from shapely.geometry import Point, box

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
PURPLE, PINK, RED, BLUE, GREEN, ORANGE = "#7b2d8e", "#e8629c", "#c0392b", "#1f78b4", "#1a9850", "#e08214"


def on_grid(path, like):
    """A raster resampled (nearest) onto the grid of the open raster `like`."""
    out = np.zeros(like.shape, dtype=np.float64)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), out, dst_transform=like.transform, dst_crs=like.crs, resampling=Resampling.nearest)
    return out


def panel(ax, config, a, setup):
    c = load_config(config)
    project, name = c["project_dir"], c["domain"]
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv_utm.tif")) as r:
        dem = r.read(1, masked=True).filled(np.nan).astype(float)
        tr, crs, shape = r.transform, r.crs, r.shape
        like = r
        glc = on_grid(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id.tif"), like) > 0
        ext = on_grid(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id_extend.tif"), like) > 0
    basin = gpd.read_file(glob.glob(os.path.join(project, "shapefiles", "river_basins", "*.shp"))[0]).to_crs(crs)
    hrus = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{name}_HRUs_elevation.shp")).to_crs(crs)
    outside = ~geometry_mask(list(basin.geometry), transform=tr, invert=True, out_shape=shape)
    x0, y0, x1, y1 = basin.total_bounds
    pad = 0.06 * max(x1 - x0, y1 - y0)
    extent = (tr.c, tr.c + tr.a * shape[1], tr.f + tr.e * shape[0], tr.f)
    rows, cols = np.nonzero(np.isfinite(dem))  # the surface's valid cells; beyond them the raster is empty
    valid = (tr.c + tr.a * (cols.min() + 1), tr.f + tr.e * (rows.max() - 1), tr.c + tr.a * (cols.max() - 1), tr.f + tr.e * (rows.min() + 1))
    left, bottom, right, top = max(x0 - pad, valid[0]), max(y0 - pad, valid[1]), min(x1 + pad, valid[2]), min(y1 + pad, valid[3])
    xs = tr.c + tr.a * (np.arange(shape[1]) + 0.5)
    ys = tr.f + tr.e * (np.arange(shape[0]) + 0.5)
    filled = np.where(np.isfinite(dem), dem, np.nanmin(dem))
    shade = LightSource(315, 40).hillshade(filled, vert_exag=2, dx=abs(tr.a), dy=abs(tr.e))
    ax.imshow(shade, cmap="gray", vmin=0.2, vmax=1.0, extent=extent, zorder=0)
    levels = np.arange(np.floor(np.nanmin(dem) / a.contour) * a.contour, np.nanmax(dem) + a.contour, a.contour)
    index = levels % (5 * a.contour) == 0
    ax.contour(xs, ys, dem, levels=levels[~index], colors="#3a3a3a", linewidths=0.4, zorder=1)
    labelled = ax.contour(xs, ys, dem, levels=levels[index], colors="#1a1a1a", linewidths=0.9, zorder=1)
    for text in ax.clabel(labelled, fontsize=6, fmt="%d", inline=True, inline_spacing=4):
        text.set_zorder(12)
    ax.imshow(np.where(outside, 1.0, np.nan), cmap="gray_r", vmin=0, vmax=1.3, alpha=0.55, extent=extent, zorder=2)
    ax.contourf(xs, ys, (ext & ~glc).astype(float), levels=[0.5, 1.5], colors=[PINK], alpha=0.45, zorder=3)
    ax.contour(xs, ys, (ext & ~glc).astype(float), levels=[0.5], colors=[PINK], linewidths=1.0, zorder=4)
    ax.contour(xs, ys, (glc & ~outside).astype(float), levels=[0.5], colors=[PURPLE], linewidths=1.3, zorder=5)
    hrus.boundary.plot(ax=ax, color=GREEN, linewidth=1.8, zorder=6)
    basin.boundary.plot(ax=ax, color="black", linewidth=1.8, zorder=7)
    lat, lon = (float(v) for v in c["pour_point"].split("/"))
    gx, gy = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(crs).iloc[0].coords[0]
    ax.plot(gx, gy, marker="^", ms=15, mfc=RED, mec="white", mew=1.5, ls="none", zorder=13)
    if a.grids:
        from glacier_cold_state import grid_transforms
        tf, _ = grid_transforms(project, name, c["utm_epsg"])
        with nc4.Dataset(os.path.join(project, "settings", "SUMMA", "attributes_glac.nc")) as d:
            nx, ny, ids = (np.asarray(d[v][:, 0]).astype(int) for v in ("nx", "ny", "gridId"))
        for k, g in enumerate(ids):
            t = tf[int(g)]
            ax.add_patch(Rectangle((t.c, t.f + t.e * ny[k]), abs(t.a) * nx[k], abs(t.e) * ny[k], fill=False, ec=ORANGE, lw=1.2, ls="-", zorder=8))
    if a.stations and setup == "added":  # the stations belong to the added-data setup
        source = os.path.join(HERE, c["seed_from"]) if c.get("seed_from") else project  # the stations belong to the added-data domain
        st = pd.read_csv(os.path.join(source, "observations", "stations", "weatherStationLocations.csv"))
        st = st[st["Location"] == name]
        for _, s in st.iterrows():
            px, py = gpd.GeoSeries([Point(s["Longitude"], s["Latitude"])], crs=4326).to_crs(crs).iloc[0].coords[0]
            ax.plot(px, py, marker="s", ms=7, mfc="#f1c40f", mec="black", mew=1.0, ls="none", zorder=14)
            ax.annotate(f"{int(s['Elevation'])} m", (px, py), xytext=(8, 6), textcoords="offset points", fontsize=6, zorder=14)
    if a.streams:
        nhd = os.path.join(project, "shapefiles", "nhd.gpkg")
        if os.path.exists(nhd):
            window = gpd.GeoSeries([box(left, bottom, right, top)], crs=crs).iloc[0]
            for layer, keep, kw in (("waterbodies", (390, 436), dict(color="#a6cee3", edgecolor=BLUE, linewidth=0.6)),  # lakes, ponds, reservoirs; not NHD's ice masses
                                    ("flowlines", (460,), dict(color=BLUE, linewidth=1.4)),
                                    ("flowlines", (558,), dict(color=BLUE, linewidth=0.7, linestyle=":"))):  # artificial paths, through lakes and ice
                gdf = gpd.read_file(nhd, layer=layer).to_crs(crs).rename(columns=str.lower)
                gdf = gpd.clip(gdf[gdf["ftype"].isin(keep)], basin.geometry.union_all())  # only what is in the basin
                if len(gdf):
                    gdf.plot(ax=ax, zorder=9, **kw)
        for lake in (c.get("observations") or {}).get("lake_area", []):
            w, s0, e, n = lake["box"]
            bx = gpd.GeoSeries([box(w, s0, e, n)], crs=4326).to_crs(crs).iloc[0].bounds
            if lake["name"].endswith("reach"):
                ax.add_patch(Rectangle((bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1], fill=False, ec=ORANGE, lw=1.3, ls="--", zorder=9))
    ax.set_xlim(left, right)
    ax.set_ylim(bottom, top)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    # scale bar and north arrow
    length = 1000 if (right - left) < 9000 else 2000
    bx0, by0 = left + 0.05 * (right - left), bottom + 0.05 * (top - bottom)
    ax.add_patch(Rectangle((bx0 - 0.015 * (right - left), by0 - 0.012 * (top - bottom)), length + 0.03 * (right - left), 0.06 * (top - bottom),
                           fc="white", alpha=0.75, ec="none", zorder=11))
    ax.plot([bx0, bx0 + length], [by0, by0], color="black", lw=3, zorder=12, solid_capstyle="butt")
    ax.text(bx0 + length / 2, by0 + 0.014 * (top - bottom), f"{length // 1000} km", ha="center", fontsize=7, zorder=12)
    nx0, ny0 = right - 0.07 * (right - left), top - 0.13 * (top - bottom)
    ax.annotate("N", (nx0, ny0 + 0.09 * (top - bottom)), (nx0, ny0), ha="center", va="bottom", fontsize=8,
                arrowprops=dict(arrowstyle="-|>", color="black"), zorder=11)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("output", help="figure to write (.pdf or .png)")
    p.add_argument("--basins", nargs="+", default=["wolverine", "gulkana"])
    p.add_argument("--setups", nargs="+", choices=("general", "added"), default=["general", "added"])
    p.add_argument("--contour", type=float, default=100.0, help="contour interval, m")
    p.add_argument("--grids", action="store_true", help="the extent of each glacier's flow-model grid")
    p.add_argument("--stations", action="store_true", help="the USGS weather stations")
    p.add_argument("--streams", action="store_true", help="the NHD streams and lakes, and the terminus-to-gauge windows of the YAML")
    a = p.parse_args()
    fig, axes = plt.subplots(len(a.basins), len(a.setups), figsize=(max(4.6 * len(a.setups), 6.6), 5.6 * len(a.basins)), squeeze=False)
    for i, basin in enumerate(a.basins):
        for j, setup in enumerate(a.setups):
            config = os.path.join(HERE, "domains", f"{basin}{'_general' if setup == 'general' else ''}.yaml")
            panel(axes[i, j], config, a, setup)
            label = "general setup" if setup == "general" else "added-data setup"
            axes[i, j].set_title(f"{basin.capitalize()}, {label}", fontsize=10)
    handles = [Line2D([], [], color="#3a3a3a", lw=0.5, label=f"{a.contour:g} m contours (labelled every {5 * a.contour:g} m)"),
               Line2D([], [], color=PURPLE, lw=1.3, label="glacier outline at the start"),
               Patch(fc=PINK, ec=PINK, alpha=0.5, label="room to advance"),
               Line2D([], [], color="black", lw=1.8, label="basin"), Line2D([], [], color=GREEN, lw=1.8, label="HRUs"),
               Line2D([], [], marker="^", ls="none", mfc=RED, mec="white", ms=8, label="gauge")]
    if a.grids:
        handles.append(Line2D([], [], color=ORANGE, lw=1.2, label="flow-model grid"))
    if a.stations and setup == "added":  # the stations belong to the added-data setup
        handles.append(Line2D([], [], marker="s", ls="none", mfc="#f1c40f", mec="black", ms=6, label="weather station"))
    if a.streams:
        handles += [Line2D([], [], color=BLUE, lw=1.4, label="stream (NHD; dotted: through lakes and ice)"), Patch(fc="#a6cee3", ec=BLUE, label="lake (NHD)"),
                    Line2D([], [], color=ORANGE, lw=1.3, ls="--", label="terminus-to-gauge window")]
    fig.legend(handles=handles, loc="lower center", ncol=min(len(handles), 2 if len(a.setups) == 1 else 5), fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1), h_pad=3.0)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    fig.savefig(a.output, dpi=250)
    print("wrote", a.output)


if __name__ == "__main__":
    main()
