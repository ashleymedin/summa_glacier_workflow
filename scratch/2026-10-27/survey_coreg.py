"""Each survey DEM against the glacier's Millan reference survey on stable ground (off the earliest outline,
buffered 200 m, slope under 20 degrees, |dz - median| < 30 m) at 50 m: median, a plane plus elevation fit and
its residual, and how much of the survey's own outline it covers."""
import numpy as np, geopandas as gpd, rasterio
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp').to_crs(32606)
sets = {'Gulkana Glacier': ('Deltas_20160830', ['Deltas_19930711', 'Deltas_20050808', 'Deltas_20070811']),
        'Wolverine Glacier': ('EasternKenai_20150813', ['EasternKenai_19950927', 'EasternKenai_20060808', 'EasternKenai_20080917'])}
def read(n, tr, sh):
    with rasterio.open(f'{WF}/GlacierDEM/{n}_DEM/{n}_DEM.tif') as s:
        f = max(1, int(2.0 / abs(s.res[0])))
        z = s.read(1, masked=True, out_shape=(s.height // f, s.width // f), resampling=Resampling.average).astype(float).filled(np.nan)
        t = s.transform * s.transform.scale(s.width / z.shape[1], s.height / z.shape[0])
        out = np.full(sh, np.nan)
        reproject(z, out, src_transform=t, src_crs=s.crs, src_nodata=np.nan, dst_transform=tr, dst_crs=32606, dst_nodata=np.nan, resampling=Resampling.average)
    return out
for gname, (ref, others) in sets.items():
    g = u[u.Glacier == gname]
    x0, y0, x1, y1 = g.total_bounds; pad = 3000
    tr = from_origin(x0 - pad, y1 + pad, 50, 50); sh = (int((y1 - y0 + 2 * pad) / 50), int((x1 - x0 + 2 * pad) / 50))
    R = read(ref, tr, sh)
    off = ~geometry_mask(list(g[g.Year == g.Year.min()].geometry.buffer(200)), sh, tr)
    gy, gx = np.gradient(R, 50); flat = np.degrees(np.arctan(np.hypot(gx, gy))) < 20
    r, c = np.indices(sh); X, Y = tr * (c + 0.5, r + 0.5)
    print(f'\n{gname}: against {ref}')
    for n in others:
        Z = read(n, tr, sh); d = Z - R
        st = ~off & flat & np.isfinite(d); st &= np.abs(d - np.nanmedian(d[st])) < 30
        M = np.c_[np.ones(st.sum()), (X[st] - X.mean()) / 1e3, (Y[st] - Y.mean()) / 1e3, (R[st] - 1000) / 100]
        k, *_ = np.linalg.lstsq(M, d[st], rcond=None); res = d[st] - M @ k
        nm = lambda v: 1.4826 * np.median(np.abs(v - np.median(v)))
        yr = int(n[-8:-4]); own = u[(u.Glacier == gname) & (u.Year == yr)]
        cov = (np.isfinite(Z) & ~geometry_mask(list(own.geometry), sh, tr)).sum() / max((~geometry_mask(list(own.geometry), sh, tr)).sum(), 1) if len(own) else np.nan
        print(f'  {n[-8:]}: ground n {st.sum()}, median {np.median(d[st]):+.1f} NMAD {nm(d[st]):.1f}; plane+elev {k[1]:+.2f} m/km E {k[2]:+.2f} m/km N '
              f'{k[3]:+.2f} m/100 m, residual NMAD {nm(res):.1f}; covers {cov*100:.0f}% of its outline' + ('' if len(own) else ' (no outline that year)'))
