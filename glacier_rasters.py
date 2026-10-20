#!/usr/bin/env python3
"""Make the glacier rasters of a SYMFLUENCE domain on its surface DEM grid.

From the global glacier products (each downloaded by hand, see README.md) writes, in attributes/glaciers:

  domain_<name>_domain_type.tif       1 upland, 2 accumulation, 3 clean ablation, 4 debris ablation
  domain_<name>_rgi_id.tif            RGI 6.0 id as region*100000 + number, 0 off glacier
  domain_<name>_debris_thickness.tif  debris thickness (m), non-zero only where the type is 4

and in attributes/elevation/dem domain_<name>_glacier_elv.tif, the glacier surface: the DEM, with the survey DEM
of the USGS outline on that glacier where usgs_outline names one (levelled to the DEM on the ground around it);
and domain_<name>_bedrock_elv.tif, that surface less the glacier thickness.

Glacier outlines are RGI 6.0, replaced by the Herreid and Pellicciotti (2020) outline where it has one, and by a
USGS survey outline (McNeil et al. 2019, doi:10.5066/P9R8BP3K) where the YAML's usgs_outline names one. Their
ablation zones (buffered 50 m, clipped to the glacier) set the ablation area; a glacier without one uses Zmed
as its equilibrium line. Debris is their debris cover, never in the accumulation zone, and every glacier keeps
at least its highest cells as accumulation. Debris thickness is Rounce et al. (2021), nearest neighbour, with
thicknesses at or below --min-debris (0.04 m) raised to it (Herreid 2021; Rounce et al. 2018). Glacier
thickness is Millan et al. (2022), zero off the outlines and filled from the nearest Millan cell where an
outline reaches past it. It also prints each glacier's lateral moraine width, the mean thinnest width of its
debris polygons, for latMoraineWidth.

    ./glacier_rasters.py domains/wolverine.yaml
"""

import argparse
import os
import shutil

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject
from scipy.interpolate import griddata
from scipy.ndimage import distance_transform_edt
from shapely.affinity import rotate
from shapely.geometry import Point, box, shape
from shapely.ops import unary_union

from domain_config import load_config

UPLAND, ACCUMULATION, CLEAN_ABLATION, DEBRIS_ABLATION = 1, 2, 3, 4
HERE = os.path.dirname(os.path.abspath(__file__))


def elevation_polygon(src, geometry, z, side):
    """The part of a glacier above (side 'high') or below ('low') elevation z, z held within its elevations."""
    image = mask(src, [geometry], crop=True)
    out_image, out_transform = image[0][0], image[1]
    valid = out_image[out_image > 0]
    if side == "high":
        selected = (out_image > min(z, valid.max())) & (out_image > 0)
    else:
        selected = (out_image < max(z, valid.min())) & (out_image > 0)
    polygons = [shape(g) for g, v in shapes(selected.astype(np.int16), transform=out_transform) if v == 1]
    return unary_union(polygons) if polygons else None


def thinnest_width(polygon):
    """Thinnest width of a polygon's convex hull (m in a projected CRS), the largest part of a multipolygon."""
    if polygon.geom_type == "MultiPolygon":
        polygon = max(polygon.geoms, key=lambda p: p.area)
    hull = polygon.convex_hull
    coords = np.array(hull.exterior.coords)
    width = np.inf
    for p1, p2 in zip(coords[:-1], coords[1:]):
        angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
        bounds = rotate(hull, -angle, origin=(0, 0)).bounds
        width = min(width, bounds[3] - bounds[1])
    return width


