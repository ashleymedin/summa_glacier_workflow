#!/usr/bin/env python3
"""Write the glacier attributes and cold state of a SYMFLUENCE domain for SUMMA.

Starts from the domain's upland attributes.nc and coldState.nc and the glacier rasters and catchment
intersections made by glacier_rasters.py, glacier_extend.py and glacier_zonal_stats.py, and writes
attributes_glac.nc and coldstate_glac.nc beside them in settings/SUMMA:

  attributes  adds nGlac, nWtld and the per-glacier grids (bed_elev, glacierMask, cell2hruId on a UTM grid),
              each the glacier's bounding box widened by --wall-pad so the rock faces above its margins are in it
  cold state  adds the horizontal domains of each HRU (upland, clean glacier 1 and 2, debris glacier), their
              layering and starting states, and the glacier surface elevation and debris thickness grids

Domains: every HRU has an upland domain, glacier domains where it holds glacier-capable cells, and a debris
domain with a clean one beside it wherever the glacier has debris, so debris can advect. A second clean domain
is kept only where one HRU holds the whole glacier. Any domain may start with zero area.

Layering: clean glacier ice has five layers, 0.15, 0.30, 1.80, 4.75 and 23 m thick. A debris domain puts
soil layers over the same ice, as many as its debris may need (2 to 5): the fewest whose top layer of at most
--debris-top-max, each layer up to 3 times the one above, reach the thickest debris cell of the HRU, since
debris advection can thicken the domain toward it and the count is fixed for the run.
The debris is split as SUMMA re-splits it at each glacier update: the top layer the smaller of an equal share
and --debris-top-max, each layer below a fixed ratio times the one above, so thin debris splits evenly.

Starting states: glacier ice at --ice-temp (deg C), ice fraction 0.90 at the top to 0.98 at the base, no
liquid. Every soil and debris layer, the canopy and the canopy air start from each HRU's mean air temperature
over the first year of the run (the 12 forcing months from --start), the soil layers --soil-offset (deg C)
warmer, the insulation of the winter snow. Other states are taken from coldState.nc.

    ./glacier_cold_state.py data/domain_Wolverine --utm-epsg 32606 --start 2008-01
"""

import argparse
import glob
import os
import shutil
import tempfile

import geopandas as gpd
import netCDF4 as nc4
import numpy as np
import rasterio
from affine import Affine
from pyproj import CRS
from rasterio.warp import Resampling, calculate_default_transform, reproject

REAL_MISSING = -9999.0
TFREEZE = 273.16
ICE_DEPTHS = np.array([0.15, 0.45, 2.25, 7.0, 30.0])  # bottom of each glacier ice layer below the ice surface (m)
N_DOM_TYPES = 5  # upland, clean glacier 1, clean glacier 2, debris glacier, wetland
UPLAND, CLEAN1, CLEAN2, DEBRIS, WETLAND = 1, 2, 3, 4, 5


def debris_layering(thick, n_layers, top_max):
    """Thickness of each debris layer, top down (m), as glacAreaChange.f90 debrisLayering splits it."""
    top = min(thick / n_layers, top_max)
    if n_layers == 1 or top >= thick / n_layers:
        return np.full(n_layers, thick / n_layers)
    fill = lambda r: top * sum(r**k for k in range(n_layers))
    low, high = 1.0, 2.0
    while fill(high) < thick:
        high *= 2.0
    for _ in range(200):
        mid = 0.5 * (low + high)
        low, high = (mid, high) if fill(mid) < thick else (low, mid)
    depths = top * (0.5 * (low + high)) ** np.arange(n_layers)
    depths[-1] = thick - depths[:-1].sum()
    return depths


def debris_layer_count(thick, top_max, growth=3.0, fewest=2, most=5):
    """Fewest debris layers whose top layer of top_max, each up to growth times the one above, reach thick."""
    for n in range(fewest, most + 1):
        if top_max * sum(growth**k for k in range(n)) >= thick:
            return n
    return most


