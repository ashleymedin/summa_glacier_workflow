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
from scipy.ndimage import distance_transform_edt, gaussian_filter, label
from matplotlib import patheffects
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from rasterio.features import geometry_mask
from rasterio.warp import Resampling, reproject
from shapely.geometry import LineString, Point, Polygon, box

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
PURPLE, PINK, RED, BLUE, GREEN, ORANGE, BROWN = "#7b2d8e", "#e8629c", "#c0392b", "#1f78b4", "#1a9850", "#e08214", "#a8773f"
NAVY = "#08306b"  # the stream from the ice front, or the reaches of the GRUs
YELLOW = "#ffd400"  # the proglacial image's area
SKY = "#56b4e9"  # the on-ice station
CONTOUR, CONTOUR_INDEX = "#8a8a8a", "#5a5a5a"  # contour lines and the labelled ones, the same in both figures
OUTLINE_LW, DEBRIS_EDGE = 0.5, "#6b3a12"  # glacier, debris and advance-room outlines, one width in both figures
HRU_LW = 1.8  # the HRU lines, and the observed outlines of plot_glacier_end.py
DIM_ALPHA = 0.15  # opacity of the grey over the hillshade, the same in both figures
HILL_VMIN = -0.3  # the hillshade's black point; below 0 its darkest slopes stay mid-grey
VERT_EXAG = 1.0  # hillshade relief exaggeration, the same in both figures
ICE_ALPHA = 0.55  # its opacity over the hillshade, the same in both figures
ICE_FILL = "#d9c3e3"  # glacier ice, a light shade of PURPLE (here the start, in plot_glacier_end.py the model's end)
HALO = [patheffects.withStroke(linewidth=2.0, foreground="white")]  # station labels stay legible on dark hillshade
ON_ICE_SITES = ("B",)  # Site B, the on-ice weather station of the 2024 campaign


def legend_below(fig, axes, handles, ncol):
    """The legend just under the lowest panel, whose equal aspect leaves its box short of the space tight_layout gave it."""
    fig.canvas.draw()
    bottom = min(ax.get_position().y0 for ax in axes.flat)
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, bottom - 0.01), ncol=ncol, fontsize=7.5, frameon=False)


def on_ice_sites(source):
    """The on-ice weather stations of the campaign in a domain's observations, as dicts of lat, lon and elev; none if it has no campaign."""
    path = os.path.join(source, "observations", "campaigns", "wilson_2024", "site_locations.csv")
    if not os.path.exists(path):
        return []
    t = pd.read_csv(path, skipinitialspace=True)
    t.columns = ["site", "lat", "lon", "elev"]
    return [{"lat": float(r.lat), "lon": float(r.lon), "elev": str(r.elev).strip()} for r in t.itertuples() if str(r.site).strip() in ON_ICE_SITES]


STAKE_SITES = os.path.join(HERE, "data", "external", "USGS_massBalance", "Glacier_Mass_Balance_Sites", "Glacier_Mass_Balance_Data_Sites.csv")  # USGS release 10.5066/F7HD7SRF
STAKE_MIN_ELEV = 800.0  # correct_forcing_to_station.py --stake-min-elev


def used_stakes(source, c, name):
    """The mass-balance stakes with a winter balance from the first water year of the run on, as (lon, lat, fitted): fitted when the
    stake lies above STAKE_MIN_ELEV, where the added-data forcing correction fits its winter balance (below it, winter melt and rain
    leave the winter balance short of the snowfall, and the stake enters only the USGS glacier-wide balances).  Positions are the
    USGS site locations; none without the site file or stake record."""
    if not c.get("stakes") or not os.path.exists(STAKE_SITES):
        return []
    rec = pd.read_csv(os.path.join(source, c["stakes"]))
    first = int(str(c.get("cold_start", "1900-10"))[:4]) + 1  # water year of the first forcing October
    rec = rec[(rec["Year"] >= first) & rec["bw"].notna()].assign(site_name=lambda t: t["site_name"].astype(str).str.strip())
    used = set(rec["site_name"])
    fitted = set(rec.loc[rec["elevation"] > STAKE_MIN_ELEV, "site_name"])
    sites = pd.read_csv(STAKE_SITES)
    sites = sites[(sites["Glacier"] == name) & (sites["Type"] == "Glaciological")]
    sites = sites.assign(site_name=sites["site_name"].astype(str).str.strip()).drop_duplicates("site_name")
    missing = used - set(sites["site_name"])
    if missing:
        print(f"{name}: no USGS position for stakes {sorted(missing)}")
    return [(float(r.longitude), float(r.latitude), r.site_name in fitted) for r in sites.itertuples() if r.site_name in used]


