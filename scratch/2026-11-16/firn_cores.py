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


def sample_layers(rows):
    """(top, bottom, density) of each sample, m and kg m-3, from consecutive sample bottom depths.

    The release's layer_top/layer_bottom columns are garbled in some cores (tops below bottoms), so only SBD is used.
    """
    out, top = [], 0.
    for r in rows:
        bot = float(r["SBD"])/100.
        out.append((top, bot, 1000.*float(r["layer_density"])))
        top = bot
    return out


def cores(glacier):
    site = sites(glacier)
    att = os.path.join(DATA, f"domain_{glacier}", "attributes")
    for path in sorted(glob.glob(os.path.join(DATA, f"domain_{glacier}", "observations", "firn", "*_firn_*.csv"))):
        name = os.path.basename(path).split("_")[1]
        s = site[name]
        x, y, epsg = s["Easting"], s["Northing"], s["UTM_EPSG"]
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        layers = sample_layers(rows)
        bottom = layers[-1][1]
        yield dict(
            file=os.path.basename(path), site=name,
            elev=raster_value(os.path.join(att, "elevation", "dem", f"domain_{glacier}_glacier_elv_utm.tif"), x, y, epsg),
            hru=int(raster_value(os.path.join(att, "glaciers", f"domain_{glacier}_hru_id.tif"), x, y, epsg)),
            layers=layers, bottom=bottom, swe=sum((b - t)*rho for t, b, rho in layers)/1000.,
            deep=np.mean([rho for t, b, rho in layers if t > bottom-2.])/1000.,
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


def density_over(layers, top, bottom):
    """Mean core density (kg m-3) between two depths (m), and the length of core that covers them (m)."""
    w = np.array([max(0., min(bottom, b) - max(top, t)) for t, b, r in layers])
    return (float(np.sum(w*np.array([r for t, b, r in layers]))/np.sum(w)), float(np.sum(w))) if np.sum(w) > 0. else (0., 0.)


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
                if dz.size == 0:
                    print("    model: no snow")
                    continue
                print(f"    model: {np.sum(dz):.1f} m of snow, {np.sum(dz*rho)/1000:.2f} m w.e., "
                      f"{swe_at(dz, rho, c['bottom']):.2f} m w.e. above {c['bottom']:.1f} m, densest {rho.max():.0f} kg m-3")
                # a spring core sits on the model's 1 October datum once the snow above last summer's surface is removed
                shift = c["annual"][0][0] if c["annual"] and int(c["file"].split("_")[-1][5:7]) < 7 else 0.
                ztop = np.concatenate([[0.], np.cumsum(dz)[:-1]])
                for t, b, r in zip(ztop, ztop+dz, rho):
                    core, cover = density_over(c["layers"], t+shift, b+shift)
                    if cover > 0.:
                        print(f"    {t:5.1f}-{b:5.1f} m: model {r:4.0f}, core {core:4.0f} kg m-3 over {cover:.1f} m "
                              f"(winter snow {shift:.1f} m removed)")


if __name__ == "__main__":
    main()