def first_year_air_temperature(forcing_dir, hru_ids, start):
    """Mean forcing air temperature of each HRU over the 12 monthly files *YYYYMM.nc from start (YYYY-MM), K."""
    y0, m0 = (int(v) for v in start.split("-"))
    months = {f"{y0 + (m0 - 1 + k) // 12:04d}{(m0 - 1 + k) % 12 + 1:02d}" for k in range(12)}
    total = np.zeros(len(hru_ids))
    count = 0
    found = set()
    for path in sorted(glob.glob(os.path.join(forcing_dir, "*.nc"))):
        stamp = os.path.basename(path)[-9:-3]
        if stamp not in months:
            continue
        found.add(stamp)
        with nc4.Dataset(path) as ds:
            order = [list(np.asarray(ds["hruId"][:]).astype(int)).index(h) for h in hru_ids]
            temp = np.asarray(ds["airtemp"][:], dtype=float)[:, order]
        total += np.nansum(temp, axis=0)
        count += temp.shape[0]
    if found != months:
        raise SystemExit(f"forcing months {sorted(months - found)} missing from {forcing_dir}")
    return total / count


def reproject_to_utm(src_path, dst_path, utm_epsg):
    """Reproject a raster to a UTM zone, nearest neighbour, so grid cells are in metres."""
    with rasterio.open(src_path) as src:
        utm_crs = CRS.from_epsg(utm_epsg)
        transform, width, height = calculate_default_transform(src.crs, utm_crs, src.width, src.height, *src.bounds)
        meta = src.meta.copy()
        meta.update({"crs": utm_crs, "transform": transform, "width": width, "height": height})
        with rasterio.open(dst_path, "w", **meta) as dst:
            for i in range(1, src.count + 1):
                reproject(source=rasterio.band(src, i), destination=rasterio.band(dst, i),
                          src_transform=src.transform, src_crs=src.crs,
                          dst_transform=transform, dst_crs=utm_crs, resampling=Resampling.nearest)


def grid_transforms(project_dir, domain, utm_epsg, pad=500.0):
    """The UTM affine transform of each glacier's grid, by RGI id, as read_glacier_grids cuts it (same pad)."""
    src = os.path.join(project_dir, "attributes", "glaciers", f"domain_{domain}_rgi_id_extend.tif")
    with tempfile.TemporaryDirectory() as tmp:
        reproject_to_utm(src, os.path.join(tmp, "id.tif"), utm_epsg)
        with rasterio.open(os.path.join(tmp, "id.tif")) as r:
            gid, transform, res = r.read(1), r.transform, r.res
    py, px = int(np.ceil(pad / res[1])), int(np.ceil(pad / res[0]))
    out = {}
    for g in np.unique(gid[gid > 0]):
        rows, cols = np.where(gid == g)
        y0, x0 = max(rows.min() - py, 0), max(cols.min() - px, 0)
        out[int(g)] = transform * Affine.translation(x0, y0)
    return out, CRS.from_epsg(utm_epsg)


