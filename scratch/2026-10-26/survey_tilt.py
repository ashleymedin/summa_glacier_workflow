"""Pairwise difference of the USGS survey DEMs on stable ground (off the earliest outline, buffered 200 m, slope
under 20 degrees) at 50 m, with a plane and an elevation term fitted, and the same difference over the glacier by band."""
import sys
import numpy as np, geopandas as gpd, rasterio
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp').to_crs(32606)
pairs = {'Gulkana Glacier': ('Deltas_20070811', 'Deltas_20160830', 'Deltas_20050808'),
         'Wolverine Glacier': ('EasternKenai_20060808', 'EasternKenai_20150813', 'EasternKenai_20080917')}
for gname, names in pairs.items():
    g = u[u.Glacier == gname]
    x0, y0, x1, y1 = g.total_bounds; pad = 3000
    tr = from_origin(x0 - pad, y1 + pad, 50, 50); sh = (int((y1 - y0 + 2 * pad) / 50), int((x1 - x0 + 2 * pad) / 50))
    Z = {}
    for n in names:
        with rasterio.open(f'{WF}/GlacierDEM/{n}_DEM/{n}_DEM.tif') as s:
            f = max(1, int(2.0 / abs(s.res[0])))
            z = s.read(1, masked=True, out_shape=(s.height // f, s.width // f), resampling=Resampling.average).astype(float).filled(np.nan)
            t = s.transform * s.transform.scale(s.width / z.shape[1], s.height / z.shape[0])
            out = np.full(sh, np.nan)
            reproject(z, out, src_transform=t, src_crs=s.crs, src_nodata=np.nan, dst_transform=tr, dst_crs=32606, dst_nodata=np.nan, resampling=Resampling.average)
            Z[n] = out
    ice = ~geometry_mask(list(g[g.Year == g.Year.min()].geometry.buffer(200)), sh, tr)
    r, c = np.indices(sh); X, Y = tr * (c + 0.5, r + 0.5)
    for a, b in ((names[0], names[1]), (names[0], names[2])):
        d = Z[b] - Z[a]
        gy, gx = np.gradient(Z[a], 50); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        st = ~ice & np.isfinite(d) & (slope < 20) & (np.abs(d - np.nanmedian(d[~ice])) < 30)
        M = np.c_[np.ones(st.sum()), (X[st] - X.mean()) / 1e3, (Y[st] - Y.mean()) / 1e3, (Z[a][st] - 1500) / 100]
        k, *_ = np.linalg.lstsq(M, d[st], rcond=None)
        res = d[st] - M @ k
        print(f'\n{gname} {b[-8:]} minus {a[-8:]}: stable ground n {st.sum()}, median {np.median(d[st]):+.1f} m, NMAD {1.4826*np.median(np.abs(d[st]-np.median(d[st]))):.1f}; '
              f'fit {k[0]:+.1f} m {k[1]:+.2f} m/km east {k[2]:+.2f} m/km north {k[3]:+.2f} m/100 m elev, residual NMAD {1.4826*np.median(np.abs(res-np.median(res))):.1f}')
        zb = np.floor(Z[a] / 100) * 100
        on = ~geometry_mask(list(g[g.Year == int(a[-8:-4])].geometry), sh, tr) & np.isfinite(d)
        print('  glacier band: ' + '  '.join(f'{z:.0f} {np.median(d[on & (zb == z)]):+.1f}' for z in np.unique(zb[on]) if (on & (zb == z)).sum() > 20))
        gs = ~ice & np.isfinite(d) & (slope < 20)
        print('  ground band:  ' + '  '.join(f'{z:.0f} {np.median(d[gs & (zb == z)]):+.1f}' for z in np.unique(zb[gs]) if (gs & (zb == z)).sum() > 50))
