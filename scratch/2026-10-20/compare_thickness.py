"""Millan (2022) against Farinotti (2019) thickness on Farinotti's 25 m grid, per glacier."""
import glob, os
import numpy as np, rasterio, geopandas as gpd
from rasterio.warp import reproject, Resampling
from rasterio.features import geometry_mask
from scipy.ndimage import distance_transform_edt

H = os.path.expanduser('~/Research/USask/Thickness_data')
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
rgi = gpd.read_file(os.path.expanduser('~/Research/USask/RGI_data/nsidc0770_01.rgi60.Alaska/01_rgi60_Alaska.shp'))
usgs = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
millan = sorted(glob.glob(f'{H}/RGI-1/THICKNESS_RGI-1.*.tif'))
for gid, name, dom, tongue, date in (('00570', 'Gulkana', 'Gulkana', 1400, '2007/08/11'),
                                    ('09162', 'Wolverine', 'Wolverine', 700, '2006/08/08')):
    f = rasterio.open(f'{H}/Farinotti2019/RGI60-01/RGI60-01.{gid}_thickness.tif')
    F = f.read(1).astype(float)
    M = np.zeros_like(F)
    for p in millan:
        tmp = np.full_like(F, np.nan)
        with rasterio.open(p) as s:
            reproject(rasterio.band(s, 1), tmp, dst_transform=f.transform, dst_crs=f.crs, resampling=Resampling.bilinear,
                      src_nodata=s.nodata, dst_nodata=np.nan)
        ok = np.isfinite(tmp) & (tmp > 0)
        M[ok] = tmp[ok]
    Z = np.full_like(F, np.nan)
    with rasterio.open(f'{WF}/data/domain_{dom}/attributes/elevation/dem/domain_{dom}_elv.tif') as s:
        reproject(rasterio.band(s, 1), Z, dst_transform=f.transform, dst_crs=f.crs, resampling=Resampling.bilinear)
    out = rgi[rgi.RGIId == f'RGI60-01.{gid}'].to_crs(f.crs).geometry.iloc[0]
    us = usgs[(usgs.Glacier == f'{name} Glacier') & (usgs.Date == date)].to_crs(f.crs).geometry.union_all()
    g = geometry_mask([out], transform=f.transform, invert=True, out_shape=F.shape)
    u = geometry_mask([us], transform=f.transform, invert=True, out_shape=F.shape)
    d = distance_transform_edt(g) * 25 - 12.5
    a = 25 * 25 / 1e6
    print(f'\n{name} RGI60-01.{gid}: RGI outline {g.sum()*a:.2f} km2, USGS {date} {u.sum()*a:.2f} km2')
    for lab, T in (('Millan', M), ('Farinotti', F)):
        print(f'  {lab:9s} volume {T[g].sum()*25*25/1e9:.3f} km3, mean {T[g].mean():.0f} m, max {T[g].max():.0f} m, '
              f'zero cells in RGI outline {(g & (T <= 0)).sum()*a:.2f} km2, in USGS outline {(u & (T <= 0)).sum()*a:.2f} km2, '
              f'tongue <{tongue} m mean {T[g & (Z < tongue)].mean():.0f} m')
    print('  distance from RGI outline (m):  ' + '  '.join(f'{lo}-{hi}' for lo, hi in ((0, 25), (25, 75), (75, 150), (150, 300), (300, 600))))
    for lab, T in (('Millan', M), ('Farinotti', F)):
        print(f'  {lab:9s} median thickness  ' + '  '.join(f'{np.median(T[g & (d >= lo) & (d < hi)]):5.0f}'
                                                        for lo, hi in ((0, 25), (25, 75), (75, 150), (150, 300), (300, 600))))
    print(f'  tongue cells <{tongue} m: Millan-Farinotti median {np.median((M-F)[g & (Z < tongue)]):.0f} m; '
          f'correlation in outline {np.corrcoef(M[g], F[g])[0,1]:.2f}')
