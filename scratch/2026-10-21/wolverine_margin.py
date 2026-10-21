"""Wolverine cells the 2020 survey loses from the 2006 outline, by 100 m band (USGS heights of the start surface):
start ice, ice left in 2020, the USGS profile's mean balance there, and the melt that would remove the start ice by 2020.
Then the lowest stakes' annual balance against the profile at their elevation, 2007-2020."""
import sys, glob, csv
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
import numpy as np, geopandas as gpd, netCDF4 as nc4
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from domain_config import load_config
from glacier_cold_state import grid_transforms
from compare_glacier_change import yearly

WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
DZ, RWI, Y0, Y1 = -14.0, 1000 / 917, 2006, 2020
label = sys.argv[1] if len(sys.argv) > 1 else 'usgsmb2_A0.4'
MB = f'{WF}/data/domain_Wolverine/observations/storage/mass_balance'
c = load_config(f'{WF}/domains/wolverine.yaml')
run = f'{WF}/runs/wolverine_corrected/calibration_paper1_rerun/sample_469_{label}'
with nc4.Dataset(run + '_settings/attributes.nc') as d:
    bed = np.asarray(d['bed_elev'][:, :, :, 0], float); ids = np.asarray(d['gridId'][:, 0]).astype(int)
    nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int); dx = float(np.asarray(d['dx'][:]).flat[0])
g = int(np.argmax(nx * ny)); b = bed[:ny[g], :nx[g], g]
with nc4.Dataset(run + '_settings/coldState.nc') as d:
    s0 = np.asarray(d['surface_elev'][:ny[g], :nx[g], g, 0], float); d0 = np.asarray(d['debris_thick'][:ny[g], :nx[g], g, 0], float)
S, D, years = yearly(sorted(glob.glob(f'{run}/output/*spinup_rank0001_annual.nc')) + sorted(glob.glob(f'{run}/output/*sample*_annual.nc')))
H1 = np.maximum(S[list(years).index(Y1), :ny[g], :nx[g], g] - b, 0)
tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
gl = u[u.Glacier == 'Wolverine Glacier'].to_crs(crs)
mask = lambda y: rasterize(gl[gl.Year == y].geometry, out_shape=(ny[g], nx[g]), transform=tr[int(ids[g])]).astype(bool)
m0, m1 = mask(Y0), mask(Y1)
H0 = np.maximum(s0 - b, 0)
lost = m0 & ~m1 & (H0 > 0.1)
dist = distance_transform_edt(m0) * dx

a = np.loadtxt(f'{MB}/wolverine_balance_profile.txt', comments='!')
prof = lambda y, z: np.interp(z, a[(a[:, 0] == y) & (a[:, 1] == 0), 2], a[(a[:, 0] == y) & (a[:, 1] == 0), 3])
bal = np.mean([prof(y, s0) for y in range(Y0 + 1, Y1 + 1)], axis=0) * RWI  # m ice/yr, clean rows, start surface
n = Y1 - Y0
print(f'{label}: survey loses {lost.sum() * dx * dx / 1e6:.2f} km2; model melts out {(lost & (H1 <= 0.1)).sum() * dx * dx / 1e6:.2f} of it by {Y1}')
print(' band  lost km2  melted  debris%  edge dist m  H0 med  H2020 med  profile m ice/yr  needed m ice/yr')
Z = np.floor((s0 - DZ) / 100) * 100
for z in np.unique(Z[lost]):
    k = lost & (Z == z)
    if k.sum() * dx * dx < 0.01e6: continue
    print(f' {z:5.0f} {k.sum() * dx * dx / 1e6:8.2f} {(k & (H1 <= 0.1)).sum() * dx * dx / 1e6:7.2f} {(d0[k] >= 0.02).mean() * 100:7.0f}'
          f' {np.median(dist[k]):11.0f} {np.median(H0[k]):7.0f} {np.median(H1[k]):10.0f} {np.median(bal[k]):17.1f} {-np.median(H0[k]) / n:15.1f}')

