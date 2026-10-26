"""Gulkana's start thickness on the flow grid: the current setup (DEM-grid bed, regridded nearest) against
glacier_rasters' UTM bed with Millan sampled once, by distance in from the start edge and at the cells that
over-retreated in the melt-out run."""
import sys, os, tempfile
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
import numpy as np, rasterio
from scipy.ndimage import distance_transform_edt
from affine import Affine
from glacier_cold_state import reproject_to_utm
new_dir = sys.argv[1]
A = f'{WF}/data/domain_Gulkana/attributes/elevation/dem/domain_Gulkana_'
def old(key):
    with tempfile.TemporaryDirectory() as t:
        reproject_to_utm(A + f'{key}_elv.tif', f'{t}/x.tif', 32606)
        with rasterio.open(f'{t}/x.tif') as s: return s.read(1).astype(float), s.transform
So, tr = old('glacier'); Bo, _ = old('bedrock')
with rasterio.open(f'{new_dir}/domain_Gulkana_glacier_elv_utm.tif') as s: Sn, trn = s.read(1).astype(float), s.transform
with rasterio.open(f'{new_dir}/domain_Gulkana_bedrock_elv_utm.tif') as s: Bn = s.read(1).astype(float)
assert Sn.shape == So.shape and tuple(trn)[:6] == tuple(tr)[:6], (Sn.shape, So.shape)
Ho, Hn = So - Bo, Sn - Bn
ice = (Hn > 0.1) | (Ho > 0.1)
dist = distance_transform_edt(ice) * 51.0
print(' dist in (m)  km2   old H  new H   (start ice)')
for a, b in ((0, 60), (60, 120), (120, 200), (200, 400), (400, 1e4)):
    s = ice & (dist >= a) & (dist < b)
    print(f' {a:4.0f}-{b:<5.0f} {s.sum()*51.0**2/1e6:5.2f} {np.median(Ho[s]):6.1f} {np.median(Hn[s]):6.1f}')
print(f'volume km3: old {np.maximum(Ho, 0)[ice].sum()*51.0**2/1e9:.3f}, new {np.maximum(Hn, 0)[ice].sum()*51.0**2/1e9:.3f}')
z = np.load(f'{WF}/scratch/2026-10-26/upper_margins_meltout_usgsmb_A0.4.npz')
ov = z['band'] & (z['H1'] <= 0.1) & z['m1']
gt = Affine(*z['tr']); r, k = np.where(ov); x, y = gt * (k + 0.5, r + 0.5)
rr, kk = rasterio.transform.rowcol(tr, x, y); rr, kk = np.asarray(rr), np.asarray(kk)
print(f'over-lost cells ({ov.sum()}): old H median {np.median(Ho[rr, kk]):.1f}, new {np.median(Hn[rr, kk]):.1f}, '
      f'Millan direct {np.nanmedian(z["mil"][ov]):.1f}')
