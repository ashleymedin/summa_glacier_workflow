"""Gulkana's 1 Oct 2004 start on the UTM grid: 2007 survey carried back by Hugonnet's dh/dt against the 1993/2005
interpolation, by 100 m band (USGS heights) of the start ice: surface and thickness."""
import sys
import numpy as np, rasterio, geopandas as gpd, yaml
from rasterio.features import geometry_mask
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
from glacier_rasters import start_outline
S = sys.argv[1]
c = yaml.safe_load(open(f'{S}/gulkana_2004.yaml'))
u = gpd.read_file('/Users/amedin/Research/SummaSundials/summa_glacier_workflow/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
u = u[u.Glacier == 'Gulkana Glacier'].to_crs(c['utm_crs'])
r = {}
for k in ('gr04_gulkana', 'gr04h_gulkana'):
    with rasterio.open(f'{S}/{k}/domain_Gulkana_glacier_elv_utm.tif') as f:
        s = f.read(1).astype(float); a = abs(f.transform.a * f.transform.e) / 1e6
        own = geometry_mask([start_outline(c['usgs_outline'], u)], transform=f.transform, invert=True, out_shape=s.shape)
    with rasterio.open(f'{S}/{k}/domain_Gulkana_bedrock_elv_utm.tif') as f: b = f.read(1).astype(float)
    r[k] = (s, s - b)
(si, hi), (sh, hh) = r['gr04_gulkana'], r['gr04h_gulkana']
ice = own & ((hi > 0.1) | (hh > 0.1))
d = np.abs((si - hi) - (sh - hh)) > 0.01
zu = sh + 16.1
print(f'Gulkana start ice km2: interpolated {(own & (hi > 0.1)).sum() * a:.2f}, 2007+Hugonnet {(own & (hh > 0.1)).sum() * a:.2f}; '
      f'bed differs on {(d & own).sum()} of its cells, {(d & ~own).sum()} elsewhere')
print(' band   km2  surf diff m (H-I)  NMAD   H interp  H 2007+Hug')
for z in range(1100, 2500, 100):
    k = ice & (zu >= z) & (zu < z + 100)
    if not k.any(): continue
    d = (sh - si)[k]
    print(f' {z:5d} {k.sum() * a:5.2f} {np.median(d):+16.1f} {1.4826 * np.median(np.abs(d - np.median(d))):5.1f} '
          f'{np.median(hi[k]):9.0f} {np.median(hh[k]):10.0f}')
