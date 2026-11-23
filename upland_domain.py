#!/usr/bin/env python3
"""Build the non-glacier pieces of a new domain from global data, in place of the SYMFLUENCE domain.

Three parts, run by setup_glacier_domain.py around the glacier steps; surface and upland when the domain YAML has an
`upland:` block:

  surface   before the rasters step, over the YAML's bounding_box on a 3 arc-second grid (MERIT Hydro's spacing):
              attributes/elevation/dem/domain_<name>_elv.tif        upland:dem tiles (Copernicus GLO-30), cell means, m
              attributes/landclass/domain_<name>_land_classes.tif   IGBP class (MODIFIED_IGBP_MODIS_NOAH) from
                                                                    upland:landclass: ESA WorldCover 2021 (10 m, the mode in
                                                                    each cell, its classes mapped by WORLDCOVER_IGBP and
                                                                    landclass:igbp) or MODIS MCD12Q1.061 LC_Type1 (the mode
                                                                    of the years landclass:years, nearest cell)
              attributes/soilclass/domain_<name>_soil_classes.tif   ROSETTA class 1-12 of TBL_SOILPARM.TBL, the USDA texture
                                                                    of SoilGrids 2.0 sand and clay averaged over 0-100 cm;
                                                                    cells it leaves bare (ice, water) take the nearest class
              settings/SUMMA                                        upland:settings_from's tables, decisions and parameters
  upland    after the bands step, for the HRUs of shapefiles/catchment/<name>_HRUs_elevation.shp:
              settings/SUMMA/attributes.nc   ids, the HRU's majority land and soil class over its ice-free cells (the
                                             upland domain's), snow and ice only where it holds more than half of them;
                                             slopeTypeIndex of settings_from; mHeight MHEIGHT_ABOVE over the class's
                                             canopy top (HVT); area, centre, elevation and slope are hru_attributes.py's
              settings/SUMMA/coldState.nc    settings_from's first HRU column for every HRU
              settings/SUMMA/trialParams.nc  hruId and settings_from's first maxstep
  vegetation  for any domain with a landclass: block (top level, or under upland:): the land class raster again on the
              domain's DEM grid, and only vegTypeIndex and mHeight rewritten, as above, in settings/SUMMA/attributes.nc
              and attributes_glac.nc, so a SYMFLUENCE domain's vegetation is chosen as a new domain's

MODIS tiles come from NASA Earthdata (a urs.earthdata.nasa.gov login in ~/.netrc) into data/external/MODIS_MCD12Q1. They are
HDF4: if this Python's GDAL cannot read HDF4, the gdal_translate named by GDAL_TRANSLATE_HDF4 converts them (default the ngen
conda env's). WorldCover is read from the Microsoft Planetary Computer and SoilGrids from the ISRIC WCS, no key.

    ./upland_domain.py domains/lemon_creek.yaml surface
    ./upland_domain.py domains/lemon_creek.yaml upland
    ./upland_domain.py domains/wolverine.yaml vegetation
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

import geopandas as gpd
import netCDF4 as nc4
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterstats import zonal_stats
from scipy.ndimage import distance_transform_edt

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = 1.0 / 1200  # 3 arc-seconds, deg
NODATA = -9999.0
MODIS_DIR = os.path.join(HERE, "data", "external", "MODIS_MCD12Q1")
HDF4_TRANSLATE = os.environ.get("GDAL_TRANSLATE_HDF4", os.path.expanduser("~/miniconda3/envs/ngen/bin/gdal_translate"))
SOILGRIDS = "https://maps.isric.org/mapserv?map=/map/{var}.map"
SOIL_DEPTHS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15, "30-60cm": 30, "60-100cm": 40}  # layer, thickness (cm)
ROSETTA = {"clay": 1, "clay loam": 2, "loam": 3, "loamy sand": 4, "sand": 5, "sandy clay": 6, "sandy clay loam": 7,
           "sandy loam": 8, "silt": 9, "silty clay": 10, "silty clay loam": 11, "silt loam": 12}
SNOW_ICE = 15  # IGBP permanent snow and ice
MHEIGHT_ABOVE = 1.5  # forcing height above the canopy top, m
WORLDCOVER_IGBP = {10: 1, 20: 7, 30: 10, 40: 12, 50: 13, 60: 16, 70: SNOW_ICE, 80: 17, 90: 11, 95: 11, 100: 19}  # tree as
# evergreen needleleaf, shrub open shrubland, moss and lichen mixed tundra; landclass:igbp overrides any of these
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{collection}"
TEMPLATE_SKIP =("attributes*.nc", "coldState*.nc", "coldstate*.nc", "trialParams*.nc", "forcingFileList.txt", "fileManager*.txt")


def landclass_config(c):
    """The YAML's landclass: block, top-level or under upland:."""
    return c.get("landclass") or c.get("upland", {}).get("landclass", {})