def mosaic_to_dem(files, target_crs, dem_shape, dem_transform, tmp_dir):
    """Mosaic rasters reprojected to the DEM's CRS, and interpolate them nearest-neighbour onto the DEM grid."""
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        reprojected = []
        for n, path in enumerate(files):
            with rasterio.open(path) as src:
                transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds)
                meta = src.meta.copy()
                meta.update({"crs": target_crs, "transform": transform, "width": width, "height": height})
                out = os.path.join(tmp_dir, f"reprojected_{n}.tif")
                with rasterio.open(out, "w", **meta) as dst:
                    for i in range(1, src.count + 1):
                        reproject(source=rasterio.band(src, i), destination=rasterio.band(dst, i),
                                  src_transform=src.transform, src_crs=src.crs, dst_transform=transform,
                                  dst_crs=target_crs, resampling=Resampling.nearest)
            reprojected.append(out)
        sources = [rasterio.open(p) for p in reprojected]
        mosaic, mosaic_transform = merge(sources)
        for s in sources:
            s.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # subset the mosaic to the DEM's bounds
    dem_box = box(*rasterio.transform.array_bounds(dem_shape[0], dem_shape[1], dem_transform))
    mosaic_box = box(*rasterio.transform.array_bounds(mosaic.shape[1], mosaic.shape[2], mosaic_transform))
    minx, miny, maxx, maxy = dem_box.intersection(mosaic_box).bounds
    col0, row0 = ~mosaic_transform * (minx, maxy)
    col1, row1 = ~mosaic_transform * (maxx, miny)
    subset = mosaic[0][int(row0):int(row1), int(col0):int(col1)]
    subset_transform = from_bounds(minx, miny, maxx, maxy, subset.shape[1], subset.shape[0])

    rows, cols = np.indices(dem_shape)
    x, y = rasterio.transform.xy(dem_transform, rows, cols)
    src_rows, src_cols = np.indices(subset.shape)
    sx, sy = rasterio.transform.xy(subset_transform, src_rows, src_cols)
    points = np.vstack([np.array(sx).ravel(), np.array(sy).ravel()]).T
    return griddata(points, subset.ravel(), (np.array(x).ravel(), np.array(y).ravel()), method="nearest").reshape(dem_shape)


