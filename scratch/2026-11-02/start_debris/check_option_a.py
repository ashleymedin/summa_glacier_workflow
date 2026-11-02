"""Option A for the starting debris: mapped debris less cells clean in the 2004-05 Landsat, plus bare ablation cells; usage: check_option_a.py <Domain> <scene dates...>"""
import sys
import numpy as np, rasterio
from rasterio.warp import reproject, Resampling
from scipy import ndimage
name, dates = sys.argv[1], sys.argv[2:]
root = f"/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_{name}"
g = f"{root}/attributes/glaciers/domain_{name}_"
src = rasterio.open(g + "domain_type.tif"); dtype = src.read(1); rgi = rasterio.open(g + "rgi_id.tif").read(1)
thick = rasterio.open(g + "debris_thickness.tif").read(1)
lat = src.bounds.top - (np.arange(dtype.shape[0]) + 0.5) * src.res[1]
km2 = (np.cos(np.radians(lat))[:, None] * 111.32e3 * src.res[0]) * (110.57e3 * src.res[1]) / 1e6 * np.ones(dtype.shape)
ice_sum, clear_sum = np.zeros(dtype.shape), np.zeros(dtype.shape)
for d in dates:
    s = rasterio.open(f"{root}/observations/imagery/imagery_landsat_{d}.tif"); cls = s.read(1)
    for arr, val in ((ice_sum, np.isin(cls, (1, 3))), (clear_sum, ~np.isin(cls, (4, 5)))):
        out = np.zeros(dtype.shape, dtype=np.float32)
        reproject(val.astype(np.float32), out, src_transform=s.transform, src_crs=s.crs, dst_transform=src.transform,
                  dst_crs=src.crs, resampling=Resampling.average)
        arr += out
frac = np.where(clear_sum > 0.2, ice_sum / np.maximum(clear_sum, 1e-9), np.nan)
main = np.bincount(rgi[dtype == 4]).argmax(); own = rgi == main
abl = own & np.isin(dtype, (3, 4)); interior = ndimage.binary_erosion(own)
deb = own & (dtype == 4)
clean = deb & (frac >= 0.5); bare = abl & (dtype == 3) & (frac < 0.5) & interior
print(f"{name} {dates}: glacier {km2[own].sum():.2f} km2, ablation {km2[abl].sum():.2f}, debris now {km2[deb].sum():.3f} km2 ({deb.sum()} cells)")
print(f"  mapped debris clean in the scenes: {km2[clean].sum():.3f} km2 ({clean.sum()}), mean thickness {thick[clean].mean() if clean.any() else 0:.3f} m vs kept {thick[deb & ~clean].mean():.3f} m")
print(f"  clean ablation cells bare in the scenes (interior): {km2[bare].sum():.3f} km2 ({bare.sum()}); no clear pixels on debris: {np.isnan(frac[deb]).sum()}")
new = (deb & ~clean) | bare
print(f"  option A debris {km2[new].sum():.3f} km2 ({new.sum()}), {km2[new].sum() / km2[own].sum() * 100:.1f}% of the glacier")
for lo in range(0, 101, 20):
    m = deb & (frac * 100 >= lo) & (frac * 100 < lo + 20 if lo < 100 else True)
    print(f"   ice fraction {lo:3d}-{lo + 20:3d}%: {m.sum()} debris cells")
