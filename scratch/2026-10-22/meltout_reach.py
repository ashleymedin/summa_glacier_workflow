"""Melt-out bed: carry distance (reach) against Gulkana 2024 radar, from glacier_rasters.py --output-dir runs in r_<glacier>/ (scratchpad) before reach was added."""
import numpy as np, rasterio, pandas as pd, geopandas as gpd, sys
from rasterio.features import geometry_mask
from scipy.ndimage import distance_transform_edt
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
from glacier_rasters import harmonic_fill
SP = '/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/4ac083c7-0f61-4381-86ee-764f921e607f/scratchpad'
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
r = pd.read_csv(f'{WF}/GlacierDEM/GulkanaRadarDepth/Gulkana_2024_radar_interpretations.csv').dropna(subset=['bed_elev'])
for G, d0, d1 in (('Gulkana', '2007/08/11', '2021/09/19'), ('Wolverine', '2006/08/08', '2020/10/19')):
    with rasterio.open(f'{SP}/r_{G.lower()}/domain_{G}_bedrock_elv.tif') as s:
        new = s.read(1).astype(float); T, crs, sh = s.transform, s.crs, s.shape
    old = rasterio.open(f'{WF}/data/domain_{G}/attributes/elevation/dem/domain_{G}_bedrock_elv.tif').read(1).astype(float)
    srf = rasterio.open(f'{SP}/r_{G.lower()}/domain_{G}_glacier_elv.tif').read(1).astype(float)
    rid = rasterio.open(f'{SP}/r_{G.lower()}/domain_{G}_rgi_id.tif').read(1); glacier = rid > 0
    g = u[u.Glacier == f'{G} Glacier'].to_crs(crs)
    a, b = g[g.Date == d0].union_all(), g[g.Date == d1].union_all()
    lost = glacier & geometry_mask([a.difference(b)], sh, T, invert=True) & ~geometry_mask([b], sh, T, invert=True)
    known = lost & (abs(new - old) > 0)  # cells the strips set (approx)
    dy = abs(T.e) * 111320; dx = T.a * 111320 * np.cos(np.radians(T.f + T.e * sh[0] / 2))
    dist = distance_transform_edt(~known, sampling=(dy, dx))
    H0 = (srf - old)[glacier & ~lost].sum()
    for L in (0, 250, 500, 750, 1000, 1e9):
        region = glacier & (dist <= L)
        ch = harmonic_fill(np.where(known, new - old, 0.0), known, region)
        bed = np.where(glacier, np.minimum(old + ch, srf), old)
        msg = f'{G:9s} L {L:6.0f}: remaining-ice volume {(srf - bed)[glacier & ~lost].sum() / H0:.3f} of Millan'
        if G == 'Gulkana':
            p = gpd.GeoSeries(gpd.points_from_xy(r.utm6n_x, r.utm6n_y), crs=32606).to_crs(crs)
            rows, cols = rasterio.transform.rowcol(T, p.x, p.y)
            e = bed[rows, cols] - (r.bed_elev.values + 15.9); e0 = old[rows, cols] - (r.bed_elev.values + 15.9)
            for lo, hi in ((1400, 1500), (1500, 1600), (1600, 1800)):
                k = ((r.srf_elev >= lo) & (r.srf_elev < hi)).values
                msg += f' | {lo}: {np.median(e[k]):+5.1f} (MAD {np.median(abs(e[k] - np.median(e[k]))):4.1f})'
            k = (srf < 1400) & glacier & ~lost
            msg += f' | tongue<1400 H {np.median((srf - bed)[k]):.0f} m'
        print(msg)
