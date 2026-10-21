"""Slope of bare rock against vegetation around Gulkana, from Sentinel-2 2021-08-02 and Copernicus GLO-30."""
import os, sys
sys.path.insert(0, "/Users/amedin/Research/SummaSundials/summa_glacier_workflow")
os.chdir("/Users/amedin/Research/SummaSundials/summa_glacier_workflow")
import numpy as np, pandas as pd, rasterio, planetary_computer, pystac_client
from odc.stac import load
from rasterio.warp import reproject, Resampling
from scipy import ndimage
from domain_config import load_config
from check_glacier_imagery import STAC, to_grid

c = load_config("domains/gulkana.yaml")
project, name = c["project_dir"], c["domain"]
lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
bbox = [lon_min, lat_min, lon_max, lat_max]
cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
item = [i for i in cat.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime="2021-08-02/2021-08-02").items()]
item = sorted(item, key=lambda i: i.properties["eo:cloud_cover"])[0]
ds = load([item], bands=["B03", "B04", "B08", "B11", "SCL"], crs=c["utm_crs"], resolution=30, bbox=bbox,
          resampling={"*": "bilinear", "SCL": "nearest"})
off = -0.1 if float(item.properties.get("s2:processing_baseline", "0")) >= 4.0 else 0.0
g, r, n, s = (np.asarray(ds[b].isel(time=0), float) * 1e-4 + off for b in ["B03", "B04", "B08", "B11"])
scl = np.asarray(ds["SCL"].isel(time=0))
dem_item = next(cat.search(collections=["cop-dem-glo-30"], bbox=bbox).items())
dems = [next(cat.search(collections=["cop-dem-glo-30"], bbox=bbox).items())]
dem = load(list(cat.search(collections=["cop-dem-glo-30"], bbox=bbox).items()), bands=["data"], crs=c["utm_crs"],
           resolution=30, bbox=bbox, resampling="bilinear")
z = np.asarray(dem["data"].isel(time=0), float)
assert z.shape == g.shape


def slope_deg(z, d):
    gy, gx = np.gradient(z, d)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


s30 = slope_deg(z, 30.0)
# the same ground on a 50 m grid, as the model sees it
tr = ds.odc.geobox.transform
ny50, nx50 = int(z.shape[0] * 30 / 50), int(z.shape[1] * 30 / 50)
from affine import Affine
tr50 = Affine(50.0, 0, tr.c, 0, -50.0, tr.f)
z50 = np.zeros((ny50, nx50))
reproject(z, z50, src_transform=tr, src_crs=ds.odc.geobox.crs, dst_transform=tr50, dst_crs=ds.odc.geobox.crs,
          resampling=Resampling.average)
sl50 = slope_deg(z50, 50.0)
s50 = np.zeros_like(z)
reproject(sl50, s50, src_transform=tr50, src_crs=ds.odc.geobox.crs, dst_transform=tr, dst_crs=ds.odc.geobox.crs,
          resampling=Resampling.nearest)

glac_dir = os.path.join(project, "attributes", "glaciers")
basin = to_grid(os.path.join(glac_dir, f"domain_{name}_hru_id.tif"), ds) > 0
dtype = to_grid(os.path.join(glac_dir, f"domain_{name}_domain_type.tif"), ds)
glacier = (dtype >= 2) & (dtype <= 4)
with np.errstate(invalid="ignore", divide="ignore"):
    ndsi, ndvi, ndwi = (g - s) / (g + s), (n - r) / (n + r), (g - n) / (g + n)
ice = ndsi >= 0.4
water = (ndwi >= 0.3) & (n < 0.12)
cloud = (g > 0.25) & (s > 0.25)
shadow = (n < 0.06) | (scl == 2) | (scl == 3)
near = (ndimage.distance_transform_edt(~glacier) * 30 <= 500) & ~glacier & ~ice & ~water & ~cloud & ~shadow & basin
bare = near & (ndvi < 0.15)
veg = near & (ndvi >= 0.3)
print(item.id, "cells near the glacier", near.sum(), "bare", bare.sum(), "vegetated", veg.sum(),
      "shadow excluded", (shadow & basin & ~glacier).sum())
for lab, sl in (("30 m", s30), ("50 m", s50)):
    bins = np.arange(0, 65, 5)
    hb, _ = np.histogram(sl[bare], bins); hv, _ = np.histogram(sl[veg], bins); hn, _ = np.histogram(sl[near], bins)
    t = pd.DataFrame({"slope": [f"{a}-{a+5}" for a in bins[:-1]], "near": hn, "bare": hb, "veg": hv,
                      "bare_frac": np.round(hb / np.maximum(hn, 1), 2)})
    print(f"\n{lab} slope, ground within 500 m of the glacier")
    print(t.to_string(index=False))
    print("bare slope p10/25/50/75/90", np.percentile(sl[bare], [10, 25, 50, 75, 90]).round(1))
    print("veg  slope p10/25/50/75/90", np.percentile(sl[veg], [10, 25, 50, 75, 90]).round(1))
np.savez_compressed(os.path.join(os.path.dirname(__file__), "wall_slope.npz"), s30=s30, s50=s50, ndvi=ndvi, near=near,
                    bare=bare, veg=veg, glacier=glacier, z=z, ice=ice, shadow=shadow, basin=basin,
                    rgb=np.clip(np.dstack([s, n, g]) / 0.5, 0, 1))
