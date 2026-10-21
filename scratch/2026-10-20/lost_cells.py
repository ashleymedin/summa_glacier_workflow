"""On cells inside the start USGS outline but outside a later survey's: the model's starting ice, its ice at that
survey's year, and the thinning still needed, per run."""
import sys, glob, os
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
import numpy as np, geopandas as gpd, netCDF4 as nc4
from rasterio.features import rasterize
from domain_config import load_config
from glacier_cold_state import grid_transforms
from compare_glacier_change import yearly

WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
label = sys.argv[1] if len(sys.argv) > 1 else 'flow_A1'
for name, case, trial, glacier, y0, ys in (('gulkana', 'gulkana_corrected', 384, 'Gulkana Glacier', 2007, (2014, 2016, 2021)),
                                           ('wolverine', 'wolverine_corrected', 469, 'Wolverine Glacier', 2006, (2011, 2015, 2020))):
    c = load_config(f'{WF}/domains/{name}.yaml')
    run = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
    with nc4.Dataset(run + '_settings/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float)
        ids = np.asarray(d['gridId'][:, 0]).astype(int); nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
        dx = float(np.asarray(d['dx'][:]).flat[0])
    g = int(np.argmax(nx * ny))
    with nc4.Dataset(run + '_settings/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]
    S, D, years = yearly(sorted(glob.glob(f'{run}/output/*sample*_annual.nc')))
    b = bed[:ny[g], :nx[g], g]
    tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
    gl = u[u.Glacier == glacier].to_crs(crs)
    mask = lambda y: rasterize(gl[gl.Year == y].geometry, out_shape=(ny[g], nx[g]), transform=tr[int(ids[g])]).astype(bool)
    m0 = mask(y0); H0 = np.where(s0 - b > 0.1, s0 - b, 0)
    print(f'\n{name} ({label}), start outline {m0.sum()*dx*dx/1e6:.2f} km2, model start ice {(H0>0.1).sum()*dx*dx/1e6:.2f} km2, dx {dx:.0f} m')
    for y in ys:
        lost = m0 & ~mask(y) & (H0 > 0.1)
        k = int(np.where(years == min(y, years.max()))[0][0])
        H = np.maximum(S[k, :ny[g], :nx[g], g] - b, 0)
        print(f'  {y}: survey loses {lost.sum()*dx*dx/1e6:.2f} km2; there the model starts with H median {np.median(H0[lost]):.0f} m '
              f'(p25 {np.percentile(H0[lost],25):.0f}, p75 {np.percentile(H0[lost],75):.0f}), thins {np.median(H0[lost]-H[lost]):.1f} m, '
              f'keeps {(H[lost]>0.1).mean()*100:.0f}% of them; needs {np.median(H[lost])/(y-y0):.1f} m/yr more')
    from scipy.ndimage import distance_transform_edt
    with nc4.Dataset(run + '_settings/coldState.nc') as d:
        d0 = np.asarray(d['debris_thick'][:, :, g, 0], float)[:ny[g], :nx[g]]
    lost = m0 & ~mask(ys[-1]) & (H0 > 0.1)
    dist = distance_transform_edt(m0) * dx
    k = int(np.where(years == min(ys[-1], years.max()))[0][0])
    H = np.maximum(S[k, :ny[g], :nx[g], g] - b, 0)
    for lab, sel in (('debris', lost & (d0 >= 0.02)), ('clean', lost & (d0 < 0.02))):
        if sel.sum():
            print(f'  {lab}: {sel.sum()*dx*dx/1e6:.2f} km2, start H median {np.median(H0[sel]):.0f} m, {ys[-1]} H {np.median(H[sel]):.0f} m, '
                  f'distance in from the start outline median {np.median(dist[sel]):.0f} m (p90 {np.percentile(dist[sel],90):.0f})')
    rows = np.where(lost.any(1))[0]; cols = np.where(lost.any(0))[0]
    print(f'  lost cells span rows {rows.min()}-{rows.max()}, cols {cols.min()}-{cols.max()}; surface {np.median(s0[lost]):.0f} m (p10 {np.percentile(s0[lost],10):.0f}, p90 {np.percentile(s0[lost],90):.0f})')
