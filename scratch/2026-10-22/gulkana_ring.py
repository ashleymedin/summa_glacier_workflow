"""Gulkana: is the ice USGS dropped between outlines melted out, or stagnant debris-covered ice? Hugonnet 2000-2019 dh/dt,
2024 radar traces, and the USGS DEMs over each strip lost between successive outlines."""
import glob
import numpy as np, pandas as pd, geopandas as gpd, rasterio, rasterio.mask
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
g = u[u.Glacier == 'Gulkana Glacier'].to_crs(32606).set_index('Year').geometry
strips = {f'{a}-{b}': g[a].difference(g[b]) for a, b in ((1993, 2005), (2005, 2014), (2014, 2016), (2016, 2021))}
strips['in 2021, <1400 m'] = None
inside21 = g[2021]


def zonal(path, geom, band=1):
    with rasterio.open(path) as s:
        gg = gpd.GeoSeries([geom], crs=32606).to_crs(s.crs)
        a, _ = rasterio.mask.mask(s, gg, crop=True, filled=True, nodata=np.nan, indexes=band)
    a = a.astype(float); return a[np.isfinite(a)]


hug = glob.glob(f'{WF}/HugonnetData/01_02_rgi60_2000-01-01_2020-01-01/dhdt/N63W146*dhdt.tif')[0]
dem = {y: f'{WF}/GlacierDEM/Deltas_{d}_DEM/Deltas_{d}_DEM.tif' for y, d in ((1993, '19930711'), (2005, '20050808'), (2007, '20070811'))}
with rasterio.open(dem[2007]) as s:
    z07 = s.read(1, masked=True)
    tongue = gpd.GeoSeries([inside21], crs=32606).to_crs(s.crs)
r = pd.read_csv(f'{WF}/GlacierDEM/GulkanaRadarDepth/Gulkana_2024_radar_interpretations.csv')
pts = gpd.GeoSeries(gpd.points_from_xy(r.utm6n_x, r.utm6n_y), crs=32606)

# low tongue still inside the 2021 outline, for comparison
lowbox = None
with rasterio.open(dem[2007]) as s:
    z, t = rasterio.mask.mask(s, tongue, crop=True, filled=True, nodata=np.nan)
from shapely.geometry import shape
from rasterio import features
with rasterio.open(dem[2007]) as s:
    zz = s.read(1).astype(float); zz[zz == s.nodata] = np.nan
    low = [shape(p) for p, v in features.shapes((zz < 1400 + 15.9).astype('uint8'), transform=s.transform) if v == 1]
    low = gpd.GeoSeries(low, crs=s.crs).to_crs(32606).union_all()
strips['in 2021, <1400 m'] = inside21.intersection(low)

print('strip            km2   Hugonnet dh/dt 2000-19 (m/yr) median [10-90%]   dh 2005->07 DEM (m/yr)   radar traces / with bed / median ice (m)')
for k, geom in strips.items():
    h = zonal(hug, geom)
    d5, d7 = zonal(dem[2005], geom), zonal(dem[2007], geom)
    n = min(len(d5), len(d7))
    with rasterio.open(dem[2005]) as a, rasterio.open(dem[2007]) as b:
        gg = gpd.GeoSeries([geom], crs=32606).to_crs(a.crs)
        A, _ = rasterio.mask.mask(a, gg, crop=True, filled=True, nodata=np.nan); B, _ = rasterio.mask.mask(b, gg, crop=True, filled=True, nodata=np.nan)
        dd = (B[0].astype(float) - A[0].astype(float))[np.isfinite(A[0]) & np.isfinite(B[0])] / 2 if A.shape == B.shape else np.array([np.nan])
    inr = pts.within(geom).values
    hb = r.srf_bed_thick[inr & r.bed_elev.notna()]
    print(f'{k:15s} {geom.area/1e6:5.2f}   {np.median(h):6.2f} [{np.percentile(h,10):5.2f} {np.percentile(h,90):5.2f}]'
          f'                      {np.nanmedian(dd) if dd.size else np.nan:6.2f}               {inr.sum():5d} / {len(hb):4d} / {hb.median() if len(hb) else np.nan:5.0f}')
