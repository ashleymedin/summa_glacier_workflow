"""Model cold-state surface minus the USGS survey DEM on the model's main glacier grid, by 100 m band."""
import numpy as np, rasterio, netCDF4 as nc4
from rasterio.warp import reproject, Resampling
import sys; sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow')
from domain_config import load_config
from glacier_cold_state import grid_transforms
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
for name, dem, case in (('gulkana', 'Deltas_20070811_DEM', 'gulkana_corrected'), ('wolverine', 'EasternKenai_20060808_DEM', 'wolverine_corrected')):
    c = load_config(f'{WF}/domains/{name}.yaml')
    ins = f'{WF}/runs/{case}/summa_inputs'
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
    d = s0 - z
    ok = ice & np.isfinite(d)
    print(f'{name}: {ok.sum()} of {ice.sum()} ice cells covered; model - survey DEM median {np.median(d[ok]):+.1f} m, '
          f'5-95% {np.percentile(d[ok], 5):+.1f} {np.percentile(d[ok], 95):+.1f}')
    for b in range(int(z[ok].min() // 100 * 100), int(z[ok].max()) + 100, 100):
        m = ok & (z >= b) & (z < b + 100)
        if m.sum(): print(f'   {b}-{b+100} m: {m.sum():5d} cells, median {np.median(d[m]):+6.1f} m')