def usda_texture(sand, clay):
    """USDA texture class of sand and clay percentages (silt the rest)."""
    silt = 100.0 - sand - clay
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 1.5 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def grid(c):
    """Transform and shape of the 3 arc-second grid over the bounding box, its edges on whole cells."""
    lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
    west, north = np.floor(lon_min / CELL) * CELL, np.ceil(lat_max / CELL) * CELL
    width, height = int(np.ceil((lon_max - west) / CELL)), int(np.ceil((north - lat_min) / CELL))
    return from_origin(west, north, CELL, CELL), (height, width)


def write(path, data, transform, dtype, nodata):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1, dtype=dtype,
                       crs="EPSG:4326", transform=transform, nodata=nodata, compress="deflate") as dst:
        dst.write(data.astype(dtype), 1)
    print(f"wrote {path}")


def fill_nearest(values, valid):
    _, (r, k) = distance_transform_edt(~valid, return_indices=True)
    return values[r, k]


def surface_dem(c, transform, shape, path):
    tiles = sorted(glob.glob(os.path.join(HERE, c["upland"]["dem"])))
    out = np.full(shape, np.nan)
    for t in tiles:
        with rasterio.open(t) as s:
            part = np.full(shape, np.nan)
            reproject(rasterio.band(s, 1), part, src_transform=s.transform, src_crs=s.crs, src_nodata=s.nodata,
                      dst_transform=transform, dst_crs="EPSG:4326", dst_nodata=np.nan, resampling=Resampling.average)
            out = np.where(np.isfinite(part), part, out)
    if np.isnan(out).any():
        raise SystemExit(f"{np.isnan(out).sum()} cells of the bounding box have no DEM in {c['upland']['dem']}")
    write(path, out, transform, "float32", NODATA)


def earthdata_get(url, dest):
    """Download a file behind the Earthdata login (~/.netrc), following its redirects with a cookie jar."""
    with tempfile.NamedTemporaryFile() as jar:
        subprocess.run(["curl", "-sS", "-f", "-n", "-L", "-c", jar.name, "-b", jar.name, "-o", dest, url], check=True)


def modis_tiles(c, years):
    """MCD12Q1.061 granules over the bounding box for those years, downloaded to MODIS_DIR, by year."""
    lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
    q = urllib.parse.urlencode({"short_name": "MCD12Q1", "version": "061", "page_size": 2000,
                                "bounding_box": f"{lon_min},{lat_min},{lon_max},{lat_max}"})
    with urllib.request.urlopen(f"https://cmr.earthdata.nasa.gov/search/granules.json?{q}") as r:
        entries = json.load(r)["feed"]["entry"]
    os.makedirs(MODIS_DIR, exist_ok=True)
    files = {}
    for e in entries:
        year = int(e["time_start"][:4])
        if year not in years:
            continue
        url = next(x["href"] for x in e["links"] if x["href"].startswith("https") and x["href"].endswith(".hdf"))
        hdf = os.path.join(MODIS_DIR, os.path.basename(url))
        tif = hdf.replace(".hdf", "_LC_Type1.tif")
        if not os.path.exists(tif):
            if not os.path.exists(hdf):
                print(f"fetching {os.path.basename(url)}", flush=True)
                earthdata_get(url, hdf)
            sub = f'HDF4_EOS:EOS_GRID:"{hdf}":MCD12Q1:LC_Type1'
            try:
                with rasterio.open(sub) as s, rasterio.open(tif, "w", **{**s.meta, "driver": "GTiff"}) as d:
                    d.write(s.read())
            except rasterio.errors.RasterioIOError:
                subprocess.run([HDF4_TRANSLATE, "-q", sub, tif], check=True)
            os.remove(hdf)
        files.setdefault(year, []).append(tif)
    missing = sorted(set(years) - set(files))
    if missing:
        raise SystemExit(f"no MCD12Q1.061 granule over the domain for {missing}")
    return files