def read_glacier_grids(project_dir, domain, utm_epsg, hru_ids, gru_ids, hru2gru, threshold, pad=0.0):
    """Per-GRU glacier grids on a UTM grid: the glaciers mostly inside each GRU, their bed, surface,
    mask, HRU of each cell, debris thickness and ablation and accumulation areas."""
    glacier_dir = os.path.join(project_dir, "attributes", "glaciers")
    dem_dir = os.path.join(project_dir, "attributes", "elevation", "dem")
    sources = {
        "bed": os.path.join(dem_dir, f"domain_{domain}_bedrock_elv_utm.tif"),  # glacier_rasters.py's, on this grid
        "surf": os.path.join(dem_dir, f"domain_{domain}_glacier_elv_utm.tif"),
        "debris": os.path.join(glacier_dir, f"domain_{domain}_debris_thickness.tif"),
        "hru": os.path.join(glacier_dir, f"domain_{domain}_hru_id.tif"),
        "id": os.path.join(glacier_dir, f"domain_{domain}_rgi_id_extend.tif"),
        "type": os.path.join(glacier_dir, f"domain_{domain}_domain_type_extend.tif"),
    }
    temp_dir = os.path.join(glacier_dir, "utm_temp")
    os.makedirs(temp_dir, exist_ok=True)
    rasters = {}
    try:
        for key, path in sources.items():
            utm_path = path if path.endswith("_utm.tif") else os.path.join(temp_dir, f"{key}_utm.tif")
            if utm_path != path:
                reproject_to_utm(path, utm_path, utm_epsg)
            with rasterio.open(utm_path) as src:
                rasters[key] = src.read(1)
                res = src.res
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if len({r.shape for r in rasters.values()}) > 1:
        raise ValueError(f"UTM grids differ: { {k: r.shape for k, r in rasters.items()} }; rerun glacier_rasters.py")
    bed, surf, debris, hru_cell, gid, dtype = (rasters[k] for k in ("bed", "surf", "debris", "hru", "id", "type"))
    cell_area = res[0] * res[1]

    n_gru = len(gru_ids)
    n_grid = np.zeros(n_gru, dtype="i4")
    storage = np.zeros(n_gru)  # glacier ice in each GRU (Gt)
    ids_in_gru = []
    for i, gru in enumerate(gru_ids):
        gru_cells = np.isin(hru_cell, hru_ids[hru2gru == gru])
        storage[i] = cell_area * np.sum(surf[gru_cells] - bed[gru_cells]) * 916.7e-9
        inside = []
        for g in np.unique(gid[gru_cells]):
            if g > 0 and np.sum(gid[gru_cells] == g) >= threshold * np.sum(gid == g):
                inside.append(g)
        n_grid[i] = len(inside)
        ids_in_gru.append(inside)
    n_glac = max(n_grid.max(), 1)
    grid_id = np.zeros((1, n_glac, n_gru), dtype="i8")
    for i, inside in enumerate(ids_in_gru):
        grid_id[0, :len(inside), i] = inside

    nx = np.zeros((1, n_glac, n_gru), dtype="i4")
    ny = np.zeros((1, n_glac, n_gru), dtype="i4")
    full = (bed.shape[0], bed.shape[1], n_glac, n_gru)
    B, S, debris_gr = np.zeros(full), np.zeros(full), np.zeros(full)
    mask, cell2hru, ctype = np.zeros(full, dtype="i4"), np.zeros(full, dtype="i8"), np.zeros(full, dtype="i4")
    abl_area = np.zeros((n_glac, n_gru))
    acc_area = np.zeros((n_glac, n_gru))
    single_glac_hru = []
    for i in range(n_gru):
        for j in range(n_grid[i]):
            rows, cols = np.where(gid == grid_id[0, j, i])
            py, px = int(np.ceil(pad / res[1])), int(np.ceil(pad / res[0]))
            y0, y1 = max(rows.min() - py, 0), min(rows.max() + 1 + py, bed.shape[0])
            x0, x1 = max(cols.min() - px, 0), min(cols.max() + 1 + px, bed.shape[1])
            ny[0, j, i], nx[0, j, i] = y1 - y0, x1 - x0
            box = (slice(0, y1 - y0), slice(0, x1 - x0), j, i)
            B[box] = bed[y0:y1, x0:x1]
            S[box] = surf[y0:y1, x0:x1]
            mask[box] = (gid[y0:y1, x0:x1] == grid_id[0, j, i]).astype("i4")
            ctype[box] = dtype[y0:y1, x0:x1]
            outside = mask[box] == 0
            B[box][outside] = S[box][outside]  # bed is the surface outside the glacier
            cell2hru[box] = hru_cell[y0:y1, x0:x1]
            debris_gr[box] = np.where(outside, 0.0, debris[y0:y1, x0:x1])
            acc_area[j, i] = cell_area * np.sum(mask[box][ctype[box] == CLEAN1])
            abl_area[j, i] = cell_area * np.sum(mask[box][(ctype[box] == CLEAN2) | (ctype[box] == DEBRIS)])
            glacier_hrus = np.unique(cell2hru[box][mask[box] == 1])
            if len(glacier_hrus) == 1:
                single_glac_hru.append(glacier_hrus[0])
    dim_y, dim_x = ny.max(), nx.max()
    B, S = B[:dim_y, :dim_x], S[:dim_y, :dim_x]
    debris_gr = np.minimum(debris_gr[:dim_y, :dim_x], S - B)  # debris no thicker than the glacier
    return {
        "n_grid": n_grid, "grid_id": grid_id, "nx": nx, "ny": ny,
        "dx": np.full((1, n_glac, n_gru), res[0]), "dy": np.full((1, n_glac, n_gru), res[1]),
        "bed": B, "surface": S, "mask": mask[:dim_y, :dim_x], "cell2hru": cell2hru[:dim_y, :dim_x],
        "debris": debris_gr, "abl_area": abl_area, "acc_area": acc_area, "storage": storage,
        "single_glac_hru": single_glac_hru,
    }


