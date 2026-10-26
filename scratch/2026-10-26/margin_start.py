"""At Gulkana's over-lost upper-margin cells: the setup's thickness (glacier_elv - bedrock_elv) and Millan's,
nearest onto the flow grid, against the cold state's ice."""
import sys, os
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
import numpy as np, rasterio
from affine import Affine
from rasterio.warp import reproject, Resampling
from domain_config import load_config
c = load_config(f'{WF}/domains/gulkana.yaml')
z = np.load(f'{WF}/scratch/2026-10-26/upper_margins_meltout_usgsmb_A0.4.npz')
tr = Affine(*z['tr']); sh = z['H0'].shape
from pyproj import CRS; crs = CRS.from_epsg(c['utm_epsg'])
def near(f):
    a = np.full(sh, np.nan)
    with rasterio.open(f) as s:
        reproject(rasterio.band(s, 1), a, src_transform=s.transform, src_crs=s.crs, dst_transform=tr, dst_crs=crs,
                  resampling=Resampling.nearest, src_nodata=s.nodata, dst_nodata=np.nan)
    return a
A = f"{c['project_dir']}/attributes/elevation/dem/domain_{c['domain']}_"
Hs = near(A + 'glacier_elv.tif') - near(A + 'bedrock_elv.tif')
rn = str(int(c['rgi6_region'][:2])); tdir = os.path.join(os.path.expanduser(c['data']['ice_thickness']), f'RGI-{rn}')
mil = np.full(sh, np.nan)
for f in sorted(os.listdir(tdir)):
    if f.startswith(f'THICKNESS_RGI-{rn}.') and f.endswith('tif'):
        m = near(os.path.join(tdir, f)); mil = np.where(np.isfinite(m) & (m > 0), m, mil)
H0, H1 = z['H0'], z['H1']
ov = z['band'] & (H1 <= 0.1) & z['m1']
keep = z['band'] & (H1 > 0.1) & z['m1'] & (z['dist'] < 200)
for n, s in (('over-lost', ov), ('kept edge 200 m', keep)):
    print(f'{n:16s} n {s.sum():4d}  cold-state H {np.median(H0[s]):5.1f}  setup H {np.nanmedian(Hs[s]):5.1f}  '
          f'Millan nearest {np.nanmedian(mil[s]):5.1f} (bare {np.isnan(mil[s]).mean()*100:.0f}%)  dist {np.median(z["dist"][s]):.0f} m')
d = Hs[ov] - H0[ov]
print('setup minus cold state at over-lost cells, quartiles', np.nanpercentile(d, [10, 25, 50, 75, 90]).round(1))

# on the DEM grid: setup thickness against Millan as glacier_rasters mosaics it, at the over-lost cells
import tempfile
from glacier_rasters import mosaic_to_dem
from rasterio.transform import rowcol
with rasterio.open(A + 'glacier_elv.tif') as s:
    Sd, dcrs, dtr, dsh = s.read(1).astype(float), s.crs, s.transform, s.shape
    print('DEM grid', dcrs, 'res', s.res)
with rasterio.open(A + 'bedrock_elv.tif') as s: Bd = s.read(1).astype(float)
with tempfile.TemporaryDirectory() as tmp:
    Md = mosaic_to_dem([os.path.join(tdir, f) for f in sorted(os.listdir(tdir)) if f.startswith(f'THICKNESS_RGI-{rn}.') and f.endswith('tif')], dcrs, dsh, dtr, tmp)
from pyproj import Transformer
t = Transformer.from_crs(crs, dcrs, always_xy=True)
r, k = np.where(ov); x, y = tr * (k + 0.5, r + 0.5); lon, lat = t.transform(x, y)
rr, kk = rowcol(dtr, lon, lat)
rr, kk = np.asarray(rr), np.asarray(kk)
Hd = (Sd - Bd)[rr, kk]; Mdv = Md[rr, kk]
print('over-lost on DEM grid: setup H', np.percentile(Hd, [25, 50, 75]).round(1), ' Millan mosaic', np.nanpercentile(Mdv, [25, 50, 75]).round(1),
      ' bed raised vs surface-Millan (m)', np.nanpercentile(Bd[rr, kk] - (Sd[rr, kk] - Mdv), [25, 50, 75]).round(1))

# whole glacier: cold-state ice against Millan sampled straight onto the flow grid, by distance in from the 2007 edge
ice = z['m0'] & (H0 > 0.1)
print('\ndist in (m)  km2   cold-state H  Millan direct  ratio   (2007 ice, all elevations)')
for a, b in ((0, 60), (60, 120), (120, 200), (200, 400), (400, 1e4)):
    s = ice & (z['dist'] >= a) & (z['dist'] < b) & np.isfinite(mil)
    print(f' {a:4.0f}-{b:<5.0f} {s.sum()*51.0**2/1e6:5.2f} {np.median(H0[s]):10.1f} {np.median(mil[s]):12.1f} {np.median(H0[s])/np.median(mil[s]):7.2f}')
s = ice & np.isfinite(mil)
print(f'volume km3: cold state {H0[s].sum()*51.0**2/1e9:.3f}, Millan direct {mil[s].sum()*51.0**2/1e9:.3f}')

# 2024 radar on the flow grid: over-lost cells and kept upper-edge cells holding a pick, ice there in 2024 against the start
import pandas as pd
from rasterio.transform import rowcol as rc
r = pd.read_csv(f'{WF}/GlacierDEM/GulkanaRadarDepth/Gulkana_2024_radar_interpretations.csv').dropna(subset=['bed_elev'])
tx = Transformer.from_crs(32606, crs, always_xy=True)
px, py = tx.transform(r.utm6n_x.values, r.utm6n_y.values)
ri, ci = rc(tr, px, py); ri, ci = np.asarray(ri), np.asarray(ci)
ok = (ri >= 0) & (ri < sh[0]) & (ci >= 0) & (ci < sh[1])
r, ri, ci = r[ok], ri[ok], ci[ok]
upper = z['band'] & z['m1'] & (z['dist'] < 300)
for n, s in (('over-lost', ov), ('upper band, kept, within 300 m of edge', upper & (H1 > 0.1))):
    hit = s[ri, ci]
    if not hit.any(): print(f'{n}: no radar picks'); continue
    k = r[hit]; i, j = ri[hit], ci[hit]
    print(f'{n}: {hit.sum()} picks in {len(set(zip(i, j)))} cells; 2024 radar thickness med {k.srf_bed_thick.median():.0f} m, '
          f'start H {np.median(H0[i, j]):.0f}, Millan direct {np.nanmedian(mil[i, j]):.0f}, model 2021 H {np.median(H1[i, j]):.0f}; '
          f'radar bed minus setup bed med {np.median(k.bed_elev.values - (z["zu"][i, j] - H0[i, j])):.0f} m (USGS heights)')

# would Millan's own thickness have kept them: start ice plus the run's balance and flow change, unchanged flow
need = -(z['cum'] + z['flow'])
print(f'\nover-lost: start H < half Millan direct in {(H0[ov] < 0.5*mil[ov]).mean()*100:.0f}% of cells; '
      f'Millan direct > the run\'s balance+flow loss in {(mil[ov] > need[ov]).mean()*100:.0f}%, '
      f'{(ov & (mil > need)).sum()*51.0**2/1e6:.2f} of {ov.sum()*51.0**2/1e6:.2f} km2')
