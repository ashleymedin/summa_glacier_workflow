"""ITS_LIVE v2 annual 120 m mosaics (v, v_error, count) on each glacier's model flow grid, nearest neighbour, 2006-2022.
Writes data/domain_<Name>/observations/storage/velocity/itslive_annual.npz."""
import os, sys
import numpy as np, netCDF4 as nc4, rasterio
from rasterio.warp import reproject, Resampling
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
from domain_config import load_config
from glacier_cold_state import grid_transforms

URL = '/vsicurl/https://its-live-data.s3.amazonaws.com/velocity_mosaic/v2/annual/cog/ITS_LIVE_velocity_120m_RGI01A_{y}_v02_{f}.tif'
CASES = dict(gulkana=('gulkana_corrected', 384, 'Gulkana'), wolverine=('wolverine_corrected', 469, 'Wolverine'))
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')

for name in sys.argv[1:] or CASES:
    case, trial, cap = CASES[name]
    c = load_config(f'{WF}/domains/{name}.yaml')
    tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
    with nc4.Dataset(f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_usgsmb2_A1_settings/attributes.nc') as d:
        nx, ny = np.asarray(d['nx'][:, 0]).astype(int), np.asarray(d['ny'][:, 0]).astype(int)
        ids = np.asarray(d['gridId'][:, 0]).astype(int)
    g = int(np.argmax(nx * ny)); t = tr[int(ids[g])]
    years = np.arange(2006, 2023)
    out = {f: np.full((len(years), ny[g], nx[g]), np.nan, np.float32) for f in ('v', 'v_error', 'count')}
    for i, y in enumerate(years):
        for f in out:
            with rasterio.open(URL.format(y=y, f=f)) as src:
                reproject(rasterio.band(src, 1), out[f][i], dst_transform=t, dst_crs=crs, dst_nodata=np.nan,
                          resampling=Resampling.nearest, src_nodata=src.nodata)
        print(name, y, np.nanmedian(out['v'][i]), flush=True)
    od = f'{WF}/data/domain_{cap}/observations/storage/velocity'
    os.makedirs(od, exist_ok=True)
    np.savez_compressed(f'{od}/itslive_annual.npz', years=years, transform=np.array(t)[:6], **out)
    print('wrote', od)