def on_grid(path, like):
    """A raster resampled (nearest) onto the grid of the open raster `like`."""
    out = np.zeros(like.shape, dtype=np.float64)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), out, dst_transform=like.transform, dst_crs=like.crs, resampling=Resampling.nearest)
    return out


def soft(mask, sigma=1.0):
    """A boolean raster as a blurred 0-1 field, so its 0.5 contour is a smooth outline (display only)."""
    return gaussian_filter(mask.astype(float), sigma)


def chaikin(geom, n=3):
    """A line or polygon with its corners cut n times (display only); the staircase of a raster outline becomes a smooth curve."""
    def cut(xy, closed):
        for _ in range(n):
            xy = np.asarray(xy)
            a, b = (xy, np.roll(xy, -1, axis=0)) if closed else (xy[:-1], xy[1:])
            q = np.empty((2 * len(a), 2))
            q[0::2], q[1::2] = 0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b
            xy = q if closed else np.vstack([xy[:1], q, xy[-1:]])
        return xy
    if geom.geom_type in ("MultiPolygon", "GeometryCollection", "MultiLineString"):
        return geom.__class__([chaikin(g, n) for g in geom.geoms])
    if geom.geom_type == "Polygon":
        return Polygon(cut(geom.exterior.coords[:-1], True), [cut(r.coords[:-1], True) for r in geom.interiors])
    return LineString(cut(geom.coords, geom.coords[0] == geom.coords[-1]))