def worldcover_classes(c, transform, shape, path):
    """ESA WorldCover 2021 over the grid, the mode of its 10 m classes in each cell, as IGBP classes."""
    lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
    query = json.dumps({"collections": ["esa-worldcover"], "bbox": [lon_min, lat_min, lon_max, lat_max], "limit": 50,
                        "query": {"esa_worldcover:product_version": {"eq": "2.0.0"}}}).encode()
    with urllib.request.urlopen(urllib.request.Request(PC_STAC, query, {"Content-Type": "application/json"})) as r:
        items = json.load(r)["features"]
    with urllib.request.urlopen(PC_TOKEN.format(collection="esa-worldcover")) as r:
        token = json.load(r)["token"]
    wc = np.zeros(shape, dtype=np.uint8)
    for item in items:
        with rasterio.open(item["assets"]["map"]["href"] + "?" + token) as s:
            part = np.zeros(shape, dtype=np.uint8)
            reproject(rasterio.band(s, 1), part, src_transform=s.transform, src_crs=s.crs, src_nodata=0,
                      dst_transform=transform, dst_crs="EPSG:4326", dst_nodata=0, resampling=Resampling.mode)
            wc = np.where(part > 0, part, wc)
    table = {**WORLDCOVER_IGBP, **{int(k): int(v) for k, v in landclass_config(c).get("igbp", {}).items()}}
    igbp = np.zeros(shape, dtype=np.int16)
    for k, v in table.items():
        igbp[wc == k] = v
    print(f"WorldCover 2021 ({', '.join(i['id'] for i in items)}) as IGBP: "
          + ", ".join(f"{k}: {int((igbp == k).sum())}" for k in np.unique(igbp)))
    write(path, igbp, transform, "int16", 0)


def land_classes(c, transform, shape, path):
    if landclass_config(c).get("source", "modis") == "worldcover":
        return worldcover_classes(c, transform, shape, path)
    first, last = landclass_config(c).get("years", [2001, 2020])
    stack = []
    for year, tifs in sorted(modis_tiles(c, range(first, last + 1)).items()):
        lc = np.zeros(shape, dtype=np.uint8)
        for t in tifs:
            with rasterio.open(t) as s:
                part = np.zeros(shape, dtype=np.uint8)
                reproject(rasterio.band(s, 1), part, src_transform=s.transform, src_crs=s.crs, src_nodata=255,
                          dst_transform=transform, dst_crs="EPSG:4326", dst_nodata=0, resampling=Resampling.nearest)
                lc = np.where(part > 0, part, lc)
        stack.append(lc)
    stack = np.array(stack)
    counts = np.stack([(stack == k).sum(axis=0) for k in range(1, 18)])  # IGBP 1-17
    mode = np.where(counts.sum(axis=0) > 0, counts.argmax(axis=0) + 1, 0)
    print(f"IGBP classes over the box, {first}-{last} mode: " + ", ".join(f"{k}: {int((mode == k).sum())}" for k in np.unique(mode)))
    write(path, mode, transform, "int16", 0)


def soilgrids(var, depth, bounds):
    """One SoilGrids 2.0 mean layer (g/kg) over the bounds (west, south, east, north), as an array and its transform."""
    west, south, east, north = bounds
    q = urllib.parse.urlencode([("SERVICE", "WCS"), ("VERSION", "2.0.1"), ("REQUEST", "GetCoverage"),
                                ("COVERAGEID", f"{var}_{depth}_mean"), ("FORMAT", "image/tiff"),
                                ("SUBSET", f"long({west},{east})"), ("SUBSET", f"lat({south},{north})"),
                                ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/4326"),
                                ("OUTPUTCRS", "http://www.opengis.net/def/crs/EPSG/0/4326")])
    with tempfile.NamedTemporaryFile(suffix=".tif") as f:
        with urllib.request.urlopen(SOILGRIDS.format(var=var) + "&" + q, timeout=300) as r:
            f.write(r.read())
        f.flush()
        with rasterio.open(f.name) as s:
            return s.read(1).astype(float), s.transform, s.nodata


