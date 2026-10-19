#!/usr/bin/env python3
"""Compare a run's glacier area and debris through time with the USGS glacier areas and the imagery classes.

Reads a trial's yearly glacier grids (surface_elev and debris_thick, written by runs/rerun_trials.py) and its
spin-up's, which hold the starting state, with the bed and grid of the case's attributes.nc. A cell is glacier
where the ice is thicker than thick4area (0.1 m) and debris where it also carries at least 2 cm (min_thickness),
as SUMMA counts them. Writes, in <run>/glacier_change:

  area.csv     each year's glacier area (km2) of the main glacier, of all the run's glaciers and of the USGS
               area-altitude record (USGSweatherData/<Name>/Input_<Name>_Area_Altitude_Distribution.csv)
  bands.csv    the main glacier's area by the USGS 100 m bands, model and USGS, in the first and last year
  debris.csv   for each imagery date (check_glacier_imagery.py's class rasters, put on the model grid), the
               model's glacier and debris area at that year's end and the image's ice and debris or rock in
               the model glacier, the debris cells both agree on, and the image's debris or rock off it
  maps.npz     the main glacier's model debris and glacier masks and the image classes on its grid, by date

    ./compare_glacier_change.py domains/gulkana.yaml runs/gulkana_corrected/calibration_paper1_rerun/sample_384
"""

import argparse
import glob
import os

import netCDF4 as nc4
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject

from domain_config import load_config
from glacier_cold_state import grid_transforms

THICK4AREA, MIN_DEBRIS = 0.1, 0.02   # m, globalData.f90 thick4area and glacAreaChange.f90 min_thickness


def yearly(paths):
    """surface_elev and debris_thick (year, y, x, grid) and the year each ends (1 January stamps the year before)."""
    S, D, years = [], [], []
    for p in paths:
        with nc4.Dataset(p) as d:
            t = nc4.num2date(d["time"][:], d["time"].units)
            S.append(np.asarray(d["surface_elev"][:, :, :, :, 0], float))
            D.append(np.asarray(d["debris_thick"][:, :, :, :, 0], float))
            years += [x.year - 1 if (x.month, x.day) == (1, 1) else x.year for x in t]  # a year-end stamp, or the run's end
    order = np.argsort(years)
    return np.concatenate(S)[order], np.concatenate(D)[order], np.asarray(years)[order]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("run", help="a rerun trial folder, <case>/<name>_rerun/sample_<n>")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    run = os.path.abspath(a.run)
    out_dir = os.path.join(run, "glacier_change")
    os.makedirs(out_dir, exist_ok=True)

    case_dir = os.path.dirname(os.path.dirname(run))
    with nc4.Dataset(os.path.join(case_dir, "summa_inputs", "attributes.nc")) as d:
        bed = np.asarray(d["bed_elev"][:, :, :, 0], float)
        ids = np.asarray(d["gridId"][:, 0]).astype(int)
        nx, ny = np.asarray(d["nx"][:, 0]).astype(int), np.asarray(d["ny"][:, 0]).astype(int)
        dx = float(np.asarray(d["dx"][:]).flat[0])
    files = sorted(glob.glob(os.path.join(run, "output", "*spinup_rank0001_annual.nc"))) + \
        sorted(glob.glob(os.path.join(run, "output", "*sample*_annual.nc")))
    S, D, years = yearly(files)
    cell = dx * dx / 1e6
    main_g = int(np.argmax(nx * ny))
    ice = (S - bed[None]) > THICK4AREA
    for g in range(len(ids)):
        ice[:, ny[g]:, :, g] = False
        ice[:, :, nx[g]:, g] = False
    debris = ice & (D >= MIN_DEBRIS)

    usgs = pd.read_csv(os.path.join(project, "USGSweatherData", name, f"Input_{name}_Area_Altitude_Distribution.csv"),
                       index_col="Year")
    area = pd.DataFrame({"model_main_km2": ice[:, :, :, main_g].sum((1, 2)) * cell,
                         "model_all_km2": ice.sum((1, 2, 3)) * cell,
                         "model_main_debris_km2": debris[:, :, :, main_g].sum((1, 2)) * cell}, index=years)
    area["usgs_km2"] = usgs.sum(axis=1).reindex(years).values
    area.index.name = "year"
    area.round(4).to_csv(os.path.join(out_dir, "area.csv"))

    bands = []
    centres = np.array([float(b) for b in usgs.columns])
    for k in (0, len(years) - 1):
        s = S[k, :, :, main_g][ice[k, :, :, main_g]]
        counts = [((s >= b - 50) & (s < b + 50)).sum() * cell for b in centres]
        bands.append(pd.Series(counts, index=centres, name=f"model_{years[k]}"))
        if years[k] in usgs.index:
            bands.append(pd.Series(usgs.loc[years[k]].values, index=centres, name=f"usgs_{years[k]}"))
    pd.concat(bands, axis=1).rename_axis("band_centre_m").round(4).to_csv(os.path.join(out_dir, "bands.csv"))

    transforms, crs = grid_transforms(project, name, c["utm_epsg"])
    rows, maps = [], {"model_years": years, "dx": dx}
    for tif in sorted(glob.glob(os.path.join(project, "observations", "imagery", "imagery_*.tif"))):
        date = os.path.basename(tif)[:-4].split("_")[-1]
        k = int(np.where(years == min(max(int(date[:4]), years.min()), years.max()))[0][0])
        cls = np.zeros((ny[main_g], nx[main_g]), dtype=np.uint8)
        with rasterio.open(tif) as src:
            reproject(rasterio.band(src, 1), cls, dst_transform=transforms[int(ids[main_g])], dst_crs=crs,
                      resampling=Resampling.nearest)
        g_ice, g_deb = ice[k, :ny[main_g], :nx[main_g], main_g], debris[k, :ny[main_g], :nx[main_g], main_g]
        rows.append({"image_date": date, "model_year": int(years[k]),
                     "model_glacier_km2": g_ice.sum() * cell, "model_debris_km2": g_deb.sum() * cell,
                     "image_ice_in_model_glacier_km2": (g_ice & np.isin(cls, (1, 3))).sum() * cell,
                     "image_debris_in_model_glacier_km2": (g_ice & (cls == 2)).sum() * cell,
                     "debris_both_km2": (g_deb & (cls == 2)).sum() * cell,
                     "model_debris_image_ice_km2": (g_deb & np.isin(cls, (1, 3))).sum() * cell})
        maps[f"classes_{date}"] = cls
        maps[f"model_ice_{date}"] = g_ice
        maps[f"model_debris_{date}"] = g_deb
    pd.DataFrame(rows).round(4).to_csv(os.path.join(out_dir, "debris.csv"), index=False)
    np.savez_compressed(os.path.join(out_dir, "maps.npz"), **maps)
    print(area.round(3).to_string())
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
