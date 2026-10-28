"""Gulkana's four small glaciers (RGI 01.00332, 00333, 00334, 22903) against ArcticDEM strips, 2010 on: has their ice melted out?
Per year the strip with most cover of the glaciers' cells, 8 m, levelled to the DEM on the ice-free ground and averaged onto the
DEM grid; per glacier the lowering from the start surface, the thickness left over the built bed, and the stable (not lowering) cells.
Writes small_glaciers_strips.npz (year, strip heights on the DEM grid) and prints the table."""
import os, sys
import numpy as np, rasterio, geopandas as gpd, pystac_client
from rasterio.warp import reproject, Resampling, transform_bounds
from pyproj import Transformer
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
from acquire_arcticdem import read_clip, STAC, COLLECTION
from shapely.geometry import box
D = f'{WF}/data/domain_Gulkana/attributes'
IDS = {100332: '00332', 100333: '00333', 100334: '00334', 122903: '22903'}

with rasterio.open(f'{D}/glaciers/domain_Gulkana_rgi_id.tif') as r:
    rid, T, CRS = r.read(1), r.transform, r.crs
with rasterio.open(f'{D}/elevation/dem/domain_Gulkana_elv.tif') as r:
    dem = r.read(1).astype(float)
with rasterio.open(f'{D}/elevation/dem/domain_Gulkana_glacier_elv.tif') as r:
    surf = r.read(1).astype(float)
with rasterio.open(f'{D}/elevation/dem/domain_Gulkana_bedrock_elv.tif') as r:
    bed = r.read(1).astype(float)
small = np.isin(rid, list(IDS))
rows, cols = np.nonzero(small)
w, n = T * (cols.min(), rows.max() + 1); e, s = T * (cols.max() + 1, rows.min())   # lon/lat bounds of the four
pad = 0.01
bbox4326 = (w - pad, n - pad, e + pad, s + pad)
bounds3413 = tuple(8 * round(b / 8) for b in transform_bounds(CRS, 3413, *bbox4326))
print('bbox', [round(b, 4) for b in bbox4326], 'cells', int(small.sum()))
items = pystac_client.Client.open(STAC).search(collections=[COLLECTION], bbox=list(bbox4326), datetime='2010-01-01T00:00:00Z/..').item_collection()
items = [i for i in items if 8 <= i.datetime.month <= 9]
print(len(items), 'strips Aug-Sep')
best = {}
win = (slice(rows.min() - 15, rows.max() + 16), slice(cols.min() - 15, cols.max() + 16))
ground = (rid == 0)
for it in sorted(items, key=lambda i: i.datetime):
    z, t, crs = read_clip(it.assets['dem'].href, bounds3413, 4)
    bits, _, _ = read_clip(it.assets['mask'].href, bounds3413, 4, Resampling.nearest)
    z[bits != 0] = np.nan
    out = np.full(dem.shape, np.nan)
    reproject(z, out, src_transform=t, src_crs=crs, src_nodata=np.nan, dst_transform=T, dst_crs=CRS, dst_nodata=np.nan,
              resampling=Resampling.average)
    cover = np.isfinite(out[small]).mean()
    if cover < 0.5:
        continue
    off = np.nanmedian((dem - out)[ground & np.isfinite(out)][::7])
    y = it.datetime.year
    if y not in best or cover > best[y][0]:
        best[y] = (cover, out + off, off, it.datetime.date())
    print(it.datetime.date(), f'cover {cover:.0%} offset {off:+.1f}', flush=True)
years = sorted(best)
Z = np.array([best[y][1] for y in years])
np.savez_compressed(f'{WF}/scratch/2026-10-28/small_glaciers_strips.npz', years=years, z=Z, rid=rid, surf=surf, bed=bed)
print('\nlowering of the strip below the start surface (m), and ice left over the built bed (m), median over cells')
print('glacier  cells  ' + '  '.join(f'{y}' for y in years))
for k, nm in IDS.items():
    m = rid == k
    low = [np.nanmedian((Z[i] - surf)[m]) for i in range(len(years))]
    thick = [np.nanmedian((Z[i] - bed)[m]) for i in range(len(years))]
    print(f'{nm}  {int(m.sum()):4d}  low ' + ' '.join(f'{v:6.1f}' for v in low))
    print(f'{"":13s} ice ' + ' '.join(f'{v:6.1f}' for v in thick))
    last = Z[-1]
    gone = np.nanmean(((last - bed) < 3)[m & np.isfinite(last)])
    # stable cells: slope of strip height over the last years that have the cell
    sl = np.full(m.sum(), np.nan)
    zz = Z[:, m]
    for j in range(zz.shape[1]):
        ok = np.isfinite(zz[:, j]) & (np.array(years) >= 2014)
        if ok.sum() >= 3:
            sl[j] = np.polyfit(np.array(years)[ok], zz[ok, j], 1)[0]
    print(f'{"":13s} strip within 3 m of the bed on {gone:.0%} of cells; median slope {np.nanmedian(sl):+.2f} m/yr; stable (|slope|<0.3) {np.nanmean(np.abs(sl) < 0.3):.0%}')