def soil_classes(c, transform, shape, path):
    west, north = transform.c, transform.f
    bounds = (west - 0.01, north - shape[0] * CELL - 0.01, west + shape[1] * CELL + 0.01, north + 0.01)
    mean = {}
    for var in ("sand", "clay"):
        total = np.zeros(shape)
        for depth, dz in SOIL_DEPTHS.items():
            values, tr, nd = soilgrids(var, depth, bounds)
            values[values == nd] = np.nan
            values[values <= 0] = np.nan  # SoilGrids leaves ice and water at 0
            part = np.full(shape, np.nan)
            reproject(values, part, src_transform=tr, src_crs="EPSG:4326", dst_transform=transform, dst_crs="EPSG:4326",
                      src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.nearest)
            total += part * dz
        mean[var] = total / sum(SOIL_DEPTHS.values()) / 10.0  # g/kg to %
    valid = np.isfinite(mean["sand"]) & np.isfinite(mean["clay"])
    if not valid.any():
        raise SystemExit("SoilGrids has no soil over the bounding box")
    cls = np.zeros(shape, dtype=np.int16)
    for i, k in zip(*np.nonzero(valid)):
        cls[i, k] = ROSETTA[usda_texture(mean["sand"][i, k], mean["clay"][i, k])]
    print(f"soil on {valid.mean():.0%} of the box; ROSETTA classes " + ", ".join(f"{k}: {int((cls == k).sum())}" for k in np.unique(cls[valid])))
    write(path, fill_nearest(cls, valid), transform, "int16", 0)


def copy_settings(c, settings):
    src = os.path.join(HERE, c["upland"]["settings_from"])
    shutil.copytree(src, settings, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*TEMPLATE_SKIP, ".DS_Store"))
    print(f"copied the SUMMA settings of {src} to {settings}")


def majority(path, polygons, ice_free=None):
    """Each polygon's most common class over the cells of ice_free (all cells if None); snow and ice only where it
    holds more than half of them."""
    with rasterio.open(path) as s:
        data, affine, nodata = s.read(1), s.transform, s.nodata
    if ice_free is not None:
        data = np.where(ice_free, data, nodata)
    out = []
    for z in zonal_stats(polygons.to_crs(4326), data, affine=affine, nodata=nodata, categorical=True):
        z = {int(k): v for k, v in z.items() if k != nodata}
        rest = {k: v for k, v in z.items() if k != SNOW_ICE}
        out.append(SNOW_ICE if not rest or z.get(SNOW_ICE, 0) > sum(z.values()) / 2 else max(rest, key=rest.get))
    return out


def canopy_top(mptable, veg):
    """Canopy top height (m), HVT of the noah_mp_modis_parameters block of TBL_MPTABLE.TBL, for each IGBP class."""
    with open(mptable) as f:
        text = f.read().split("&noah_mp_modis_parameters", 1)[1]
    hvt = next(l for l in text.splitlines() if l.strip().startswith("HVT"))
    heights = [float(v) for v in hvt.split("=", 1)[1].replace(",", " ").split()]
    return np.array([heights[v - 1] for v in veg])


def write_like(src, path, n_hru, values, skip=(), n_gru=1):
    """A copy of the netCDF src with its hru dimension n_hru long and gru n_gru, each hru or gru variable its first column
    repeated unless in values."""
    with nc4.Dataset(src) as s, nc4.Dataset(path, "w") as d:
        d.setncatts({k: s.getncattr(k) for k in s.ncattrs()})
        for dim, v in s.dimensions.items():
            d.createDimension(dim, n_hru if dim == "hru" else n_gru if dim == "gru" else len(v))
        for name, v in s.variables.items():
            if name in skip:
                continue
            fill = v.getncattr("_FillValue") if "_FillValue" in v.ncattrs() else None
            out = d.createVariable(name, v.datatype, v.dimensions, fill_value=fill)
            out.setncatts({k: v.getncattr(k) for k in v.ncattrs() if k != "_FillValue"})
            data = np.asarray(v[:])
            if name in values:
                out[:] = values[name]
            elif "hru" in v.dimensions or "gru" in v.dimensions:
                for dim, size in (("hru", n_hru), ("gru", n_gru)):
                    if dim in v.dimensions:
                        ax = v.dimensions.index(dim)
                        data = np.repeat(np.take(data, [0], axis=ax), size, axis=ax)
                out[:] = data
            else:
                out[:] = data
    print(f"wrote {path}")


