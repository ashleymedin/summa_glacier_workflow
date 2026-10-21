"""Gulkana 2024 radar against the setup's bed, Millan and Farinotti, and the margin thickness gradient."""
import glob, os
import numpy as np, pandas as pd, geopandas as gpd, rasterio

WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
H = os.path.expanduser('~/Research/USask/Thickness_data')
r = pd.read_csv(f'{WF}/GlacierDEM/GulkanaRadarDepth/Gulkana_2024_radar_interpretations.csv').dropna(subset=['bed_elev'])
pts = gpd.GeoSeries(gpd.points_from_xy(r.utm6n_x, r.utm6n_y), crs=32606)
print(f'{len(r)} points with a bed, thickness {r.srf_bed_thick.min():.0f}-{r.srf_bed_thick.max():.0f} m')

def sample(path, x, y, crs_pts=32606):
    with rasterio.open(path) as s:
        xx, yy = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=crs_pts).to_crs(s.crs).pipe(lambda g: (g.x.values, g.y.values))
        v = np.array([a[0] for a in s.sample(zip(xx, yy))], float)
        inb = (xx > s.bounds.left) & (xx < s.bounds.right) & (yy > s.bounds.bottom) & (yy < s.bounds.top)
        if s.nodata is not None:
            v[v == s.nodata] = np.nan
        v[~inb] = np.nan
    return v

D = f'{WF}/data/domain_Gulkana/attributes'
r['survey2007'] = sample(f'{WF}/GlacierDEM/Deltas_20070811_DEM/Deltas_20070811_DEM.tif', r.utm6n_x, r.utm6n_y)
r['model_bed'] = sample(f'{D}/elevation/dem/domain_Gulkana_bedrock_elv.tif', r.utm6n_x, r.utm6n_y)
r['model_srf'] = sample(f'{D}/elevation/dem/domain_Gulkana_glacier_elv.tif', r.utm6n_x, r.utm6n_y)
r['dtype'] = sample(f'{D}/glaciers/domain_Gulkana_domain_type.tif', r.utm6n_x, r.utm6n_y)
r['farinotti'] = sample(f'{H}/Farinotti2019/RGI60-01/RGI60-01.00570_thickness.tif', r.utm6n_x, r.utm6n_y)
m = np.full(len(r), np.nan)
for p in glob.glob(f'{H}/RGI-1/THICKNESS_RGI-1.*.tif'):
    v = sample(p, r.utm6n_x, r.utm6n_y); ok = np.isfinite(v) & (v > 0); m[ok] = v[ok]
r['millan'] = m

d = r.srf_elev - r.survey2007
print(f'radar 2024 surface minus 2007 survey DEM: median {d.median():.1f} m (above 1900 m: {d[r.srf_elev > 1900].median():.1f})')
off = 15.9  # survey DEM to domain DEM, glacier_rasters.py
bed = r.bed_elev + off
e = r.model_bed - bed
print(f'model bed minus radar bed (+{off} m datum): median {e.median():.1f} m, MAD {np.median(abs(e - e.median())):.1f} m')
for lo, hi in ((1200, 1500), (1500, 1800), (1800, 2200)):
    s = (r.srf_elev >= lo) & (r.srf_elev < hi)
    print(f'  surface {lo}-{hi} m: n {s.sum():5d}, model bed - radar bed median {e[s].median():6.1f} m')
for c in ('millan', 'farinotti'):
    x = r[c] - r.srf_bed_thick
    print(f'{c:9s} - radar thickness: bias {x.mean():6.1f} m, RMSE {np.sqrt((x**2).mean()):5.1f} m, n {x.notna().sum()}')

usgs = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
o = usgs[(usgs.Glacier == 'Gulkana Glacier') & (usgs.Year == 2021)].to_crs(32606).geometry.union_all()
r['dist'] = pts.distance(o.boundary).values
abl = r.dtype.isin([3, 4])
print(f'ablation-zone points {abl.sum()}, within 300 m of the 2021 outline {(abl & (r.dist < 300)).sum()}')
for lo, hi in ((0, 50), (50, 100), (100, 150), (150, 200), (200, 300), (300, 500)):
    s = abl & (r.dist >= lo) & (r.dist < hi)
    if s.sum():
        q = r.srf_bed_thick[s] / r.dist[s]
        print(f'  {lo:3d}-{hi:3d} m: n {s.sum():5d}  thickness median {r.srf_bed_thick[s].median():5.0f} m  '
              f'h/d median {q.median():.2f} (10-90% {q.quantile(.1):.2f}-{q.quantile(.9):.2f})')
s = abl & (r.dist < 200)
print(f'h = s d through zero within 200 m: s = {(r.dist[s]*r.srf_bed_thick[s]).sum()/(r.dist[s]**2).sum():.2f}')
