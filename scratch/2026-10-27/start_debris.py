"""The 2004 start's domain types on the benchmark glacier beyond Herreid and Pellicciotti's outline, by elevation,
and the debris thickness of debris cells inside and beyond it."""
import sys
import numpy as np, rasterio, geopandas as gpd
from rasterio.features import geometry_mask
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
glc = gpd.read_file(f'{WF}/data/external/Debris_data/S1/01Alaska/01Alaska_minGl1km2.shp')
for d, name, gid in ((sys.argv[1], 'Gulkana', '00570'), (sys.argv[2], 'Wolverine', '09162')):
    f = rasterio.open(f'{d}/domain_{name}_domain_type.tif'); t = f.read(1)
    r = rasterio.open(f'{d}/domain_{name}_rgi_id.tif').read(1)
    z = rasterio.open(f'{d}/domain_{name}_glacier_elv.tif').read(1)
    h = rasterio.open(f'{d}/domain_{name}_debris_thickness.tif').read(1)
    hp = geometry_mask(list(glc[glc.RGIId == f'RGI50-01.{gid}'].to_crs(f.crs).geometry), transform=f.transform, invert=True, out_shape=t.shape)
    g = r == 100000 + int(gid)
    print(f'{name}: cells by type (accumulation, clean, debris) in the mapped outline '
          f'{[int((t[g & hp] == k).sum()) for k in (2, 3, 4)]}, beyond it {[int((t[g & ~hp] == k).sum()) for k in (2, 3, 4)]}')
    for k, n in ((2, 'accumulation'), (3, 'clean'), (4, 'debris')):
        m = g & ~hp & (t == k)
        if m.any(): print(f'  beyond, {n}: elevation 10/50/90% {np.percentile(z[m], [10, 50, 90]).round(0)}')
    for n, m in (('in', g & hp & (t == 4)), ('beyond', g & ~hp & (t == 4))):
        if m.any(): print(f'  debris thickness {n}: median {np.median(h[m]):.2f} m, 10/90% {np.percentile(h[m], [10, 90]).round(2)}')