def survey_surface(dem, glacier, src, outlines, path, buffer=1000.0):
    """The DEM with a survey DEM's mean on the glacier cells, levelled to the DEM by their median difference on
    the ground within buffer (m) of the outlines."""
    with rasterio.open(path) as s:
        z = s.read(1, masked=True).astype(np.float64).filled(np.nan)
        on_ice = geometry_mask(list(outlines.to_crs(s.crs).geometry), transform=s.transform, invert=True, out_shape=z.shape)
        near = geometry_mask(list(outlines.to_crs(s.crs).buffer(buffer)), transform=s.transform, invert=True, out_shape=z.shape)
        means = {}
        for key, keep in (("ice", on_ice), ("ground", near & ~on_ice)):
            out = np.full(dem.shape, np.nan)
            reproject(np.where(keep, z, np.nan), out, src_transform=s.transform, src_crs=s.crs, src_nodata=np.nan,
                      dst_transform=src.transform, dst_crs=src.crs, dst_nodata=np.nan, resampling=Resampling.average)
            means[key] = out
    offset = np.nanmedian(dem - means["ground"])
    print(f"{os.path.basename(path)}: {offset:+.1f} m to the DEM on {np.isfinite(means['ground']).sum()} ground cells")
    surface = dem.copy()
    fill = glacier & np.isfinite(means["ice"])
    surface[fill] = means["ice"][fill] + offset
    return surface


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--output-dir", help="write the rasters here instead of the domain's attributes folders")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    glacier_dir = a.output_dir or os.path.join(project, "attributes", "glaciers")
    dem_dir = os.path.join(project, "attributes", "elevation", "dem")
    bed_dir = a.output_dir or dem_dir
    os.makedirs(glacier_dir, exist_ok=True)

    src = rasterio.open(os.path.join(dem_dir, f"domain_{name}_elv.tif"))
    dem = src.read(1)
    meta = src.meta.copy()
    crs = src.crs
    lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
    bbox = box(lon_min, lat_min, lon_max, lat_max)
    region = c["rgi6_region"]  # e.g. 01Alaska
    rnum, rname = region[:2], region[2:]

    rgi = gpd.read_file(os.path.join(c["data"]["rgi"], f"nsidc0770_{rnum}.rgi60.{rname}", f"{rnum}_rgi60_{rname}.shp")).to_crs(crs)
    rgi = rgi[rgi.geometry.within(bbox)].copy()
    print(rgi[["RGIId", "Name", "Area", "Zmed"]].to_string(index=False))

    s1 = os.path.join(c["data"]["debris_extent"], "S1", region)
    size = str(c.get("min_glacier_size_km2", 1))
    deb = gpd.read_file(os.path.join(s1, f"{region}_minGl{size}km2_debrisCover.shp")).to_crs(crs)
    abl = gpd.read_file(os.path.join(s1, f"{region}_ablationZone.shp")).to_crs(crs)
    glc = gpd.read_file(os.path.join(s1, f"{region}_minGl1km2.shp")).to_crs(crs)
    deb, abl, glc = (g[g.geometry.within(bbox)].copy() for g in (deb, abl, glc))
    glc["RGIId"] = glc["RGIId"].str.replace("RGI50", "RGI60")  # the outlines are named RGI50 but are RGI 6.0 ids
    for i, glacier in rgi.iterrows():
        if glacier["RGIId"] in glc["RGIId"].values:
            rgi.at[i, "geometry"] = glc[glc["RGIId"] == glacier["RGIId"]]["geometry"].values[0]
    usgs = c.get("usgs_outline")
    if usgs:
        u = gpd.read_file(c["data"]["usgs_outlines"]).to_crs(crs)
        u = u[(u["Glacier"] == usgs["glacier"]) & (u["Date"] == usgs["date"])].geometry.union_all()
        i = rgi.geometry.intersection(u).area.idxmax()  # the RGI glacier it overlaps most
        print(f"{rgi.at[i, 'RGIId']}: USGS outline of {usgs['date']}")
        rgi.at[i, "geometry"] = u
    deb = gpd.overlay(deb, rgi, how="intersection")
    abl = gpd.overlay(abl, rgi, how="intersection")
    abl = abl.to_crs(c["utm_crs"])
    abl["geometry"] = abl.geometry.buffer(50)  # ablation zones can stop short of the glacier edge
    abl = gpd.overlay(abl.to_crs(crs), glc, how="intersection")

    low = []
    for _, glacier in rgi.iterrows():
        if glacier["RGIId"] not in abl["RGIId_1"].values:  # no ablation zone: Zmed is the equilibrium line
            poly = elevation_polygon(src, glacier.geometry, glacier["Zmed"], "low")
            if poly:
                low.append({**glacier.to_dict(), "geometry": poly})
    if low:
        abl = pd.concat([abl, gpd.GeoDataFrame(low, columns=rgi.columns, crs=crs)], ignore_index=True)
    acc = gpd.overlay(rgi, abl, how="difference")
    deb = gpd.overlay(deb, acc, how="difference")  # no debris in the accumulation zone

    moraine = deb.to_crs(c["utm_crs"])
    for gid in rgi["RGIId"]:
        polys = [g for g in moraine[moraine["RGIId"] == gid].geometry if g.is_valid and not g.is_empty and g.area > 1e4]
        if polys:
            print(f"{gid}: lateral moraine width {np.mean([thinnest_width(g) for g in polys]):.0f} m "
                  f"from {len(polys)} debris polygons")

    def burn(gdf, value, array):
        for geom in gdf.geometry:
            array[geometry_mask([geom], transform=src.transform, invert=True, out_shape=dem.shape)] = value

    dtype = np.full(dem.shape, UPLAND, dtype=np.int16)
    burn(acc, ACCUMULATION, dtype)
    burn(abl, CLEAN_ABLATION, dtype)
    burn(deb, DEBRIS_ABLATION, dtype)
    high = []
    for _, glacier in rgi.iterrows():
        inside = geometry_mask([glacier.geometry], transform=src.transform, invert=True, out_shape=dem.shape)
        if not np.any(dtype[inside] == ACCUMULATION):  # every glacier keeps an accumulation zone
            poly = elevation_polygon(src, glacier.geometry, glacier["Zmax"], "high")
            if poly:
                high.append({**glacier.to_dict(), "geometry": poly})
    if high:
        acc = pd.concat([acc, gpd.GeoDataFrame(high, columns=rgi.columns, crs=crs)], ignore_index=True)
    burn(acc, ACCUMULATION, dtype)
    rgi_id = np.zeros(dem.shape, dtype=np.int32)
    for _, glacier in rgi.iterrows():
        inside = geometry_mask([glacier.geometry], transform=src.transform, invert=True, out_shape=dem.shape)
        rgi_id[inside] = int(glacier["RGIId"][9:]) + int(glacier["RGIId"][6:8]) * 100000
    dtype[rgi_id == 0] = UPLAND  # ablation zones are clipped to the Herreid and Pellicciotti outline, not the final one
    meta.update(count=1, dtype="int16")
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_domain_type.tif"), "w", **meta) as dst:
        dst.write(dtype, 1)

    meta.update(count=1, dtype="int32")
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_rgi_id.tif"), "w", **meta) as dst:
        dst.write(rgi_id, 1)

    rn = str(int(rnum))
    thick_files = []
    for gid in rgi["RGIId"]:
        for suffix in ("_hdts_m.tif", "_hdts_m_extrap.tif"):  # calibrated, else extrapolated
            path = os.path.join(c["data"]["debris_thickness"], f"region{rn}", f"HMA_DTE_{rn}.{gid[9:]}{suffix}")
            if os.path.exists(path):
                thick_files.append(path)
                break
    debris = np.zeros(dem.shape, dtype=np.float32)
    if thick_files:
        values = mosaic_to_dem(thick_files, crs, dem.shape, src.transform, os.path.join(glacier_dir, "dtk_temp"))
        values[values >= 1.e19] = 0  # no-data fill
        values[values <= c.get("min_debris_thickness", 0.04)] = c.get("min_debris_thickness", 0.04)
        debris[dtype == DEBRIS_ABLATION] = values[dtype == DEBRIS_ABLATION]
    meta.update(count=1, dtype="float32")
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_debris_thickness.tif"), "w", **meta) as dst:
        dst.write(debris, 1)

    ice_files = sorted(f for f in os.listdir(os.path.join(c["data"]["ice_thickness"], f"RGI-{rn}"))
                       if f.startswith(f"THICKNESS_RGI-{rn}.") and f.endswith("tif"))
    ice = mosaic_to_dem([os.path.join(c["data"]["ice_thickness"], f"RGI-{rn}", f) for f in ice_files],
                        crs, dem.shape, src.transform, os.path.join(glacier_dir, "tk_temp"))
    ice = np.where(np.isfinite(ice) & (ice > 0) & (rgi_id > 0), ice, 0)
    glacier, thick = rgi_id > 0, ice > 0
    if np.any(glacier & ~thick):  # outline cells Millan leaves bare take the nearest Millan thickness
        _, (r, k) = distance_transform_edt(~thick, return_indices=True)
        ice[glacier & ~thick] = ice[r, k][glacier & ~thick]

    surface = dem.astype(np.float64)
    if usgs and usgs.get("dem"):
        surface = survey_surface(surface, glacier, src, rgi.to_crs(c["utm_crs"]), os.path.join(HERE, usgs["dem"]))
    bed = np.maximum(surface - ice, 0)
    with rasterio.open(os.path.join(bed_dir, f"domain_{name}_bedrock_elv.tif"), "w", **meta) as dst:
        dst.write(bed.astype(np.float32), 1)
    with rasterio.open(os.path.join(bed_dir, f"domain_{name}_glacier_elv.tif"), "w", **meta) as dst:
        dst.write(surface.astype(np.float32), 1)
    src.close()
    print(f"wrote the domain type, RGI id and debris rasters to {glacier_dir} and the bed to {bed_dir}")


if __name__ == "__main__":
    main()