def panel(ax, config, a, setup, keep_out, letter, front_project=None):
    c = load_config(config)
    project, name = c["project_dir"], c["domain"]
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv_utm.tif")) as r:
        dem = r.read(1, masked=True).filled(np.nan).astype(float)
        tr, crs, shape = r.transform, r.crs, r.shape
        like = r
        glc = on_grid(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id.tif"), like) > 0
        ext = on_grid(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id_extend.tif"), like) > 0
        debris = on_grid(os.path.join(project, "attributes", "glaciers", f"domain_{name}_domain_type.tif"), like) == 4
    basin = gpd.read_file(glob.glob(os.path.join(project, "shapefiles", "river_basins", "*.shp"))[0]).to_crs(crs)
    hrus = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{name}_HRUs_elevation.shp")).to_crs(crs)
    smooth_hrus = hrus.set_geometry(hrus.geometry.map(chaikin))
    smooth_basin = basin.set_geometry(basin.geometry.map(chaikin))
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
    shade = LightSource(315, 40).hillshade(filled, vert_exag=VERT_EXAG, dx=abs(tr.a), dy=abs(tr.e))
    ax.imshow(shade, cmap="gray", vmin=HILL_VMIN, vmax=1.0, extent=extent, zorder=0)
    levels = np.arange(np.floor(np.nanmin(dem) / a.contour) * a.contour, np.nanmax(dem) + a.contour, a.contour)
    index = levels % (5 * a.contour) == 0
    ax.contour(xs, ys, dem, levels=levels[~index], colors=CONTOUR, linewidths=0.4, zorder=1)
    labelled = ax.contour(xs, ys, dem, levels=levels[index], colors=CONTOUR_INDEX, linewidths=0.8, zorder=1)
    place = []  # one label per index contour, at its rightmost vertex outside both setups' basins, so a and b (c and d) match
    free = ~geometry_mask(list(keep_out), transform=tr, invert=True, out_shape=shape)
    for segs in labelled.allsegs:
        best = None
        for seg in segs:
            for x, y in seg[::4]:
                col, row = int((x - tr.c) / tr.a), int((y - tr.f) / tr.e)
                if left < x < right - 0.04 * (right - left) and bottom < y < top and 0 <= row < shape[0] and 0 <= col < shape[1] and free[row, col]:
                    if best is None or x > best[0]:
                        best = (x, y)
        place.append(best)
    for k, best in enumerate(place):
        if best is not None:
            for text in ax.clabel(labelled, levels=[labelled.levels[k]], fontsize=6.5, fmt="%d", manual=[best], inline=True, inline_spacing=3):
                text.set_zorder(12)
    ax.imshow(np.ones(shape), cmap="gray_r", vmin=0, vmax=1.3, alpha=DIM_ALPHA, extent=extent, zorder=0.2)  # the hillshade dimmed alike inside and outside the basin
    ax.contourf(xs, ys, soft(glc & ~outside), levels=[0.5, 1.5], colors=[ICE_FILL], alpha=ICE_ALPHA, zorder=0.4)
    if debris.any():
        ax.contourf(xs, ys, soft(debris & ~outside), levels=[0.5, 1.5], colors=[BROWN], alpha=0.5, zorder=0.5)
        ax.contour(xs, ys, soft(debris & ~outside), levels=[0.5], colors=[DEBRIS_EDGE], linewidths=OUTLINE_LW, zorder=3)
    ax.contourf(xs, ys, soft(ext & ~glc, 0.45), levels=[0.5, 1.5], colors=[PINK], alpha=0.45, zorder=3)
    ax.contour(xs, ys, soft(ext & ~glc, 0.45), levels=[0.5], colors=[PINK], linewidths=OUTLINE_LW, zorder=4)
    ids = on_grid(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id.tif"), like).astype(int)
    if a.glaciers:  # advance room of a cell or two, lost in the blur
        lab, n = label(ext & ~glc, structure=np.ones((3, 3)))
        for k in range(1, n + 1):
            if (lab == k).sum() <= 8:
                row, col = np.nonzero(lab == k)
                ax.plot(xs[col].mean(), ys[row].mean(), marker="s", ms=4.5, mfc=PINK, mec="black", mew=0.5, ls="none", zorder=14)
    for m in [ids == g for g in np.unique(ids[glc & ~outside])] if a.glaciers else [glc]:  # outline traced on cell edges, clipped to the basin polygon
        start = ax.contour(xs, ys, soft(m, 0.6 if a.glaciers else 1.0), levels=[0.5], linewidths=0)
        gpd.GeoSeries([LineString(seg).intersection(smooth_basin.geometry.union_all()) for seg in start.allsegs[0] if len(seg) > 1]).plot(ax=ax, color=PURPLE, linewidth=1.1 if a.glaciers else OUTLINE_LW, zorder=5)
    if a.glaciers:
        for g in np.unique(ids[glc & ~outside]):
            lab, n = label(ids == g, structure=np.ones((3, 3)))
            if n == 0:
                continue
            part = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1
            if part.sum() >= 25 and (part & ~outside).mean() > 0.5 * part.mean():
                dist = distance_transform_edt(part)
                row, col = np.unravel_index(np.argmax(dist), dist.shape)
                ax.annotate(f"{g // 100000}.{g % 100000:05d}", (xs[col], ys[row]), fontsize=6.5, color=PURPLE, weight="bold", ha="center", va="center", zorder=15, path_effects=HALO)
    smooth_hrus.boundary.plot(ax=ax, color=GREEN, linewidth=HRU_LW, zorder=6)
    smooth_basin.boundary.plot(ax=ax, color="black", linewidth=1.8, zorder=7)
    split = os.path.join(project, "shapefiles", "catchment", f"{name}_GRUs.shp")
    if os.path.exists(split):  # the GRUs of split_grus.py, labelled by id
        grus = gpd.read_file(split).to_crs(crs)
        grus.set_geometry(grus.geometry.map(chaikin)).boundary.plot(ax=ax, color="black", linewidth=1.0, ls="--", zorder=7)
        for g in grus.itertuples():
            pt = g.geometry.representative_point()
            ax.annotate(f"G{g.GRU_ID}", (pt.x, pt.y), fontsize=9, weight="bold", ha="center", zorder=15,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8, lw=0))
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
    source = os.path.join(HERE, c["seed_from"]) if c.get("seed_from") else project  # the observations belong to the added-data domain
    if a.stations and setup == "added":  # the weather stations the added-data forcing is corrected to
        stations = os.path.join(source, "observations", "stations")
        st = pd.read_csv(os.path.join(stations, "weatherStationLocations.csv"))
        # the location list is USGS's for all its sites, the stream gauges and stations without a record among them;
        # only a station with its record in the folder (named by its elevation) forces the model
        st = st[(st["Location"] == name) & st["Elevation"].map(lambda e: os.path.isdir(os.path.join(stations, f"{int(e)}")))]
        for _, s in st.iterrows():
            px, py = gpd.GeoSeries([Point(s["Longitude"], s["Latitude"])], crs=4326).to_crs(crs).iloc[0].coords[0]
            ax.plot(px, py, marker="s", ms=7, mfc="#f1c40f", mec="black", mew=1.0, ls="none", zorder=14)
            ax.annotate(f"{int(s['Elevation'])} m", (px, py), xytext=(8, 6), textcoords="offset points", fontsize=6, zorder=14, path_effects=HALO)
        for lon, lat, fitted in used_stakes(source, c, name):  # white: winter balance fitted by the forcing correction; grey: glacier-wide balance only
            px, py = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(crs).iloc[0].coords[0]
            ax.plot(px, py, marker="o", ms=4.5, mfc="white" if fitted else "#555555", mec="black", mew=1.0, ls="none", zorder=15)
    if a.stations and setup == "added":  # the on-ice station of Wilson et al. (2026), which sets the glacier wind and cooling of both setups
        for site in on_ice_sites(source):
            px, py = gpd.GeoSeries([Point(site["lon"], site["lat"])], crs=4326).to_crs(crs).iloc[0].coords[0]
            ax.plot(px, py, marker="D", ms=7, mfc=SKY, mec="black", mew=1.0, ls="none", zorder=14)
            ax.annotate(f"{site['elev']} m", (px, py), xytext=(8, 6), textcoords="offset points", fontsize=6, zorder=14, path_effects=HALO)
    if a.reaches and not c.get("grus"):
        nhd = os.path.join(front_project or project, "shapefiles", "nhd.gpkg")  # the observed ice front is the same on both setups: the added-data domain's
        if os.path.exists(nhd):
            full = gpd.read_file(nhd, layer="reach").to_crs(crs).geometry.iloc[0]
            mapped = gpd.read_file(nhd, layer="reach_mapped").to_crs(crs)
            ax.plot(*full.xy, color=NAVY, lw=1.6, ls=":", zorder=15)
            mapped.plot(ax=ax, color=NAVY, linewidth=2.8, zorder=15)
    if a.reaches and (c.get("main_glacier") or name in ("Wolverine", "Gulkana")):
        nhd = os.path.join(front_project or project, "shapefiles", "nhd.gpkg")
        if os.path.exists(nhd):
            tf = gpd.read_file(nhd, layer="terminus").to_crs(crs).geometry.iloc[0]
            ax.plot(tf.x, tf.y, marker="o", ms=9, mfc="none", mec="#f1c40f", mew=2.2, ls="none", zorder=16)
    if a.reaches and c.get("grus"):  # the reach of each GRU (add_stream_grus.py), labelled by id; dotted off the NHD lines
        from add_stream_grus import reach_parts
        for k in range(1, len(c["grus"]) + 1):
            line, on, off = reach_parts(c, k)
            for geom, kw in ((on, dict(lw=2.8)), (off, dict(lw=1.6, ls=":"))):
                for part in getattr(geom, "geoms", [geom]):
                    if part.length > 0:
                        ax.plot(*part.xy, color=NAVY, zorder=15, **kw)
            mid = line.interpolate(0.35, normalized=True)
            ax.plot(mid.x, mid.y, marker="o", ms=13, mfc="white", mec=NAVY, mew=1.4, ls="none", zorder=17)
            ax.annotate(f"R{k}", (mid.x, mid.y), ha="center", va="center", fontsize=7, zorder=18)
    if a.network and c.get("stream_network"):
        import json
        net = json.load(open(os.path.join(HERE, c["stream_network"])))
        for rid, r in net["reaches"].items():
            px, py = gpd.GeoSeries([Point(r["longitude"], r["latitude"])], crs=4326).to_crs(crs).iloc[0].coords[0]
            ax.plot(px, py, marker="o", ms=11, mfc="white", mec="#08306b", mew=1.4, ls="none", zorder=17)
            ax.annotate(f"R{rid}", (px, py), ha="center", va="center", fontsize=6, zorder=18)
        for g in net["grus"]:
            px, py = gpd.GeoSeries([Point(g["longitude"], g["latitude"])], crs=4326).to_crs(crs).iloc[0].coords[0]
            ax.plot(px, py, marker="*", ms=11, mfc="#b2df8a", mec="black", mew=0.8, ls="none", zorder=17)
            ax.annotate(f"G{g['id']}", (px, py), xytext=(6, 4), textcoords="offset points", fontsize=6, zorder=18)
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
        from plot_proglacial import SCENES, epsg, window as image_window
        key = os.path.basename(config).replace(".yaml", "").replace("_general", "").replace("_grus", "")
        if key in SCENES and setup == a.setups[-1]:
            ib = gpd.GeoSeries([box(*image_window(key))], crs=epsg(key)).to_crs(crs)  # plot_proglacial.py's image
            ib.boundary.plot(ax=ax, color=YELLOW, linewidth=1.8, linestyle="--", zorder=16)
    ax.set_xlim(left, right)
    ax.set_ylim(bottom, top)
    ax.text(0.02, 0.98, f"({letter})", transform=ax.transAxes, ha="left", va="top", fontsize=11, fontweight="bold", zorder=20,
            bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
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
                arrowprops=dict(arrowstyle="-|>", color="black"), zorder=21, path_effects=HALO)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("output", help="figure to write (.pdf or .png)")
    p.add_argument("--basins", nargs="+", default=["wolverine", "gulkana"])
    p.add_argument("--setups", nargs="+", choices=("general", "added"), default=["general", "added"])
    p.add_argument("--contour", type=float, default=100.0, help="contour interval, m")
    p.add_argument("--grids", action="store_true", help="the extent of each glacier's flow-model grid")
    p.add_argument("--stations", action="store_true", help="the USGS weather stations")
    p.add_argument("--network", action="store_true", help="the YAML's stream_network: its reaches (R) and tributary GRUs (G) at their positions")
    p.add_argument("--reaches", action="store_true", help="the NHD stream from the recent ice front to the gauge, or each GRU's reach")
    p.add_argument("--glaciers", action="store_true", help="each RGI glacier's outline apart and its id, instead of the ice's outline")
    p.add_argument("--streams", action="store_true", help="the NHD streams and lakes, and the terminus-to-gauge windows of the YAML")
    p.add_argument("--split", action="store_true", help="the setups in their GRUs (<basin>_grus.yaml, <basin>_general_grus.yaml) where there are")
    a = p.parse_args()
    fig, axes = plt.subplots(len(a.basins), len(a.setups), figsize=(max(4.6 * len(a.setups), 6.6), 5.6 * len(a.basins)), squeeze=False)
    from plot_proglacial import SCENES
    used = []
    for i, basin in enumerate(a.basins):
        configs = {st: os.path.join(HERE, "domains", f"{basin}{'_general' if st == 'general' else ''}.yaml") for st in ("general", "added")}
        if a.split and os.path.exists(os.path.join(HERE, "domains", f"{basin}_grus.yaml")):
            configs["added"] = os.path.join(HERE, "domains", f"{basin}_grus.yaml")
        if a.split and os.path.exists(os.path.join(HERE, "domains", f"{basin}_general_grus.yaml")):
            configs["general"] = os.path.join(HERE, "domains", f"{basin}_general_grus.yaml")
        configs = {st: cfg for st, cfg in configs.items() if os.path.exists(cfg)}  # a basin without glaciers has one setup
        keep_out = [g for st, cfg in configs.items() for g in gpd.read_file(glob.glob(os.path.join(load_config(cfg)["project_dir"], "shapefiles", "river_basins", "*.shp"))[0]).to_crs(32606).geometry]
        for j, setup in enumerate(a.setups):
            config = configs[setup]
            used.append(config)
            keep_crs = load_config(config)["utm_crs"]
            panel(axes[i, j], config, a, setup, [g for g in gpd.GeoSeries(keep_out, crs=32606).to_crs(keep_crs)], "abcdefgh"[i * len(a.setups) + j],
                  load_config(configs["added"])["project_dir"] if "added" in configs else None)
            kind = "general setup" if setup == "general" else "added-data setup" if "general" in configs else "setup"
            axes[i, j].set_title(f"{basin.replace('_', ' ').title()}, {kind}", fontsize=10)
    confs = [load_config(cfg) for cfg in used]
    glaciers = [c for c in confs if c.get("main_glacier") or c["domain"] in ("Wolverine", "Gulkana")]
    grus = any(c.get("grus") for c in confs)
    debris = False
    for c in glaciers:
        kind, modelled = (rasterio.open(os.path.join(c["project_dir"], "attributes", "glaciers", f"domain_{c['domain']}_{r}.tif")).read(1) for r in ("domain_type", "rgi_id_extend"))
        debris |= bool(((kind == 4) & (modelled > 0)).any())
    stakes = [p for c in confs for p in used_stakes(os.path.join(HERE, c["seed_from"]) if c.get("seed_from") else c["project_dir"], c, c["domain"])]
    stakes_low = any(not fitted for _, _, fitted in stakes)
    boxes = any(l["name"].endswith("reach") for c in confs for l in (c.get("observations") or {}).get("lake_area", []))
    handles = [Line2D([], [], color=CONTOUR, lw=0.5, label=f"{a.contour:g} m contours (labelled every {5 * a.contour:g} m)")]
    if glaciers:
        handles.append(Patch(fc=ICE_FILL, ec=PURPLE, lw=OUTLINE_LW, label="glacier at the start"))
        if debris:
            handles.append(Patch(fc=BROWN, ec=DEBRIS_EDGE, alpha=0.6, label="debris-covered ice"))
        handles.append(Patch(fc=PINK, ec=PINK, lw=OUTLINE_LW, alpha=0.5, label="room to advance"))
    handles.append(Line2D([], [], color="black", lw=1.8, label="basin"))
    if grus:
        handles.append(Line2D([], [], color="black", lw=1.0, ls="--", label="GRUs (G)"))
    handles += [Line2D([], [], color=GREEN, lw=HRU_LW, label="HRUs"), Line2D([], [], marker="^", ls="none", mfc=RED, mec="white", ms=8, label="gauge")]
    if a.grids:
        handles.append(Line2D([], [], color=ORANGE, lw=1.2, label="flow-model grid"))
    if a.stations and setup == "added":  # the stations belong to the added-data setup
        handles.append(Line2D([], [], marker="s", ls="none", mfc="#f1c40f", mec="black", ms=6, label="weather station"))
        if stakes:
            handles.append(Line2D([], [], marker="o", ls="none", mfc="white", mec="black", ms=4.5, label="mass-balance stake"))
        if stakes_low:
            handles.append(Line2D([], [], marker="o", ls="none", mfc="#555555", mec="black", ms=4.5, label=f"stake below {STAKE_MIN_ELEV:,.0f} m"))
    if a.stations and any(on_ice_sites(c["project_dir"]) for c in confs):
        handles.append(Line2D([], [], marker="D", ls="none", mfc=SKY, mec="black", ms=6, label="on-ice weather station"))
    if a.reaches:
        handles.append(Line2D([], [], color=NAVY, lw=2.8, label="stream reach (R) of each GRU" if grus and not any(not c.get("grus") for c in confs) else "stream, ice front to gauge" + (", or reach (R) of each GRU" if grus else "")))
        handles[-1].set_label(handles[-1].get_label() + " (dotted: not on NHD)")
    if a.reaches and glaciers:
        handles.append(Line2D([], [], marker="o", ls="none", mfc="none", mec="#f1c40f", mew=2.2, ms=9, label="recent ice front"))
    if a.network:
        handles += [Line2D([], [], marker="o", ls="none", mfc="white", mec="#08306b", ms=9, label="network reach (R)"),
                    Line2D([], [], marker="*", ls="none", mfc="#b2df8a", mec="black", ms=11, label="tributary GRU (G)")]
    if a.streams:
        handles += [Line2D([], [], color=BLUE, lw=1.4, label="stream (NHD; dotted: through lakes and ice)"), Patch(fc="#a6cee3", ec=BLUE, label="lake (NHD)")]
        if boxes:
            handles.append(Line2D([], [], color=ORANGE, lw=1.3, ls="--", label="terminus-to-gauge window"))
        if any(b in a.basins for b in SCENES):
            handles.append(Line2D([], [], color=YELLOW, lw=1.8, ls="--", label="area of the proglacial image"))
    fig.tight_layout(rect=(0, 0.07, 1, 1), h_pad=3.0)
    legend_below(fig, axes, handles, min(len(handles), 3 if len(a.setups) == 1 else 4))
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    fig.savefig(a.output, dpi=250, bbox_inches="tight", pad_inches=0.05)
    print("wrote", a.output)


if __name__ == "__main__":
    main()
