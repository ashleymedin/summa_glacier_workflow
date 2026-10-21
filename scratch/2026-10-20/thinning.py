"""Mean surface change on the start glacier, and median thickness on the cells the last survey loses (clean, debris), per run."""
import glob, sys, numpy as np, netCDF4 as nc4, geopandas as gpd
from rasterio.features import rasterize
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
from domain_config import load_config
from glacier_cold_state import grid_transforms
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
def grids(run):
    out = []
    for f in sorted(glob.glob(f'{run}/output/*spinup_rank0001_annual.nc')) + sorted(glob.glob(f'{run}/output/*sample*_annual.nc')):
        with nc4.Dataset(f) as d:
            t = nc4.num2date(d['time'][:], d['time'].units)
            S = np.asarray(d['surface_elev'][:], float)
            for i in range(len(t)): out.append((t[i].year, S[i]))
    return out
for name, case, trial, gl, y0, y1, labels in (('gulkana', 'gulkana_corrected', 384, 'Gulkana Glacier', 2007, 2021, sys.argv[1:]),
                                               ('wolverine', 'wolverine_corrected', 469, 'Wolverine Glacier', 2006, 2020, sys.argv[1:])):
    c = load_config(f'{WF}/domains/{name}.yaml')
    ins = f'{WF}/runs/{case}/summa_inputs_flow'
    with nc4.Dataset(f'{ins}/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float); ids = np.asarray(d['gridId'][:, 0]).astype(int)
        nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
    g = int(np.argmax(nx * ny)); b = bed[:ny[g], :nx[g], g]
    with nc4.Dataset(f'{ins}/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]; d0 = np.asarray(d['debris_thick'][:, :, g, 0], float)[:ny[g], :nx[g]]
    tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
    G = u[u.Glacier == gl].to_crs(crs)
    mask = lambda y: rasterize(G[G.Year == y].geometry, out_shape=(ny[g], nx[g]), transform=tr[int(ids[g])]).astype(bool)
    H0 = s0 - b; on = H0 > 0.1; lost = mask(y0) & ~mask(y1) & on
    print(f'{name}: start {on.sum()} cells, lost by {y1}: {lost.sum()} ({(lost & (d0<0.02)).sum()} clean)')
    for lab in labels:
        run = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{lab}'
        yrs = dict(grids(run))
        S1 = yrs[y1][:ny[g], :nx[g], g, 0]
        dS = S1 - s0
        H1 = np.maximum(S1 - b, 0)
        print(f'  {lab:14s} mean dS on start glacier {dS[on].mean():6.1f} m;  lost cells H0->H{y1} clean {np.median(H0[lost&(d0<0.02)]):4.0f}->{np.median(H1[lost&(d0<0.02)]):4.0f}'
              f'  debris {np.median(H0[lost&(d0>=0.02)]) if (lost&(d0>=0.02)).any() else np.nan:4.0f}->{np.median(H1[lost&(d0>=0.02)]) if (lost&(d0>=0.02)).any() else np.nan:4.0f} m;'
              f'  still ice {(H1[lost]>0.1).mean()*100:3.0f}%')
    for lab, sel in (('clean', lost & (d0 < 0.02)), ('debris', lost & (d0 >= 0.02))):
        z = s0[sel]
        print(f'  lost {lab}: start surface quartiles {np.percentile(z,25):.0f} {np.median(z):.0f} {np.percentile(z,75):.0f} m, '
              f'below 1500 m {(z<1500).sum() if name=="gulkana" else (z<800).sum()} cells, H0 by band:',
              ' '.join(f'{lo}:{np.median(H0[sel & (s0>=lo) & (s0<lo+200)]):.0f}({(sel & (s0>=lo) & (s0<lo+200)).sum()})'
                       for lo in range(200, 2600, 200) if (sel & (s0>=lo) & (s0<lo+200)).any()))
