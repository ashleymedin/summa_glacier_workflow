#!/usr/bin/env python3
"""Check a domain's starting glacier and debris extent against late-summer satellite imagery.

For each requested year, takes the late-summer scene with the least cloud and snow over the domain's bounding box from Microsoft
Planetary Computer (Landsat Collection 2 Level-2, or Sentinel-2 Level-2A), on a 30 m grid in the domain's
utm_crs, and maps:

  ice     snow and ice, NDSI = (green - SWIR1)/(green + SWIR1) >= --ndsi (0.4), not water
  water   NDWI = (green - NIR)/(green + NIR) >= --ndwi (0.3) and NIR < 0.12
  cloud   green and SWIR1 both above --cloud (0.25): bright in the shortwave infrared, which snow and ice
          are not (the scenes' own flags call much of the snow and steep shade cloud); also any cell off the
          scene's footprint

inside the basin (cells of domain_<name>_hru_id.tif), against the setup's glacier (domain types 2-4 of
domain_<name>_domain_type.tif, the glaciers the model holds) and its debris (type 4). Inside the setup glacier,
cells that are not ice, water or cloud are taken as debris or rock. Writes, in observations/imagery of the
domain:

  imagery_<sensor>_<date>.csv    areas (km2) per glacier: setup glacier and debris, image ice inside and
                                 beyond the setup glacier, image debris, and the image-ice patch each lies in
  imagery_<sensor>_<date>.tif    classes: 1 ice in, 2 debris or rock in, 3 ice beyond the setup glacier,
                                 4 water, 5 cloud, 0 other
  imagery_<sensor>_<date>.png    false colour (SWIR1, NIR, green) with the setup outlines, and the classes

Glaciers whose cells share one connected patch of image ice were joined on that date.

    ./check_glacier_imagery.py domains/gulkana.yaml --landsat 2009 --sentinel 2020
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import planetary_computer
import pystac_client
import rasterio
from matplotlib.colors import ListedColormap
from netCDF4 import Dataset
from odc.stac import load
from rasterio.warp import Resampling, reproject
from scipy import ndimage

from domain_config import load_config

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SENSORS = {  # collection, bands (green, red, NIR, SWIR1, flags), scale, offset
    "landsat": ("landsat-c2-l2", ["green", "red", "nir08", "swir16", "qa_pixel"], 2.75e-5, -0.2),
    "sentinel": ("sentinel-2-l2a", ["B03", "B04", "B08", "B11", "SCL"], 1e-4, 0.0),
}
CLASSES = ["other", "ice in glacier", "debris or rock in glacier", "ice beyond glacier", "water", "cloud or no data"]
COLOURS = ["#f2f2f2", "#4f9fd8", "#a0522d", "#b8e0f5", "#1f3b73", "#9e9e9e"]


def scene(sensor, year, bbox, crs, max_cloud, months, cloud_refl, inside):
    """The candidate scene with the least cloud over the box: (item, green, red, nir, swir, cloud)."""
    coll, bands, scale, offset = SENSORS[sensor]
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    items = [i for i in cat.search(collections=[coll], bbox=bbox, datetime=f"{year}-{months[0]:02d}-01/{year}-{months[1]:02d}-30",
                                   query={"eo:cloud_cover": {"lt": max_cloud}}).items()]
    if sensor == "landsat" and any(i.properties.get("platform") != "landsat-7" for i in items):
        items = [i for i in items if i.properties.get("platform") != "landsat-7"]  # no scan-line gaps
    best = None
    for item in sorted(items, key=lambda i: i.properties["eo:cloud_cover"])[:8]:
        ds = load([item], bands=bands, crs=crs, resolution=30, bbox=bbox, resampling={"*": "bilinear", bands[4]: "nearest"})
        off = offset
        if sensor == "sentinel" and float(item.properties.get("s2:processing_baseline", "0")) >= 4.0:
            off = -0.1  # Sentinel-2 Level-2A offset from processing baseline 04.00
        raw = [np.asarray(ds[b].isel(time=0), float) for b in bands[:4]]
        g, r, n, s = (x * scale + off for x in raw)
        nodata = (raw[0] == 0) | (raw[3] == 0) | ~np.isfinite(raw[0])  # off the scene's footprint
        cloud = ((g > cloud_refl) & (s > cloud_refl)) | nodata
        with np.errstate(invalid="ignore", divide="ignore"):
            snow = (g - s) / (g + s) >= 0.4
        basin = inside(ds)
        frac = cloud[basin].mean() + (snow & ~nodata)[basin].mean()  # the least cloud, gap and snow beside the ice
        if best is None or frac < best[0] - 0.005:
            best = (frac, item, g, r, n, s, cloud, ds)
    if best is None:
        raise SystemExit(f"no {sensor} scene under {max_cloud}% cloud in {year}")
    return best[1:]


def to_grid(path, ds):
    """A domain raster resampled (nearest) onto the image grid."""
    out = np.zeros((ds.sizes["y"], ds.sizes["x"]), dtype=np.int64)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), out, dst_transform=ds.odc.geobox.transform, dst_crs=ds.odc.geobox.crs,
                  resampling=Resampling.nearest, dst_nodata=0)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--landsat", type=int, nargs="*", default=[], help="years to check with Landsat")
    p.add_argument("--sentinel", type=int, nargs="*", default=[], help="years to check with Sentinel-2 (2016 on)")
    p.add_argument("--months", type=int, nargs=2, default=(8, 9), help="first and last month searched")
    p.add_argument("--max-cloud", type=float, default=30.0, help="largest scene cloud cover searched, %%")
    p.add_argument("--ndsi", type=float, default=0.4)
    p.add_argument("--ndwi", type=float, default=0.3)
    p.add_argument("--cloud", type=float, default=0.25, help="green and SWIR1 reflectance above which a cell is cloud")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
    bbox = [lon_min, lat_min, lon_max, lat_max]
    out_dir = os.path.join(project, "observations", "imagery")
    os.makedirs(out_dir, exist_ok=True)
    glac_dir = os.path.join(project, "attributes", "glaciers")
    with Dataset(os.path.join(project, "settings", "SUMMA", "attributes_glac.nc")) as d:
        modelled = [int(v) for v in np.asarray(d["gridId"][:]).ravel() if v > 0]
    inside = lambda ds: to_grid(os.path.join(glac_dir, f"domain_{name}_hru_id.tif"), ds) > 0

    for sensor, years in (("landsat", a.landsat), ("sentinel", a.sentinel)):
        for year in years:
            item, g, r, n, s, cloud, ds = scene(sensor, year, bbox, c["utm_crs"], a.max_cloud, a.months, a.cloud, inside)
            date = item.datetime.strftime("%Y-%m-%d")
            basin = inside(ds)
            dtype = to_grid(os.path.join(glac_dir, f"domain_{name}_domain_type.tif"), ds)
            gid = to_grid(os.path.join(glac_dir, f"domain_{name}_rgi_id.tif"), ds)
            gid[~np.isin(gid, modelled)] = 0
            glacier, debris = (gid > 0) & (dtype >= 2) & (dtype <= 4), (gid > 0) & (dtype == 4)
            with np.errstate(invalid="ignore", divide="ignore"):
                ndsi, ndwi = (g - s) / (g + s), (g - n) / (g + n)
            water = (ndwi >= a.ndwi) & (n < 0.12) & ~cloud
            ice = (ndsi >= a.ndsi) & ~water & ~cloud & basin
            cls = np.zeros(g.shape, dtype=np.uint8)
            cls[glacier & ~ice & ~water & ~cloud] = 2
            cls[glacier & ice] = 1
            cls[~glacier & ice] = 3
            cls[water & basin] = 4
            cls[cloud & basin] = 5

            # one patch of image ice may hold several setup glaciers: they were joined
            patch, _ = ndimage.label(ice, structure=np.ones((3, 3)))
            km2 = 30.0 * 30.0 / 1e6
            rows = []
            for gl in [v for v in np.unique(gid) if v > 0]:
                cells = gid == gl
                patches = np.unique(patch[cells & ice])
                patches = patches[patches > 0]
                main = int(np.bincount(patch[cells & ice]).argmax()) if patches.size else 0
                rows.append({"glacier": f"RGI60-{gl // 100000:02d}.{gl % 100000:05d}", "patch": main,
                             "setup_glacier_km2": cells.sum() * km2, "setup_debris_km2": (cells & debris).sum() * km2,
                             "image_ice_in_km2": (cells & ice).sum() * km2,
                             "image_debris_or_rock_km2": (cells & (cls == 2)).sum() * km2,
                             "cloud_in_km2": (cells & cloud).sum() * km2,
                             "image_ice_beyond_km2": ((patch == main) & ~glacier).sum() * km2 if main else 0.0})
            tab = pd.DataFrame(rows)
            shared = tab[tab.patch > 0].groupby("patch").glacier.apply(list)
            tab["joined_with"] = [", ".join(x for x in shared.get(pt, []) if x != gl) if pt else ""
                                  for gl, pt in zip(tab.glacier, tab.patch)]
            stem = os.path.join(out_dir, f"imagery_{sensor}_{date}")
            tab.round(4).to_csv(stem + ".csv", index=False)
            prof = {"driver": "GTiff", "height": cls.shape[0], "width": cls.shape[1], "count": 1, "dtype": "uint8",
                    "crs": ds.odc.geobox.crs, "transform": ds.odc.geobox.transform, "compress": "deflate"}
            with rasterio.open(stem + ".tif", "w", **prof) as dst:
                dst.write(cls, 1)

            fig, ax = plt.subplots(1, 2, figsize=(12, 5.2), constrained_layout=True)
            rgb = np.clip(np.dstack([s, n, g]) / 0.5, 0, 1)
            rgb[~basin] *= 0.4
            ax[0].imshow(rgb)
            ax[0].contour(glacier, levels=[0.5], colors="magenta", linewidths=0.9)
            ax[0].contour(debris, levels=[0.5], colors="orange", linewidths=0.8)
            ax[0].set_title(f"{item.properties.get('platform', sensor)} {date}: setup glacier (magenta), debris (orange)")
            ax[1].imshow(cls, cmap=ListedColormap(COLOURS), vmin=-0.5, vmax=len(CLASSES) - 0.5, interpolation="nearest")
            ax[1].contour(debris, levels=[0.5], colors="orange", linewidths=0.8)
            ax[1].set_title("image classes, setup debris (orange)")
            for x in ax:
                x.set_xticks([]); x.set_yticks([])
            handles = [plt.Rectangle((0, 0), 1, 1, color=col) for col in COLOURS]
            ax[1].legend(handles, CLASSES, loc="lower right", fontsize=7, framealpha=0.9)
            fig.savefig(stem + ".png", dpi=150)
            plt.close(fig)

            tot = tab.sum(numeric_only=True)
            print(f"{name} {sensor} {date} ({item.id}), cloud over the basin {cloud[basin].mean():.1%}")
            print(f"  setup glacier {tot.setup_glacier_km2:.2f} km2, debris {tot.setup_debris_km2:.2f}; image ice in it "
                  f"{tot.image_ice_in_km2:.2f}, debris or rock {tot.image_debris_or_rock_km2:.2f}; ice beyond it in the "
                  f"basin {(cls == 3).sum() * km2:.2f}")
            print(tab.round(3).to_string(index=False))
            print(f"  wrote {stem}.csv/.tif/.png")


if __name__ == "__main__":
    main()
