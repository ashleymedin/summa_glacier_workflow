"""Gulkana's levelled surveys on its 2007 ice by 100 m band, each minus the 2007 survey, against Hugonnet's
2000-2020 dh/dt times the years between; and the elevation range of the ground each plane was fitted on."""
import sys, glob
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
import numpy as np, geopandas as gpd, rasterio
from rasterio.features import geometry_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import glacier_rasters as G
from domain_config import load_config
c = load_config(f'{WF}/domains/gulkana.yaml')
src = rasterio.open(f"{c['project_dir']}/attributes/elevation/dem/domain_{c['domain']}_elv.tif")
utm = rasterio.crs.CRS.from_string(c['utm_crs'])
tr, w, h = calculate_default_transform(src.crs, utm, src.width, src.height, *src.bounds)
grid = type('Grid', (), {'transform': tr, 'crs': utm}); dem = np.full((h, w), np.nan)
reproject(src.read(1).astype(float), dem, src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata, dst_transform=tr, dst_crs=utm, dst_nodata=np.nan, resampling=Resampling.bilinear)
u = gpd.read_file(c['data']['usgs_outlines']).to_crs(c['utm_crs']); u = u[u.Glacier == 'Gulkana Glacier']
ever = gpd.GeoDataFrame(geometry=[u[u.Year.isin([1993, 2005, 2007, 2016])].union_all()], crs=u.crs)
P = lambda n: f'{WF}/GlacierDEM/{n}_DEM/{n}_DEM.tif'
_, _, anchor = G.survey_on_grid(dem, grid, ever, P('Deltas_20160830'), offset=-16.1)
Z = {}
for n in ('Deltas_19930711', 'Deltas_20050808', 'Deltas_20070811'):
    z, cov, gr = G.survey_on_grid(dem, grid, ever, P(n), anchor=anchor)
    Z[n[-8:-4]] = np.where(cov >= 0.5, z, np.nan)
hug = np.full(dem.shape, np.nan)
for f in sorted(glob.glob(f'{WF}/HugonnetData/01_02_rgi60_2000-01-01_2020-01-01/dhdt/N63W14[56]_*.tif')):
    with rasterio.open(f) as s:
        a = np.full(dem.shape, np.nan)
        reproject(rasterio.band(s, 1), a, src_transform=s.transform, src_crs=s.crs, src_nodata=s.nodata, dst_transform=tr, dst_crs=utm, dst_nodata=np.nan, resampling=Resampling.average)
        hug = np.where(np.isfinite(a), a, hug)
on = geometry_mask(list(u[u.Year == 2007].geometry), dem.shape, tr, invert=True)
gy, gx = np.gradient(anchor, 50.5, 50.5)
gnd = np.isfinite(anchor) & (np.degrees(np.arctan(np.hypot(gx, gy))) < 20)
print(f'ground the planes were fitted on (USGS heights): {np.nanpercentile(anchor[gnd] + 16.1, [5, 50, 95]).round(0)}; glacier {np.nanpercentile(Z["2007"][on] + 16.1, [5, 50, 95]).round(0)}')
B = np.floor((Z['2007'] + 16.1) / 100) * 100
print(' band   2005-2007  Hugonnet x 2.0   1993-2007  Hugonnet x 14.1')
for b in np.unique(B[on & np.isfinite(B)]):
    k = on & (B == b)
    if k.sum() < 30: continue
    print(f' {b:5.0f} {np.nanmedian((Z["2005"] - Z["2007"])[k]):+10.1f} {-2.0 * np.nanmedian(hug[k]):+14.1f} {np.nanmedian((Z["1993"] - Z["2007"])[k]):+11.1f} {-14.1 * np.nanmedian(hug[k]):+15.1f}')
