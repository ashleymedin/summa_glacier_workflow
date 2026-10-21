"""How much of each glacier's ice, by 100 m band (USGS heights), is Millan's own thickness and how much is the
nearest-neighbour fill glacier_rasters.py gives outline cells Millan leaves bare."""
import os, sys
import numpy as np, rasterio
from scipy.ndimage import distance_transform_edt
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
from domain_config import load_config
from glacier_rasters import mosaic_to_dem
import tempfile

for name, dz in (('gulkana', -16.1), ('wolverine', -14.0)):
    c = load_config(f'{WF}/domains/{name}.yaml')
    p, d = c['project_dir'], c['domain']
    dem_dir = os.path.join(p, 'attributes', 'elevation', 'dem')
    with rasterio.open(os.path.join(dem_dir, f'domain_{d}_glacier_elv.tif')) as s:
        S, crs, tr = s.read(1).astype(float), s.crs, s.transform
        lat = tr.f + tr.e * s.height / 2
        dxm, dym = abs(tr.a) * 111320 * np.cos(np.radians(lat)), abs(tr.e) * 110540
        px = dxm * dym  # m2 per cell
    with rasterio.open(os.path.join(dem_dir, f'domain_{d}_bedrock_elv.tif')) as s: B = s.read(1).astype(float)
    with rasterio.open(os.path.join(p, 'attributes', 'glaciers', f'domain_{d}_rgi_id.tif')) as s: gid = s.read(1)
    rn = str(int(c['rgi6_region'][:2]))
    tdir = os.path.join(os.path.expanduser(c['data']['ice_thickness']), f'RGI-{rn}')
    files = [os.path.join(tdir, f) for f in sorted(os.listdir(tdir)) if f.startswith(f'THICKNESS_RGI-{rn}.') and f.endswith('tif')]
    with tempfile.TemporaryDirectory() as tmp:
        M = mosaic_to_dem(files, crs, S.shape, tr, tmp)
    gl = gid > 0
    own = gl & np.isfinite(M) & (M > 0)
    fill = gl & ~own
    dist = distance_transform_edt(~own, sampling=(dym, dxm))
    H = S - B
    main = gid == np.bincount(gid[gl]).argmax()
    print(f'\n{name}: main glacier {main.sum() * px / 1e6:.2f} km2, of it Millan-bare (filled) {(fill & main).sum() * px / 1e6:.2f} km2')
    print(' band  km2  filled km2  filled H med (m)  dist to Millan med (m)  Millan H med (m)')
    Z = np.floor((S - dz) / 100) * 100
    for z in np.unique(Z[main]):
        k = main & (Z == z)
        f = k & fill
        if k.sum() * px < 0.05e6: continue
        print(f' {z:5.0f} {k.sum() * px / 1e6:5.2f} {f.sum() * px / 1e6:6.2f} {np.median(H[f]) if f.any() else np.nan:12.0f}'
              f' {np.median(dist[f]) if f.any() else np.nan:16.0f} {np.median(H[k & own]) if (k & own).any() else np.nan:16.0f}')