def _shp_value(gdf, sel, column):
    """A domain statistic of one HRU from a catchment intersection, or None if absent or invalid."""
    if column not in gdf.columns or not sel.any():
        return None
    value = gdf[column][sel].values[0]
    if value is None or np.isnan(value) or value < 0:
        return None
    return value


def _circular_mean_deg(values, weights):
    a = np.radians(values)
    return float(np.degrees(np.arctan2(np.sum(np.sin(a) * weights), np.sum(np.cos(a) * weights))) % 360)


def build_domains(project_dir, hru_ids, hru_area, single_glac_hru, hru_id_column):
    """Horizontal domains of each HRU from the catchment intersections: type, area, elevation, slope,
    aspect, ablation fraction and debris thickness, ordered upland, clean 1, (clean 2), debris."""
    inter = os.path.join(project_dir, "shapefiles", "catchment_intersection")
    shp_elev = gpd.read_file(os.path.join(inter, "with_dem_domain", "catchment_with_dem_domain.shp"))
    shp_area = gpd.read_file(os.path.join(inter, "with_domain_type", "catchment_with_domain_type.shp"))
    shp_debris = gpd.read_file(os.path.join(inter, "with_debris_thickness", "catchment_with_debris.shp"))
    has_debris = f"elv_mean_{DEBRIS}" in shp_elev.columns
    has_clean = f"elv_mean_{CLEAN1}" in shp_elev.columns or f"elv_mean_{CLEAN2}" in shp_elev.columns

    n_hru = len(hru_ids)
    shape = (1, n_hru, N_DOM_TYPES)
    dom = {
        "DOMarea": np.zeros(shape), "DOMelev": np.full(shape, REAL_MISSING),
        "DOMtan_slope": np.full(shape, REAL_MISSING), "DOMaspect": np.full(shape, REAL_MISSING),
        "domType": np.zeros(shape, dtype="i4"),
    }
    n_dom = 0
    for i, hru in enumerate(hru_ids):
        sel_elev = shp_elev[hru_id_column].astype(int) == hru
        sel_area = shp_area[hru_id_column].astype(int) == hru
        k = 0
        if sel_elev.any():
            for t in range(1, N_DOM_TYPES + 1):
                elev = _shp_value(shp_elev, sel_elev, f"elv_mean_{t}")
                if elev is not None:
                    dom["DOMelev"][0, i, k] = elev
                    dom["DOMarea"][0, i, k] = shp_area[f"domType_{t}"][sel_area].values[0]
                    dom["DOMtan_slope"][0, i, k] = shp_elev[f"tsl_mean_{t}"][sel_elev].values[0]
                    dom["DOMaspect"][0, i, k] = shp_elev[f"asp_mean_{t}"][sel_elev].values[0]
                    dom["domType"][0, i, k] = t
                    k += 1
                elif t == UPLAND or (t == CLEAN1 and has_debris and not has_clean) or (t == DEBRIS and has_debris):
                    dom["domType"][0, i, k] = t  # zero-area domain, so the glacier can grow or debris advect into it
                    k += 1
        n_dom = max(n_dom, k)
    for i in range(n_hru):  # cell counts to areas
        total = dom["DOMarea"][0, i].sum()
        if total > 0:
            dom["DOMarea"][0, i] = hru_area[i] * dom["DOMarea"][0, i] / total

    debris_thick = np.zeros(n_hru)
    for i, hru in enumerate(hru_ids):
        value = _shp_value(shp_debris, shp_debris[hru_id_column].astype(int) == hru, "debri_mean")
        debris_thick[i] = 0.0 if value is None else value

    abl_frac = np.zeros(shape)
    abl_frac[(dom["domType"] == CLEAN2) | (dom["domType"] == DEBRIS)] = 1.0
    keys = ("DOMelev", "DOMtan_slope", "DOMaspect", "DOMarea", "domType")
    for i, hru in enumerate(hru_ids):
        if hru in single_glac_hru:
            continue
        if dom["domType"][0, i, 1] == CLEAN1 and dom["domType"][0, i, 2] == CLEAN2:
            a1, a2 = dom["DOMarea"][0, i, 1], dom["DOMarea"][0, i, 2]
            if a1 > 0:
                if a2 > 0:  # merge clean 2 into clean 1, area-weighted
                    for key in ("DOMelev", "DOMtan_slope"):
                        dom[key][0, i, 1] = (dom[key][0, i, 1] * a1 + dom[key][0, i, 2] * a2) / (a1 + a2)
                    dom["DOMaspect"][0, i, 1] = _circular_mean_deg(dom["DOMaspect"][0, i, 1:3], [a1, a2])
                    abl_frac[0, i, 1] = (abl_frac[0, i, 1] * a1 + abl_frac[0, i, 2] * a2) / (a1 + a2)
                    dom["DOMarea"][0, i, 1] = a1 + a2
            else:
                for key in ("DOMelev", "DOMtan_slope", "DOMaspect", "DOMarea"):
                    dom[key][0, i, 1] = dom[key][0, i, 2]
                abl_frac[0, i, 1] = abl_frac[0, i, 2]
            for key in keys:
                dom[key][0, i, 2:n_dom - 1] = dom[key][0, i, 3:n_dom]
            abl_frac[0, i, 2:n_dom - 1] = abl_frac[0, i, 3:n_dom]
            for key in ("DOMelev", "DOMtan_slope", "DOMaspect"):
                dom[key][0, i, n_dom - 1] = REAL_MISSING
            abl_frac[0, i, n_dom - 1] = REAL_MISSING
            dom["DOMarea"][0, i, n_dom - 1] = 0
            dom["domType"][0, i, n_dom - 1] = 0
        elif dom["domType"][0, i, 1] == CLEAN2:
            dom["domType"][0, i, 1] = CLEAN1  # a lone clean 2 is clean 1
    while n_dom > 1 and np.all(dom["domType"][0, :, n_dom - 1] == 0):
        n_dom -= 1
    for key in dom:
        dom[key] = dom[key][:, :, :n_dom]
    dom["scalarAblFrac"] = abl_frac[:, :, :n_dom]
    dom["DOMcontourLength"] = np.sqrt(dom["DOMarea"])  # square-root of area until a real contour length is used
    return dom, debris_thick