def upland(c, project, name):
    settings = os.path.join(project, "settings", "SUMMA")
    template = os.path.join(HERE, c["upland"]["settings_from"])
    hrus = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{name}_HRUs_elevation.shp")).sort_values("HRU_ID")
    n = len(hrus)
    ids = hrus["HRU_ID"].astype(int).values
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_domain_type.tif")) as s:
        ice_free = s.read(1) <= 1  # on the DEM grid, as the class rasters
    veg = majority(os.path.join(project, "attributes", "landclass", f"domain_{name}_land_classes.tif"), hrus, ice_free)
    soil = majority(os.path.join(project, "attributes", "soilclass", f"domain_{name}_soil_classes.tif"), hrus)
    m_height = canopy_top(os.path.join(settings, "TBL_MPTABLE.TBL"), veg) + MHEIGHT_ABOVE
    print(f"HRU vegTypeIndex {veg}, soilTypeIndex {soil}, mHeight {list(m_height)} m")
    gru = hrus["GRU_ID"].astype(int).values
    gru_ids = np.unique(gru)
    write_like(os.path.join(template, "attributes.nc"), os.path.join(settings, "attributes.nc"), n,
               {"hruId": ids, "gruId": gru_ids, "hru2gruId": gru, "downHRUindex": np.zeros(n, int),
                "vegTypeIndex": veg, "soilTypeIndex": soil, "mHeight": m_height, "HRUarea": hrus["HRU_area"].values,
                "latitude": hrus["center_lat"].values, "longitude": hrus["center_lon"].values,
                "elevation": hrus["elev_mean"].values}, n_gru=len(gru_ids))
    write_like(os.path.join(template, "coldState.nc"), os.path.join(settings, "coldState.nc"), n, {"hruId": ids}, n_gru=len(gru_ids))
    with nc4.Dataset(os.path.join(template, "trialParams.nc")) as s:
        keep = [v for v in s.variables if v not in ("hruId", "gruId", "maxstep")]
    write_like(os.path.join(template, "trialParams.nc"), os.path.join(settings, "trialParams.nc"), n,
               {"hruId": ids, "gruId": gru_ids}, skip=keep, n_gru=len(gru_ids))


def vegetation(c, project, name):
    """The land class raster again from landclass:, on the domain's DEM grid, and each HRU's vegTypeIndex and mHeight
    rewritten in place in settings/SUMMA/attributes.nc and attributes_glac.nc; nothing else in them changes."""
    dem_dir = os.path.join(project, "attributes", "elevation", "dem")
    with rasterio.open(os.path.join(dem_dir, f"domain_{name}_elv.tif")) as s:
        transform, shape = s.transform, s.shape
    path = os.path.join(project, "attributes", "landclass", f"domain_{name}_land_classes.tif")
    land_classes(c, transform, shape, path)
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_domain_type.tif")) as s:
        ice_free = s.read(1) <= 1
    hrus = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{name}_HRUs_elevation.shp")).sort_values("HRU_ID")
    settings = os.path.join(project, "settings", "SUMMA")
    veg = dict(zip(hrus["HRU_ID"].astype(int), majority(path, hrus, ice_free)))
    top = dict(zip(veg, canopy_top(os.path.join(settings, "TBL_MPTABLE.TBL"), list(veg.values()))))
    for f in ("attributes.nc", "attributes_glac.nc"):
        if not os.path.exists(os.path.join(settings, f)):
            continue
        with nc4.Dataset(os.path.join(settings, f), "a") as d:
            ids = np.asarray(d["hruId"][:]).astype(int)
            old_v, old_m = np.asarray(d["vegTypeIndex"][:]), np.asarray(d["mHeight"][:])
            d["vegTypeIndex"][:] = [veg.get(h, v) for h, v in zip(ids, old_v)]  # HRUs not in the shapefile (a stream) keep theirs
            d["mHeight"][:] = [top[h] + MHEIGHT_ABOVE if h in veg else m for h, m in zip(ids, old_m)]
            print(f"{f}: vegTypeIndex {list(old_v)} -> {list(d['vegTypeIndex'][:])}, mHeight {list(old_m)} -> {list(d['mHeight'][:])}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/ with an upland: block, or a landclass: one for vegetation")
    p.add_argument("part", choices=("surface", "upland", "vegetation"))
    p.add_argument("--only", nargs="+", choices=("dem", "land", "soil", "settings"), help="surface pieces to make, default all")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    if a.part == "upland":
        upland(c, project, name)
        return
    if a.part == "vegetation":
        vegetation(c, project, name)
        return
    transform, shape = grid(c)
    attrs = os.path.join(project, "attributes")
    pieces = a.only or ("dem", "land", "soil", "settings")
    if "dem" in pieces:
        surface_dem(c, transform, shape, os.path.join(attrs, "elevation", "dem", f"domain_{name}_elv.tif"))
    if "land" in pieces:
        land_classes(c, transform, shape, os.path.join(attrs, "landclass", f"domain_{name}_land_classes.tif"))
    if "soil" in pieces:
        soil_classes(c, transform, shape, os.path.join(attrs, "soilclass", f"domain_{name}_soil_classes.tif"))
    if "settings" in pieces:
        copy_settings(c, os.path.join(project, "settings", "SUMMA"))


if __name__ == "__main__":
    main()
