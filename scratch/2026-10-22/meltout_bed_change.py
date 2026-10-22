"""Melt-out bed: bed change and thickness by band, and against Gulkana 2024 radar."""
import numpy as np, rasterio, pandas as pd, geopandas as gpd, sys
SP = '/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/4ac083c7-0f61-4381-86ee-764f921e607f/scratchpad'
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
for g, G in (('gulkana', 'Gulkana'), ('wolverine', 'Wolverine')):
    rd = lambda p: rasterio.open(p).read(1).astype(float)
    old = rd(f'{WF}/data/domain_{G}/attributes/elevation/dem/domain_{G}_bedrock_elv.tif')
    new = rd(f'{SP}/r_{g}/domain_{G}_bedrock_elv.tif')
    srf = rd(f'{SP}/r_{g}/domain_{G}_glacier_elv.tif')
    srf0 = rd(f'{WF}/data/domain_{G}/attributes/elevation/dem/domain_{G}_glacier_elv.tif')
    rid = rd(f'{SP}/r_{g}/domain_{G}_rgi_id.tif'); main = rid == np.bincount(rid[rid > 0].astype(int)).argmax()
    print(G, 'surface identical:', np.array_equal(srf, srf0), ' main glacier cells', main.sum())
    d = new - old; H0, H1 = srf - old, srf - new
    print(' band   n  bed change med  p10   p90   H old  H new')
    for z in range(int(np.nanmin(srf[main]) // 100 * 100), int(np.nanmax(srf[main])) + 1, 100):
        k = main & (srf >= z) & (srf < z + 100)
        if k.sum(): print(f' {z:5d} {k.sum():4d} {np.median(d[k]):8.1f} {np.percentile(d[k],10):6.1f} {np.percentile(d[k],90):6.1f} {np.median(H0[k]):6.0f} {np.median(H1[k]):6.0f}')
    print(f' volume old {H0[main].sum():.0f} new {H1[main].sum():.0f} (cell-m); zero-ice cells old {(H0[main]<=0).sum()} new {(H1[main]<=0).sum()}')
    print(f' other glaciers changed >1 m: {((rid > 0) & ~main & (abs(d) > 1)).sum()}')
r = pd.read_csv(f'{WF}/GlacierDEM/GulkanaRadarDepth/Gulkana_2024_radar_interpretations.csv').dropna(subset=['bed_elev'])
def sample(path):
    with rasterio.open(path) as s:
        p = gpd.GeoSeries(gpd.points_from_xy(r.utm6n_x, r.utm6n_y), crs=32606).to_crs(s.crs)
        return np.array([a[0] for a in s.sample(zip(p.x, p.y))], float)
ob = sample(f'{WF}/data/domain_Gulkana/attributes/elevation/dem/domain_Gulkana_bedrock_elv.tif')
nb = sample(f'{SP}/r_gulkana/domain_Gulkana_bedrock_elv.tif')
rb = r.bed_elev + 15.9
for lo, hi in ((1400, 1500), (1500, 1600), (1600, 1800), (1800, 2300)):
    s = (r.srf_elev >= lo) & (r.srf_elev < hi)
    print(f'radar {lo}-{hi}: n {s.sum():5d} model-radar bed old {np.median((ob-rb)[s]):6.1f} new {np.median((nb-rb)[s]):6.1f}  change {np.median((nb-ob)[s]):5.1f} max {np.max((nb-ob)[s]):5.1f}')