print('\nlowest stakes, ba (m w.e.) against the profile at the stake elevation, mean over years with both')
rows = [r for r in csv.DictReader(open(f'{MB}/Input_Wolverine_Glaciological_Data.csv')) if Y0 < int(r['Year']) <= Y1 and r['ba'] not in ('', 'nan')]
for site in sorted({r['site_name'] for r in rows}, key=lambda s: np.mean([float(r['elevation']) for r in rows if r['site_name'] == s])):
    x = [r for r in rows if r['site_name'] == site]
    zs = np.mean([float(r['elevation']) for r in x])
    if zs > 1100: continue
    obs = np.mean([float(r['ba']) for r in x]); mod = np.mean([prof(int(r['Year']), float(r['elevation']) + DZ) for r in x])
    print(f' {site:4s} {zs:6.0f} m  n={len(x):2d}  stakes {obs:6.2f}  profile {mod:6.2f}')

# per-cell budget 2007-2020 on the lost cells, with the debris rows where the model has debris: dH = B + F
prof_d = lambda y, z, dbr: np.interp(z, a[(a[:, 0] == y) & (a[:, 1] == dbr), 2], a[(a[:, 0] == y) & (a[:, 1] == dbr), 3]) \
    if ((a[:, 0] == y) & (a[:, 1] == dbr)).any() else prof(y, z)
yl = list(years)
with nc4.Dataset(run + '_settings/coldState.nc') as d:
    Sp, Dp = s0, d0
Bsum = np.zeros_like(s0); Hp = H0
for y in range(Y0 + 1, Y1 + 1):
    if y not in yl: continue
    i = yl.index(y); Sn = S[i, :ny[g], :nx[g], g]; Dn = D[i, :ny[g], :nx[g], g]; Hn = np.maximum(Sn - b, 0)
    zc = 0.5 * (Sp + Sn)
    bb = np.where(Dp >= 0.02, prof_d(y, zc, 1), prof_d(y, zc, 0)) * RWI
    Bsum += np.where((Hp > 0.1) | (Hn > 0.1), np.maximum(bb, -Hp - np.maximum(Hn - Hp, 0)), 0)
    Sp, Dp, Hp = Sn, Dn, Hn
years_used = len([y for y in range(Y0 + 1, Y1 + 1) if y in yl])
print(f'\nbudget on the lost cells over {years_used} years (m ice per year, medians): dH = B + F')
print(' band  dH/yr  B/yr  F/yr   debris-row balance vs clean at the start surface')
for z in np.unique(Z[lost]):
    k = lost & (Z == z)
    if k.sum() * dx * dx < 0.01e6: continue
    dH = (H1 - H0)[k] / years_used; B = Bsum[k] / years_used
    cl = np.mean([prof(y, s0[k]) for y in range(Y0 + 1, Y1 + 1)]) * RWI
    db = np.mean([prof_d(y, s0[k], 1) for y in range(Y0 + 1, Y1 + 1)]) * RWI
    print(f' {z:5.0f} {np.median(dH):6.1f} {np.median(B):5.1f} {np.median(dH - B):5.1f}   {db:6.1f} vs {cl:6.1f}')

print(f'\nice left in {Y1} on the lost cells (km2 by thickness class)')
print(' band   gone  0.1-1 m  1-5 m  5-20 m  >20 m')
for z in np.unique(Z[lost]):
    k = lost & (Z == z)
    if k.sum() * dx * dx < 0.01e6: continue
    h = H1[k]; f = lambda m: m.sum() * dx * dx / 1e6
    print(f' {z:5.0f} {f(h <= 0.1):6.2f} {f((h > 0.1) & (h <= 1)):8.2f} {f((h > 1) & (h <= 5)):6.2f} {f((h > 5) & (h <= 20)):7.2f} {f(h > 20):6.2f}')

D1 = D[list(years).index(Y1), :ny[g], :nx[g], g]
thin = lost & (H1 > 0.1) & (H1 <= 1)
print(f'\nthin cells (0.1-1 m above the bed in {Y1}): {thin.sum()} cells; surface - bed median {np.median(H1[thin]):.2f} m, '
      f'debris median {np.median(D1[thin]):.2f} m, ice (surface - debris - bed) median {np.median((H1 - D1)[thin]):.3f} m, '
      f'cells with ice under 0.1 m: {((H1 - D1)[thin] <= 0.1).mean() * 100:.0f}%')
allc = (S[list(years).index(Y1), :ny[g], :nx[g], g] - b) > 0.1
ice = (S[list(years).index(Y1), :ny[g], :nx[g], g] - D1 - b) > 0.1
print(f'whole grid {Y1}: surface above bed by >0.1 m {allc.sum() * dx * dx / 1e6:.2f} km2, ice >0.1 m {ice.sum() * dx * dx / 1e6:.2f} km2')
