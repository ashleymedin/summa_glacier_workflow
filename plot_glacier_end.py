#!/usr/bin/env python3
"""Plot each setup's glacier and debris at the end of a trial's run against those observed, laid out as plot_basin_setup.py.

One panel per basin (rows) and setup (columns), on the setup's UTM surface grid, framed as plot_basin_setup.py frames its basin. Drawn:

  model glacier and debris   the trial's last annual state: ice thicker than thick4area (0.1 m), debris of 2 cm or more
                             (compare_glacier_change.py's rule), on each glacier's own grid
  start outline              the trial's cold-state glaciers, thin
  observed outline           the last USGS survey outline (the YAML's later_outline) brought to the last two late-summer scenes (check_glacier_imagery.py classes of
                             the added-data domain): less the cells mostly not ice in the scenes that join the ground outside
                             through such cells, but for those the added-data setup started as debris, whose ice the scenes cannot see
  observed debris            the start-debris rule of glacier_rasters.py on the same scenes: inside the observed outline, cells
                             mostly not ice, less its edge unless the added-data setup started them as debris

    ./plot_glacier_end.py figs/glacier_end.pdf \\
        wolverine:general:runs/wolverine_general/calibration_rerun_nov11/sample_396:396 \\
        wolverine:added:runs/wolverine_added/calibration_rerun/sample_459:459 \\
        gulkana:general:runs/gulkana_general/calibration_rerun_nov11/sample_370:370 \\
        gulkana:added:runs/gulkana_added/calibration_rerun/sample_451:451
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
import rasterio
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from rasterio.features import geometry_mask
from scipy.ndimage import binary_erosion, label

from compare_glacier_change import MIN_DEBRIS, THICK4AREA, yearly
from domain_config import load_config
from glacier_cold_state import grid_transforms
from glacier_rasters import image_ice_fraction
from plot_basin_setup import BROWN, HRU_LW, DEBRIS_EDGE, OUTLINE_LW, CONTOUR, CONTOUR_INDEX, DIM_ALPHA, HILL_VMIN, ICE_ALPHA, VERT_EXAG, ICE_FILL, PURPLE, chaikin, legend_below, on_grid, soft

HERE = os.path.dirname(os.path.abspath(__file__))
ICE, ICE_EDGE, OBS = ICE_FILL, "#9e7bb5", "black"  # model ice in plot_basin_setup.py's glacier shade


def model_end(c, run):
    """The run's last year and, per glacier grid, (transform, ice, debris, start ice) masks of that year's end and the cold state."""
    inputs = run + "_settings"
    if not os.path.exists(os.path.join(inputs, "attributes.nc")):
        inputs = os.path.join(os.path.dirname(os.path.dirname(run)), "summa_inputs")
    with nc4.Dataset(os.path.join(inputs, "attributes.nc")) as d:
        bed = np.asarray(d["bed_elev"][:, :, :, 0], float)
        ids = np.asarray(d["gridId"][:, 0]).astype(int)
        nx, ny = np.asarray(d["nx"][:, 0]).astype(int), np.asarray(d["ny"][:, 0]).astype(int)
    with nc4.Dataset(os.path.join(inputs, "coldState.nc")) as d:
        S0 = np.asarray(d["surface_elev"][:, :, :, 0], float)
    S, D, years = yearly(sorted(glob.glob(os.path.join(run, "output", "*sample*_annual.nc"))))
    tf, _ = grid_transforms(c["project_dir"], c["domain"], c["utm_epsg"])
    grids = []
    for g in range(len(ids)):
        ice = (S[-1, :ny[g], :nx[g], g] - bed[:ny[g], :nx[g], g]) > THICK4AREA
        ice0 = (S0[:ny[g], :nx[g], g] - bed[:ny[g], :nx[g], g]) > THICK4AREA
        grids.append((tf[int(ids[g])], ice, ice & (D[-1, :ny[g], :nx[g], g] >= MIN_DEBRIS), ice0))
    return int(years[-1]), grids


def observed(c, o, like, start_debris, in_basin):
    """The last survey outline (GeoSeries, in the grid's crs), its date, the scene dates, and the observed glacier and debris on the grid.
    The glaciers in the basin without a survey (Gulkana's small ones) start from their outlines in the added-data domain's
    glacier raster (RGI, before the survey's glacier is taken out) and go through the same imagery rule."""
    later, usgs = o["later_outline"], o["usgs_outline"]
    surveys = gpd.read_file(os.path.join(HERE, o["data"]["usgs_outlines"]))
    outline = surveys[(surveys.Glacier == usgs["glacier"]) & (surveys.Date == later["date"])].to_crs(like.crs).geometry
    inside = geometry_mask(list(outline), transform=like.transform, invert=True, out_shape=like.shape)
    rgi = on_grid(os.path.join(o["project_dir"], "attributes", "glaciers", f"domain_{o['domain']}_rgi_id.tif"), like).astype(int)
    surveyed = np.bincount(rgi[inside & (rgi > 0)]).argmax() if (inside & (rgi > 0)).any() else 0  # the survey's glacier in the raster
    inside |= (rgi > 0) & (rgi != surveyed) & in_basin
    scenes = sorted(glob.glob(os.path.join(o["project_dir"], "observations", "imagery", "imagery_*.tif")))[-2:]
    frac = image_ice_fraction(scenes, like, like.shape)
    bare = inside & (frac < 0.5)
    parts, _ = label(~inside | (bare & ~start_debris))
    ground = np.isin(parts, np.unique(parts[~inside])) & inside  # ice-free cells joined to the ground outside the outline
    glacier = inside & ~ground
    debris = glacier & bare & (binary_erosion(glacier) | start_debris)
    dates = [os.path.basename(s)[:-4].split("_")[-1] for s in scenes]
    return outline, later["date"], dates, glacier, debris


def panel(ax, config, obs_config, run, label, a, letter):
    c, o = load_config(config), load_config(obs_config)
    project, name = c["project_dir"], c["domain"]
    glaciers = os.path.join(project, "attributes", "glaciers")
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv_utm.tif")) as like:
        dem = like.read(1, masked=True).filled(np.nan).astype(float)
        tr, shape = like.transform, like.shape
        start_debris = on_grid(os.path.join(o["project_dir"], "attributes", "glaciers", f"domain_{o['domain']}_domain_type.tif"), like) == 4  # the added-data start, so both setups face the same observation
        added_basin = gpd.read_file(glob.glob(os.path.join(o["project_dir"], "shapefiles", "river_basins", "*.shp"))[0]).to_crs(like.crs)
        in_basin = geometry_mask(list(added_basin.geometry), transform=like.transform, invert=True, out_shape=like.shape)
        outline, outline_date, scene_dates, obs_glacier, obs_debris = observed(c, o, like, start_debris, in_basin)
    year, grids = model_end(c, run)
    xs = tr.c + tr.a * (np.arange(shape[1]) + 0.5)
    ys = tr.f + tr.e * (np.arange(shape[0]) + 0.5)
    extent = (tr.c, tr.c + tr.a * shape[1], tr.f + tr.e * shape[0], tr.f)
    filled = np.where(np.isfinite(dem), dem, np.nanmin(dem))
    ax.imshow(LightSource(315, 40).hillshade(filled, vert_exag=VERT_EXAG, dx=abs(tr.a), dy=abs(tr.e)), cmap="gray", vmin=HILL_VMIN, vmax=1.0,
              extent=extent, zorder=0)
    levels = np.arange(np.floor(np.nanmin(dem) / a.contour) * a.contour, np.nanmax(dem) + a.contour, a.contour)
    index = levels % (5 * a.contour) == 0  # contours over the ice, as plot_basin_setup.py draws them
    ax.contour(xs, ys, dem, levels=levels[~index], colors=CONTOUR, linewidths=0.4, zorder=2.5)
    ax.contour(xs, ys, dem, levels=levels[index], colors=CONTOUR_INDEX, linewidths=0.8, zorder=2.5)
    basin = gpd.read_file(glob.glob(os.path.join(project, "shapefiles", "river_basins", "*.shp"))[0]).to_crs(like.crs)
    ax.imshow(np.ones(shape), cmap="gray_r", vmin=0, vmax=1.3, alpha=DIM_ALPHA, extent=extent, zorder=0.2)  # the hillshade dimmed, as plot_basin_setup.py
    basin.set_geometry(basin.geometry.map(chaikin)).boundary.plot(ax=ax, color="black", linewidth=1.8, zorder=8)

    for t, ice, deb, ice0 in grids:  # the model, each glacier on its own grid
        gx = t.c + t.a * (np.arange(ice.shape[1]) + 0.5)
        gy = t.f + t.e * (np.arange(ice.shape[0]) + 0.5)
        ax.contourf(gx, gy, soft(ice), levels=[0.5, 1.5], colors=[ICE], alpha=ICE_ALPHA, zorder=2)
        ax.contour(gx, gy, soft(ice), levels=[0.5], colors=[PURPLE], linewidths=OUTLINE_LW, zorder=3)
        if deb.any():
            ax.contourf(gx, gy, soft(deb), levels=[0.5, 1.5], colors=[BROWN], alpha=0.5, zorder=4)  # as plot_basin_setup.py
            ax.contour(gx, gy, soft(deb), levels=[0.5], colors=[DEBRIS_EDGE], linewidths=OUTLINE_LW, zorder=4.5)
    ax.contour(xs, ys, soft(obs_glacier), levels=[0.5], colors=[PURPLE], linewidths=HRU_LW, linestyles="--", zorder=6)
    if obs_debris.any():
        ax.contour(xs, ys, soft(obs_debris), levels=[0.5], colors=[DEBRIS_EDGE], linewidths=HRU_LW, linestyles="--", zorder=7)

    x0, y0, x1, y1 = basin.total_bounds  # the basin and margin of plot_basin_setup.py, so the panels of the two figures match
    pad = 0.06 * max(x1 - x0, y1 - y0)
    r, k = np.nonzero(np.isfinite(dem))  # the surface's valid cells; beyond them the raster is empty
    valid = (tr.c + tr.a * (k.min() + 1), tr.f + tr.e * (r.max() - 1), tr.c + tr.a * (k.max() - 1), tr.f + tr.e * (r.min() + 1))
    left, bottom, right, top = max(x0 - pad, valid[0]), max(y0 - pad, valid[1]), min(x1 + pad, valid[2]), min(y1 + pad, valid[3])
    ax.set_xlim(left, right)
    ax.set_ylim(bottom, top)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.text(0.02, 0.98, f"({letter})", transform=ax.transAxes, ha="left", va="top", fontsize=11, fontweight="bold", zorder=20,
            bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
    length = 1000 if (right - left) < 9000 else 2000
    bx0, by0 = left + 0.05 * (right - left), bottom + 0.05 * (top - bottom)
    ax.add_patch(Rectangle((bx0 - 0.015 * (right - left), by0 - 0.012 * (top - bottom)), length + 0.03 * (right - left),
                           0.06 * (top - bottom), fc="white", alpha=0.75, ec="none", zorder=11))
    ax.plot([bx0, bx0 + length], [by0, by0], color="black", lw=3, zorder=12, solid_capstyle="butt")
    ax.text(bx0 + length / 2, by0 + 0.014 * (top - bottom), "1 km", ha="center", fontsize=7, zorder=12)
    nx0, ny0 = right - 0.07 * (right - left), top - 0.13 * (top - bottom)
    ax.annotate("N", (nx0, ny0 + 0.09 * (top - bottom)), (nx0, ny0), ha="center", va="bottom", fontsize=8,
                arrowprops=dict(arrowstyle="-|>", color="black"), zorder=11)
    cell = abs(tr.a * tr.e) / 1e6
    print(f"{name} {label}: model end of {year}; survey {outline_date} {outline.area.sum() / 1e6:.2f} km2, "
          f"observed glacier {obs_glacier.sum() * cell:.2f} km2 and debris {obs_debris.sum() * cell:.2f} km2 from {', '.join(scene_dates)}")
    return year, outline_date, scene_dates


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("output", help="figure to write (.pdf or .png)")
    p.add_argument("runs", nargs="+", help="basin:setup:run:label, row by row (setup general or added)")
    p.add_argument("--contour", type=float, default=100.0, help="contour interval, m")
    a = p.parse_args()
    specs = [r.split(":") for r in a.runs]
    basins = list(dict.fromkeys(s[0] for s in specs))
    setups = list(dict.fromkeys(s[1] for s in specs))
    fig, axes = plt.subplots(len(basins), len(setups), figsize=(max(4.6 * len(setups), 6.6), 5.6 * len(basins)), squeeze=False)
    for basin, setup, run, label in specs:
        i, j = basins.index(basin), setups.index(setup)
        config = os.path.join(HERE, "domains", f"{basin}{'_general' if setup == 'general' else ''}.yaml")
        year, *_ = panel(axes[i, j], config, os.path.join(HERE, "domains", f"{basin}.yaml"), os.path.join(HERE, run), label, a,
                         "abcdefgh"[i * len(setups) + j])
        axes[i, j].set_title(f"{basin.capitalize()}, {'general' if setup == 'general' else 'added-data'} setup", fontsize=10)
    handles = [Patch(fc=ICE, ec=PURPLE, lw=OUTLINE_LW, label=f"model glacier, end of {year}"), Patch(fc=BROWN, ec=DEBRIS_EDGE, lw=OUTLINE_LW, alpha=0.6, label="model debris, 2 cm or more"),
               Line2D([], [], color=PURPLE, lw=HRU_LW, ls="--", label="observed outline, late-summer imagery"),
               Line2D([], [], color=DEBRIS_EDGE, lw=HRU_LW, ls="--", label="observed debris, late-summer imagery"),
               Line2D([], [], color="black", lw=1.8, label="basin")]
    fig.tight_layout(rect=(0, 0.07, 1, 1), h_pad=3.0)
    legend_below(fig, axes, handles, 3)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    fig.savefig(a.output, dpi=250, bbox_inches="tight", pad_inches=0.05)
    print("wrote", a.output)


if __name__ == "__main__":
    main()
