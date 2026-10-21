"""Wolverine start surface: survey-DEM coverage on the model grid, and the cell-to-cell steps on and off its edge."""
import sys, numpy as np, rasterio, netCDF4 as nc4
from rasterio.warp import reproject, Resampling
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
from domain_config import load_config
from glacier_cold_state import grid_transforms
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
for name, dem, case in (('wolverine', 'EasternKenai_20060808_DEM', 'wolverine_corrected'), ('gulkana', 'Deltas_20070811_DEM', 'gulkana_corrected')):
    c = load_config(f'{WF}/domains/{name}.yaml')
    ins = f'{WF}/runs/{case}/summa_inputs_flow'
    with nc4.Dataset(f'{ins}/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float); ids = np.asarray(d['gridId'][:, 0]).astype(int)
        nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
    g = int(np.argmax(nx * ny))
    with nc4.Dataset(f'{ins}/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]
    ice = (s0 - bed[:ny[g], :nx[g], g]) > 0.1
    tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
    z = np.full(s0.shape, np.nan)
    with rasterio.open(f'{WF}/GlacierDEM/{dem}/{dem}.tif') as s:
        reproject(s.read(1, masked=True).astype(float).filled(np.nan), z, src_transform=s.transform, src_crs=s.crs, src_nodata=np.nan,
                  dst_transform=tr[int(ids[g])], dst_crs=crs, dst_nodata=np.nan, resampling=Resampling.average)
    cov = np.isfinite(z)
    steps = []
    for a, b_ in ((s0[1:, :], s0[:-1, :]), (s0[:, 1:], s0[:, :-1])):
        pass
    dy_ = np.abs(np.diff(s0, axis=0)); dx_ = np.abs(np.diff(s0, axis=1))
    iy = ice[1:, :] & ice[:-1, :]; ix = ice[:, 1:] & ice[:, :-1]
    seam_y = cov[1:, :] != cov[:-1, :]; seam_x = cov[:, 1:] != cov[:, :-1]
    for lab, sel_y, sel_x in (('across the coverage edge', iy & seam_y, ix & seam_x), ('elsewhere on the ice', iy & ~seam_y, ix & ~seam_x)):
        v = np.concatenate([dy_[sel_y], dx_[sel_x]])
        print(f'{name} {lab}: {v.size} cell pairs, median step {np.median(v):.1f} m, 95% {np.percentile(v,95):.0f}, >50 m: {(v>50).sum()}')
    print(f'   ice cells covered by the survey DEM: {(cov&ice).sum()} of {ice.sum()}')
    if name == 'wolverine':
        for (x, y) in ((72, 24), (72, 23), (68, 18), (70, 21)):
            print(f'   cell ({x},{y}) covered {cov[y,x]}, neighbours covered', [bool(cov[y+a, x+c]) for a, c in ((-1,0),(1,0),(0,-1),(0,1))])
