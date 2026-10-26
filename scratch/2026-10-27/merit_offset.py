"""Survey minus the domain DEM (MERIT) on the ground around each benchmark glacier, by distance from the earliest
outline and by slope, for the reference and start surveys, on the UTM grid, over the ground both cover."""
import sys
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
import numpy as np, geopandas as gpd, rasterio
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling, calculate_default_transform
from scipy.ndimage import distance_transform_edt
from domain_config import load_config
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp').to_crs(32606)
for name, gl, ns in (('gulkana', 'Gulkana Glacier', ('Deltas_20160830', 'Deltas_20070811', 'Deltas_20050808', 'Deltas_19930711')),
                     ('wolverine', 'Wolverine Glacier', ('EasternKenai_20150813', 'EasternKenai_20060808', 'EasternKenai_19950927'))):
    c = load_config(f'{WF}/domains/{name}.yaml')
    with rasterio.open(f"{c['project_dir']}/attributes/elevation/dem/domain_{c['domain']}_elv.tif") as s:
        tr, w, h = calculate_default_transform(s.crs, 'EPSG:32606', s.width, s.height, *s.bounds)
        M = np.full((h, w), np.nan)
        reproject(s.read(1).astype(float), M, src_transform=s.transform, src_crs=s.crs, dst_transform=tr, dst_crs='EPSG:32606', resampling=Resampling.bilinear)
    sh = M.shape
    allice = ~geometry_mask(list(u[u.Glacier == gl].geometry), sh, tr)
    dist = distance_transform_edt(~allice) * abs(tr.a)
    gy, gx = np.gradient(M, abs(tr.a)); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    D = {}
    for n in ns:
        with rasterio.open(f'{WF}/GlacierDEM/{n}_DEM/{n}_DEM.tif') as s:
            f = max(1, int(2.0 / abs(s.res[0])))
            z = s.read(1, masked=True, out_shape=(s.height // f, s.width // f), resampling=Resampling.average).astype(float).filled(np.nan)
            t = s.transform * s.transform.scale(s.width / z.shape[1], s.height / z.shape[0])
            o = np.full(sh, np.nan)
            reproject(z, o, src_transform=t, src_crs=s.crs, src_nodata=np.nan, dst_transform=tr, dst_crs='EPSG:32606', dst_nodata=np.nan, resampling=Resampling.average)
        D[n] = o - M
    common = ~allice & np.all([np.isfinite(d) for d in D.values()], 0) & (dist < 1000)
    print(f'\n{name}: survey minus MERIT (m), median on ground within 1 km covered by all ({common.sum()} cells)')
    print('  ' + ' '.join(f'{n[-8:]:>9s}' for n in ns) + '   where')
    for lab, k in (('all', common), ('<300 m', common & (dist < 300)), ('300-1000 m', common & (dist >= 300)),
                   ('slope<15', common & (slope < 15)), ('slope>=30', common & (slope >= 30))):
        print('  ' + ' '.join(f'{np.median(D[n][k]):+9.1f}' for n in ns) + f'   {lab} ({k.sum()})')
    for n in ns:
        k = ~allice & np.isfinite(D[n]) & (dist < 1000)
        print(f'  {n[-8:]} own footprint within 1 km: {np.median(D[n][k]):+.1f} ({k.sum()} cells)')