def build_layers(dom_type, debris_thick, debris_max, upland_heights, upland_nsoil, upland_nsnow, a):
    """Layer counts and interface heights of every domain (heights indexed [dom, hru, interface])."""
    n_hru, n_dom = dom_type.shape[1], dom_type.shape[2]
    n_glce = len(ICE_DEPTHS)
    counts = {k: np.zeros((1, n_hru, n_dom)) for k in ("nSnow", "nLake", "nSoil", "nGlce")}
    columns = {}
    for i in range(n_hru):
        for j in range(n_dom):
            t = dom_type[0, i, j]
            if t == UPLAND:
                counts["nSoil"][0, i, j], counts["nSnow"][0, i, j] = upland_nsoil[i], upland_nsnow[i]
                columns[(i, j)] = upland_heights[i]
            elif t in (CLEAN1, CLEAN2):
                counts["nGlce"][0, i, j] = n_glce
                columns[(i, j)] = np.concatenate([[0.0], ICE_DEPTHS])
            elif t == DEBRIS:
                thick = max(debris_thick[i], a.debris_min)
                n_debris = debris_layer_count(max(thick, debris_max[i]), a.debris_top_max)
                debris = np.cumsum(debris_layering(thick, n_debris, a.debris_top_max))
                counts["nSoil"][0, i, j], counts["nGlce"][0, i, j] = n_debris, n_glce
                columns[(i, j)] = np.concatenate([[0.0], debris, thick + ICE_DEPTHS])
            elif t == WETLAND:
                raise SystemExit("wetland domains are not set up yet")
    n_toto = int(max(sum(counts[k][0, i, j] for k in counts) for i in range(n_hru) for j in range(n_dom)))
    heights = np.zeros((n_dom, n_hru, n_toto + 1))
    for (i, j), column in columns.items():
        heights[j, i, :len(column)] = column
    return counts, heights, n_toto


