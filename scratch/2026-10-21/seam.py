import sys, numpy as np, rasterio, geopandas as gpd
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling
sys.path.insert(0, '.')
d = 'data/domain_Wolverine/attributes/elevation/dem/'
src = rasterio.open(d+'domain_Wolverine_elv.tif'); dem = src.read(1).astype(float)
gl = rasterio.open(d+'domain_Wolverine_glacier_elv.tif').read(1).astype(float)
rgi = rasterio.open('data/domain_Wolverine/attributes/glaciers/domain_Wolverine_rgi_id.tif').read(1)
u = gpd.read_file('GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
u = u[(u.Glacier=='Wolverine Glacier')&(u.Date=='2006/08/08')]
path='GlacierDEM/EasternKenai_20060808_DEM/EasternKenai_20060808_DEM.tif'
with rasterio.open(path) as s:
    z = s.read(1, masked=True).astype(float).filled(np.nan)
    cov = np.full(dem.shape, np.nan); cnt=np.isfinite(z).astype(float)
    reproject(cnt, cov, src_transform=s.transform, src_crs=s.crs, dst_transform=src.transform, dst_crs=src.crs, resampling=Resampling.average)
    zz = np.full(dem.shape, np.nan)
    reproject(z, zz, src_transform=s.transform, src_crs=s.crs, src_nodata=np.nan, dst_transform=src.transform, dst_crs=src.crs, dst_nodata=np.nan, resampling=Resampling.average)
ice = rgi>0
uw = geometry_mask(list(u.to_crs(src.crs).geometry), transform=src.transform, invert=True, out_shape=dem.shape)
print('ice cells', ice.sum(), 'usgs outline cells', uw.sum(), 'wolverine id', np.unique(rgi[uw]))
wid = np.bincount(rgi[uw]).argmax(); w = rgi==wid
print('wolverine cells', w.sum(), 'covered (finite)', (w&np.isfinite(zz)).sum(), 'coverage<0.5', (w&(cov<0.5)).sum())
diff = gl-dem
print('gl-dem on covered w cells: pct', np.nanpercentile(diff[w&np.isfinite(zz)],[5,25,50,75,95]))
print('raw survey - dem covered:', np.nanpercentile((zz-dem)[w],[5,25,50,75,95]))
# map of coverage
rows = np.where(w.any(1))[0]; cols=np.where(w.any(0))[0]
for r in rows[::2]:
    print(''.join(('.' if not w[r,c] else ('#' if np.isfinite(zz[r,c]) else 'o')) for c in cols))
np.savez('/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad/seam.npz', dem=dem, gl=gl, zz=zz, cov=cov, w=w, ice=ice)
