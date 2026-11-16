#!/usr/bin/env python3
"""Compare USGS firn cores with the snow column of a SUMMA state file.

For each core: site, elevation and HRU from the domain rasters, depth, cumulative SWE, the mean density of its
deepest 2 m and its dated end-of-summer surfaces. With --state, also prints the glacier-domain snow column of the
core's HRU, and the simulated cumulative SWE at the core's bottom depth.

  python3 firn_cores.py                                   # cores only
  python3 firn_cores.py --state ../../runs/wolverine_added/summa_inputs/coldState.nc --glacier Wolverine
"""
import argparse
import csv
import glob
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
GLACIERS = ("Wolverine", "Gulkana")  # Wolverine first
GLACIER_DOM = 2  # domType of clean glacier ice


def raster_value(path, x, y, epsg):
    out = subprocess.run(["gdallocationinfo", "-valonly", "-l_srs", f"EPSG:{epsg}", path, str(x), str(y)],
                         capture_output=True, text=True, check=True).stdout.split()
    return float(out[0])


def sites(glacier):
    with open(os.path.join(DATA, f"domain_{glacier}", "observations", "firn", "Glacier_Firn_Sites.csv")) as f:
        return {r["site_name"]: r for r in csv.DictReader(f) if r["Glacier"] == glacier}


def cores(glacier):
    site = sites(glacier)
    att = os.path.join(DATA, f"domain_{glacier}", "attributes")
    for path in sorted(glob.glob(os.path.join(DATA, f"domain_{glacier}", "observations", "firn", "*_firn_*.csv"))):
        name = os.path.basename(path).split("_")[1]
        s = site[name]
        x, y, epsg = s["Easting"], s["Northing"], s["UTM_EPSG"]
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        bottom = float(rows[-1]["layer_bottom"])/100.
        yield dict(
            file=os.path.basename(path), site=name,
            elev=raster_value(os.path.join(att, "elevation", "dem", f"domain_{glacier}_glacier_elv_utm.tif"), x, y, epsg),
            hru=int(raster_value(os.path.join(att, "glaciers", f"domain_{glacier}_hru_id.tif"), x, y, epsg)),
            bottom=bottom, swe=float(rows[-1]["cumulative_SWE"]),
            deep=np.mean([float(r["layer_density"]) for r in rows if float(r["layer_top"])/100. > bottom-2.]),
            lens=sum(float(r["ice_lens_thick_sum"] or 0) for r in rows),
            annual=[(float(r["annual_layer_depth"])/100., r["annual_layer_year"]) for r in rows if r["annual_layer_year"]])


def snow_column(state, hru_index):
    import netCDF4 as nc
    with nc.Dataset(state) as d:
        for k in range(d.dimensions["dom"].size):
            if np.ma.is_masked(d["domType"][hru_index, k]) or int(d["domType"][hru_index, k]) != GLACIER_DOM:
                continue
            ns = int(d["nSnow"][hru_index, k])
            dz = np.asarray(d["mLayerDepth"][:ns, hru_index, k])
            rho = 917.*np.asarray(d["mLayerVolFracIce"][:ns, hru_index, k]) + 1000.*np.asarray(d["mLayerVolFracLiq"][:ns, hru_index, k])
            return dz, rho
    return None


def swe_at(dz, rho, depth):
    top = np.concatenate([[0.], np.cumsum(dz)[:-1]])
    return float(np.sum(np.clip(depth - top, 0., dz)*rho)/1000.)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", help="SUMMA state file (coldState.nc)")
    p.add_argument("--glacier", choices=GLACIERS, help="glacier of the state file")
    a = p.parse_args()
    for glacier in GLACIERS:
        if a.glacier and glacier != a.glacier:
            continue
        print(glacier)
        for c in cores(glacier):
            dated = ", ".join(f"{y} at {z:.1f} m" for z, y in c["annual"]) or "none"
            print(f"  {c['file']}: site {c['site']} {c['elev']:.0f} m HRU {c['hru']}, {c['bottom']:.1f} m deep, "
                  f"{c['swe']:.2f} m w.e., deepest 2 m {1000*c['deep']:.0f} kg m-3, ice lenses {c['lens']:.0f} cm, "
                  f"dated surfaces: {dated}")
            if a.state:
                col = snow_column(a.state, c["hru"]-1)
                if col is None:
                    print("    no glacier domain in that HRU")
                    continue
                dz, rho = col
                print(f"    model: {np.sum(dz):.1f} m of snow, {np.sum(dz*rho)/1000:.2f} m w.e., "
                      f"{swe_at(dz, rho, c['bottom']):.2f} m w.e. above {c['bottom']:.1f} m, densest {rho.max():.0f} kg m-3")


if __name__ == "__main__":
    main()
