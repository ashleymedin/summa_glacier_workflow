"""Gulkana: height change since the first ArcticDEM strip over each strip USGS dropped, after removing each strip's
vertical offset on ground outside the 1957 outline. Ice left out of an outline keeps sinking; melted-out ground does not."""
import glob, os
import numpy as np, geopandas as gpd
from affine import Affine
from rasterio.features import geometry_mask
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
D = f'{WF}/scratch/2026-10-22'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
g = u[u.Glacier == 'Gulkana Glacier'].to_crs(3413).set_index('Year').geometry
from shapely.geometry import box as sbox
tongue = gpd.GeoSeries([sbox(577300, 7014000, 580300, 7017600)], crs=32606).to_crs(3413).iloc[0]  # UTM 6N
zones = {f'{a}-{b}': g[a].difference(g[b]).intersection(tongue) for a, b in ((1993, 2005), (2005, 2014), (2014, 2016), (2016, 2021))}
zones['2021 ice <1400'] = None
t = Affine(*np.load(f'{D}/gulkana_ring_arcticdem.npz', allow_pickle=True)['transform'])
files = sorted(glob.glob(f'{D}/arcticdem/*.npy'))
Z = {os.path.basename(f)[:10]: np.load(f).astype(float) for f in files}
dates = list(Z); ref = Z[dates[0]]
shape = ref.shape
m = {k: ~geometry_mask([v], shape, t) for k, v in zones.items() if v is not None}
m['2021 ice <1400'] = ~geometry_mask([g[2021]], shape, t) & (ref < 1400 + 16)  # ArcticDEM is ellipsoidal like USGS
stable = geometry_mask([g[1957].buffer(150)], shape, t)
gy, gx = np.gradient(ref, 2.0); stable &= np.hypot(gx, gy) < 0.3  # flat-ish off-glacier ground
for k in m: m[k] &= np.isfinite(ref)
print(f'reference {dates[0]}; height change (m) per zone, median [IQR]; stable-ground offset removed (n stable px)')
print('date        ' + ''.join(f'{k:>20s}' for k in m) + '      offset  nstab')
for d in dates[1:]:
    dz = Z[d] - ref
    s = stable & np.isfinite(dz); off = np.median(dz[s]); dz -= off
    cells = []
    for k, mk in m.items():
        v = dz[mk & np.isfinite(dz)]
        cells.append(f'{np.median(v):7.1f} [{np.percentile(v, 25):5.1f} {np.percentile(v, 75):5.1f}]' if v.size > 100 else ' ' * 20)
    print(d, ''.join(f'{c:>20s}' for c in cells), f'{off:8.1f} {s.sum():6d}')

# starting ice thickness in the setup over each zone, against the lowering ArcticDEM saw
import rasterio, rasterio.mask
A = f'{WF}/data/domain_Gulkana/attributes/elevation/dem/domain_Gulkana_'
with rasterio.open(A + 'glacier_elv.tif') as s, rasterio.open(A + 'bedrock_elv.tif') as b:
    H = s.read(1).astype(float) - b.read(1).astype(float); H[(H < 0) | (H > 2000)] = np.nan
    for k, z in list(zones.items())[:4] + [('2021 ice', g[2021].intersection(tongue))]:
        gg = gpd.GeoSeries([z], crs=3413).to_crs(s.crs)
        msk = ~geometry_mask(list(gg), H.shape, s.transform)
        v = H[msk & np.isfinite(H)]
        print(f'{k:10s} setup ice thickness median {np.median(v):5.0f} m [{np.percentile(v, 25):4.0f} {np.percentile(v, 75):4.0f}], n {v.size}')