def write_var(ds, name, dims, dtype, values, fill="-999.0"):
    """One variable of the output file, with the fill value the domain's other SUMMA files use."""
    var = ds.createVariable(name, dtype, dims, fill_value=fill)
    var[:] = values


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("project_dir", help="SYMFLUENCE domain directory, domain_<name>")
    p.add_argument("--domain", help="domain name, default the project directory's name after domain_")
    p.add_argument("--utm-epsg", type=int, required=True, help="UTM zone for the glacier grids, e.g. 32606 (6N)")
    p.add_argument("--attributes", default="attributes.nc", help="upland attributes in settings/SUMMA")
    p.add_argument("--cold-state", default="coldState.nc", help="upland cold state in settings/SUMMA")
    p.add_argument("--forcing", help="forcing directory for the mean annual air temperature, default forcing/SUMMA_input")
    p.add_argument("--start", required=True, help="first forcing month of the run, YYYY-MM; its 12 months set the start")
    p.add_argument("--soil-offset", type=float, default=1.5, help="soil and debris start this much above the air, deg C")
    p.add_argument("--ice-temp", type=float, default=-5.0, help="glacier ice starting temperature, deg C")
    p.add_argument("--debris-min", type=float, default=0.02, help="thinnest debris, m (glacAreaChange.f90 min_thickness)")
    p.add_argument("--debris-top-max", type=float, default=0.05, help="thickest top debris layer, m (maxDebrisTop)")
    p.add_argument("--gru-threshold", type=float, default=0.8,
                   help="fraction of a glacier's cells that must lie in a GRU for it to belong there")
    p.add_argument("--wall-pad", type=float, default=500.0,
                   help="ground kept around each glacier grid, m, at least glacAreaChange.f90's wallSearchDist")
    p.add_argument("--hru-id-column", default="HRU_ID", help="HRU id column of the catchment intersections")
    p.add_argument("--suffix", default="_glac", help="suffix of the written attributes and cold state files")
    p.add_argument("--output-dir", help="where to write them, default settings/SUMMA")
    a = p.parse_args()

    project_dir = os.path.abspath(os.path.expanduser(a.project_dir))
    domain = a.domain or os.path.basename(project_dir.rstrip("/")).replace("domain_", "", 1)
    settings = os.path.join(project_dir, "settings", "SUMMA")
    attr_in = os.path.join(settings, a.attributes)
    out_dir = os.path.abspath(os.path.expanduser(a.output_dir)) if a.output_dir else settings
    os.makedirs(out_dir, exist_ok=True)
    attr_out = os.path.join(out_dir, a.attributes[:-3] + a.suffix + ".nc")
    cold_in = os.path.join(settings, a.cold_state)
    cold_out = os.path.join(out_dir, a.cold_state[:-3].lower() + a.suffix + ".nc")

    with nc4.Dataset(attr_in) as ds:
        hru_ids = np.asarray(ds["hruId"][:]).astype(int)
        hru_area = np.asarray(ds["HRUarea"][:], dtype=float)
        gru_ids = np.asarray(ds["gruId"][:]).astype(int)
        hru2gru = np.asarray(ds["hru2gruId"][:]).astype(int)

    grids = read_glacier_grids(project_dir, domain, a.utm_epsg, hru_ids, gru_ids, hru2gru, a.gru_threshold, a.wall_pad)
    dom, debris_thick = build_domains(project_dir, hru_ids, hru_area, grids["single_glac_hru"], a.hru_id_column)

    with nc4.Dataset(cold_in) as ds:
        upland_heights = np.asarray(ds["iLayerHeight"][:], dtype=float).T
        upland_nsoil = np.asarray(ds["nSoil"][:]).reshape(-1)
        upland_nsnow = np.asarray(ds["nSnow"][:]).reshape(-1)
        states = {}
        for name, default in (("scalarCanopyIce", 0), ("scalarCanopyLiq", 0), ("scalarSnowDepth", 0), ("scalarSWE", 0),
                              ("scalarSfcMeltPond", 0), ("scalarAquiferStorage", 1.0), ("scalarSnowAlbedo", 0),
                              ("mLayerVolFracLiq", 0.2), ("mLayerMatricHead", -1.0), ("dt_init", 3600)):
            states[name] = float(np.asarray(ds[name][:]).flat[0]) if name in ds.variables else default
    debris_max = np.array([grids["debris"][grids["cell2hru"] == hru].max(initial=0.0) for hru in hru_ids])
    counts, heights, n_toto = build_layers(dom["domType"], debris_thick, debris_max, upland_heights, upland_nsoil, upland_nsnow, a)
    depths = np.maximum(heights[:, :, 1:] - heights[:, :, :-1], 0.0)
    n_dom = dom["domType"].shape[2]
    n_hru = len(hru_ids)
    mid_soil = int(counts["nSoil"].max())

    forcing = a.forcing or os.path.join(project_dir, "forcing", "SUMMA_input")
    maat = first_year_air_temperature(forcing, list(hru_ids), a.start)
    for i, hru in enumerate(hru_ids):
        thick = max(debris_thick[i], a.debris_min)
        n = debris_layer_count(max(thick, debris_max[i]), a.debris_top_max)
        print(f"HRU {hru}: first-year mean air temperature from {a.start} {maat[i] - TFREEZE:.2f} degC, debris {thick:.3f} m "
              f"(mapped {debris_thick[i]:.3f} m, thickest cell {debris_max[i]:.2f} m) in {n} layers "
              f"{np.round(debris_layering(thick, n, a.debris_top_max), 3).tolist()} m")

    temp = np.zeros((n_toto, n_hru, n_dom))
    ice = np.zeros((n_toto, n_hru, n_dom))
    liq = np.full((n_toto, n_hru, n_dom), states["mLayerVolFracLiq"])
    for i in range(n_hru):
        for j in range(n_dom):
            temp[:, i, j] = maat[i] + a.soil_offset
            n_glce = int(counts["nGlce"][0, i, j])
            if n_glce > 0:
                top = int(counts["nSnow"][0, i, j] + counts["nLake"][0, i, j] + counts["nSoil"][0, i, j])
                k = np.arange(n_glce)
                temp[top:top + n_glce, i, j] = TFREEZE + a.ice_temp
                ice[top:top + n_glce, i, j] = 0.90 + 0.08 * k**2 / (n_glce - 1) ** 2  # less air with depth
                liq[top:top + n_glce, i, j] = 0.0
    air = np.broadcast_to(maat[None, :, None], (1, n_hru, n_dom))

    # attributes: the upland file plus the glacier grids
    shutil.copy(attr_in, attr_out)
    n_glac = grids["grid_id"].shape[1]
    with nc4.Dataset(attr_out, "a") as ds:
        write_var(ds, "nGlac", ("gru",), "i4", grids["n_grid"], fill="-999")
        write_var(ds, "nWtld", ("gru",), "i4", np.zeros(len(gru_ids), dtype="i4"), fill="-999")
        ds.createDimension("grid", n_glac)
        ds.createDimension("xgrid", grids["bed"].shape[1])
        ds.createDimension("ygrid", grids["bed"].shape[0])
        write_var(ds, "nGrid", ("gru",), "i4", grids["n_grid"], fill="-999")
        write_var(ds, "gridId", ("grid", "gru"), "i8", grids["grid_id"], fill="-999")
        write_var(ds, "nx", ("grid", "gru"), "i4", grids["nx"], fill="-999")
        write_var(ds, "ny", ("grid", "gru"), "i4", grids["ny"], fill="-999")
        write_var(ds, "dy", ("grid", "gru"), "f8", grids["dy"])
        write_var(ds, "dx", ("grid", "gru"), "f8", grids["dx"])
        grid_dims = ("ygrid", "xgrid", "grid", "gru")
        write_var(ds, "bed_elev", grid_dims, "f8", grids["bed"])
        write_var(ds, "glacierMask", grid_dims, "i4", grids["mask"], fill="-999")
        write_var(ds, "cell2hruId", grid_dims, "i8", grids["cell2hru"], fill="-999")

    # cold state
    with nc4.Dataset(cold_out, "w", format="NETCDF4") as ds:
        for name, size in (("hru", n_hru), ("gru", len(gru_ids)), ("scalarv", 1), ("midSoil", mid_soil),
                           ("midToto", n_toto), ("ifcToto", n_toto + 1), ("dom", n_dom), ("glac", n_glac)):
            ds.createDimension(name, size)
        var = ds.createVariable("hruId", "int", ("hru",), fill_value="-999")
        var[:] = hru_ids
        var.long_name = "USGS HUC12 ID"
        var = ds.createVariable("gruId", "int", ("gru",), fill_value="-999")
        var[:] = gru_ids
        var.long_name = "GRU ID"
        hd = ("hru", "dom")
        write_var(ds, "iLayerHeight", ("ifcToto",) + hd, "f8", heights.T)
        write_var(ds, "mLayerDepth", ("midToto",) + hd, "f8", depths.T)
        for name in ("nSnow", "nLake", "nSoil", "nGlce"):
            write_var(ds, name, ("scalarv",) + hd, "f8", counts[name])
        for name in ("domType", "DOMarea", "DOMelev", "DOMtan_slope", "DOMaspect", "DOMcontourLength", "scalarAblFrac"):
            write_var(ds, name, ("scalarv",) + hd, "f8", dom[name])
        write_var(ds, "glacierAblArea", ("glac", "gru"), "f8", grids["abl_area"])
        write_var(ds, "glacierAccArea", ("glac", "gru"), "f8", grids["acc_area"])
        write_var(ds, "glacId", ("glac", "gru"), "i8", grids["grid_id"][0], fill="-999")
        write_var(ds, "basin__GlacierStorage", ("gru",), "f8", grids["storage"])
        scalar = ("scalarv",) + hd
        for name in ("scalarCanopyIce", "scalarCanopyLiq", "scalarSnowDepth", "scalarSWE", "scalarSfcMeltPond",
                     "scalarAquiferStorage", "scalarSnowAlbedo"):
            write_var(ds, name, scalar, "f8", np.full((1, n_hru, n_dom), states[name]))
        write_var(ds, "scalarCanairTemp", scalar, "f8", air)
        write_var(ds, "scalarCanopyTemp", scalar, "f8", air)
        write_var(ds, "mLayerTemp", ("midToto",) + hd, "f8", temp)
        write_var(ds, "mLayerVolFracIce", ("midToto",) + hd, "f8", ice)
        write_var(ds, "mLayerVolFracLiq", ("midToto",) + hd, "f8", liq)
        write_var(ds, "mLayerMatricHead", ("midSoil",) + hd, "f8", np.full((mid_soil, n_hru, n_dom), states["mLayerMatricHead"]))
        for name in ("glacMass4AreaChange", "scalarGlceWE"):
            write_var(ds, name, scalar, "f8", np.zeros((1, n_hru, n_dom)))
        write_var(ds, "dt_init", scalar, "f8", np.full((1, n_hru, n_dom), states["dt_init"]))
        ds.createDimension("grid", n_glac)
        ds.createDimension("xgrid", grids["bed"].shape[1])
        ds.createDimension("ygrid", grids["bed"].shape[0])
        write_var(ds, "gridId", ("grid", "gru"), "i8", grids["grid_id"], fill="-999")
        write_var(ds, "surface_elev", ("ygrid", "xgrid", "grid", "gru"), "f8", grids["surface"])
        write_var(ds, "debris_thick", ("ygrid", "xgrid", "grid", "gru"), "f8", grids["debris"])
    print(f"wrote {attr_out}\nwrote {cold_out}")


if __name__ == "__main__":
    main()
