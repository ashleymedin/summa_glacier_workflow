#!/usr/bin/env python3
"""Plot each setup's glacier and debris at the end of a trial's run against those observed, laid out as plot_basin_setup.py.

One panel per basin (rows) and setup (columns), on the setup's UTM surface grid, zoomed to its glaciers. Drawn:

  model glacier and debris   the trial's last annual state: ice thicker than thick4area (0.1 m), debris of 2 cm or more
                             (compare_glacier_change.py's rule), on each glacier's own grid
  start outline              the trial's cold-state glaciers, thin
  observed outline           the main glacier's last USGS survey outline (the YAML's later_outline)
  observed debris            the start-debris rule of glacier_rasters.py on the last two late-summer scenes
                             (check_glacier_imagery.py classes of the added-data domain): inside the observed outline, cells
                             mostly not ice in the scenes, less its edge unless the setup started them as debris

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
from scipy.ndimage import binary_erosion

from compare_glacier_change import MIN_DEBRIS, THICK4AREA, yearly
from domain_config import load_config
from glacier_cold_state import grid_transforms
from glacier_rasters import image_ice_fraction
from plot_basin_setup import BROWN, PURPLE, chaikin, on_grid, soft

HERE = os.path.dirname(os.path.abspath(__file__))
ICE, ICE_EDGE, OBS = "#9ecae1", "#2171b5", "black"


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


def observed(c, o, like, start_debris):
    """The observed outline (GeoSeries, in the grid's crs), its date, the scene dates, and the observed debris on the grid."""
    later, usgs = o["later_outline"], o["usgs_outline"]
    surveys = gpd.read_file(os.path.join(HERE, o["data"]["usgs_outlines"]))
    outline = surveys[(surveys.Glacier == usgs["glacier"]) & (surveys.Date == later["date"])].to_crs(like.crs).geometry
    inside = geometry_mask(list(outline), transform=like.transform, invert=True, out_shape=like.shape)
    scenes = sorted(glob.glob(os.path.join(o["project_dir"], "observations", "imagery", "imagery_*.tif")))[-2:]
    frac = image_ice_fraction(scenes, like, like.shape)
    bare = inside & (frac < 0.5)
    debris = bare & (binary_erosion(inside) | start_debris)
    dates = [os.path.basename(s)[:-4].split("_")[-1] for s in scenes]
    return outline, later["date"], dates, debris


def panel(ax, config, obs_config, run, label, a, letter):
    c, o = load_config(config), load_config(obs_config)
    project, name = c["project_dir"], c["domain"]
    glaciers = os.path.join(project, "attributes", "glaciers")
    with rasterio.open(os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv_utm.tif")) as like:
        dem = like.read(1, masked=True).filled(np.nan).astype(float)
        tr, shape = like.transform, like.shape
        start_debris = on_grid(os.path.join(glaciers, f"domain_{name}_domain_type.tif"), like) == 4
        outline, outline_date, scene_dates, obs_debris = observed(c, o, like, start_debris)
    year, grids = model_end(c, run)
    xs = tr.c + tr.a * (np.arange(shape[1]) + 0.5)
    ys = tr.f + tr.e * (np.arange(shape[0]) + 0.5)
    extent = (tr.c, tr.c + tr.a * shape[1], tr.f + tr.e * shape[0], tr.f)
    filled = np.where(np.isfinite(dem), dem, np.nanmin(dem))
    ax.imshow(LightSource(315, 40).hillshade(filled, vert_exag=2, dx=abs(tr.a), dy=abs(tr.e)), cmap="gray", vmin=0.2, vmax=1.0,
              extent=extent, zorder=0)
    levels = np.arange(np.floor(np.nanmin(dem) / a.contour) * a.contour, np.nanmax(dem) + a.contour, a.contour)
    ax.contour(xs, ys, dem, levels=levels, colors="#3a3a3a", linewidths=0.35, zorder=1)

    for t, ice, deb, ice0 in grids:  # the model, each glacier on its own grid
        gx = t.c + t.a * (np.arange(ice.shape[1]) + 0.5)
        gy = t.f + t.e * (np.arange(ice.shape[0]) + 0.5)
        ax.contourf(gx, gy, soft(ice), levels=[0.5, 1.5], colors=[ICE], alpha=0.75, zorder=2)
        ax.contour(gx, gy, soft(ice), levels=[0.5], colors=[ICE_EDGE], linewidths=0.8, zorder=3)
        if deb.any():
            ax.contourf(gx, gy, soft(deb), levels=[0.5, 1.5], colors=[BROWN], alpha=0.85, zorder=4)
        ax.contour(gx, gy, soft(ice0), levels=[0.5], colors=[PURPLE], linewidths=0.8, linestyles=":", zorder=5)
    gpd.GeoSeries(outline.map(chaikin)).boundary.plot(ax=ax, color=OBS, linewidth=1.4, linestyle="--", zorder=6)
    if obs_debris.any():
        ax.contour(xs, ys, soft(obs_debris), levels=[0.5], colors=["#4a2508"], linewidths=1.3, zorder=7)

    rows, cols = np.nonzero(start_debris | obs_debris)
    pad = 400.0
    left, right = tr.c + tr.a * cols.min() - pad, tr.c + tr.a * (cols.max() + 1) + pad
    top, bottom = tr.f + tr.e * rows.min() + pad, tr.f + tr.e * (rows.max() + 1) - pad
    x0, y0, x1, y1 = outline.total_bounds
    for t, _, _, ice0 in grids:
        r, k = np.nonzero(ice0)
        left, right = min(left, t.c + t.a * k.min() - pad), max(right, t.c + t.a * (k.max() + 1) + pad)
        bottom, top = min(bottom, t.f + t.e * (r.max() + 1) - pad), max(top, t.f + t.e * r.min() + pad)
    left, right, bottom, top = min(left, x0 - pad), max(right, x1 + pad), min(bottom, y0 - pad), max(top, y1 + pad)
    r, k = np.nonzero(np.isfinite(dem))  # inside the surface's valid cells, off its ragged edge
    left, right = max(left, tr.c + tr.a * (k.min() + 2)), min(right, tr.c + tr.a * (k.max() - 1))
    bottom, top = max(bottom, tr.f + tr.e * (r.max() - 1)), min(top, tr.f + tr.e * (r.min() + 2))
    ax.set_xlim(left, right)
    ax.set_ylim(bottom, top)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.text(0.02, 0.98, f"({letter})", transform=ax.transAxes, ha="left", va="top", fontsize=11, fontweight="bold", zorder=20,
            bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
    length = 1000
    bx0, by0 = left + 0.05 * (right - left), bottom + 0.05 * (top - bottom)
    ax.add_patch(Rectangle((bx0 - 0.015 * (right - left), by0 - 0.012 * (top - bottom)), length + 0.03 * (right - left),
                           0.06 * (top - bottom), fc="white", alpha=0.75, ec="none", zorder=11))
    ax.plot([bx0, bx0 + length], [by0, by0], color="black", lw=3, zorder=12, solid_capstyle="butt")
    ax.text(bx0 + length / 2, by0 + 0.014 * (top - bottom), "1 km", ha="center", fontsize=7, zorder=12)
    nx0, ny0 = right - 0.07 * (right - left), top - 0.16 * (top - bottom)
    ax.annotate("N", (nx0, ny0 + 0.09 * (top - bottom)), (nx0, ny0), ha="center", va="bottom", fontsize=8,
                arrowprops=dict(arrowstyle="-|>", color="black"), zorder=11)
    cell = abs(tr.a * tr.e) / 1e6
    print(f"{name} {label}: model end of {year}; observed outline {outline_date}, scenes {', '.join(scene_dates)}; "
          f"observed debris {obs_debris.sum() * cell:.2f} km2")
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
    fig, axes = plt.subplots(len(basins), len(setups), figsize=(4.8 * len(setups), 4.6 * len(basins)), squeeze=False)
    for basin, setup, run, label in specs:
        i, j = basins.index(basin), setups.index(setup)
        config = os.path.join(HERE, "domains", f"{basin}{'_general' if setup == 'general' else ''}.yaml")
        year, *_ = panel(axes[i, j], config, os.path.join(HERE, "domains", f"{basin}.yaml"), os.path.join(HERE, run), label, a,
                         "abcdefgh"[i * len(setups) + j])
        axes[i, j].set_title(f"{basin.capitalize()}, {'general' if setup == 'general' else 'added-data'} setup ({label})", fontsize=10)
    handles = [Patch(fc=ICE, ec=ICE_EDGE, label=f"model glacier, end of {year}"), Patch(fc=BROWN, alpha=0.85, label="model debris, 2 cm or more"),
               Line2D([], [], color=PURPLE, lw=0.9, ls=":", label="glacier outline at the start"),
               Line2D([], [], color=OBS, lw=1.4, ls="--", label="observed outline, last USGS survey"),
               Line2D([], [], color="#4a2508", lw=1.3, label="observed debris, late-summer imagery")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.5, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1), h_pad=2.0)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    fig.savefig(a.output, dpi=250, bbox_inches="tight", pad_inches=0.05)
    print("wrote", a.output)


if __name__ == "__main__":
    main()
