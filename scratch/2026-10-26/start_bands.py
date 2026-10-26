"""Start ice by 100 m band (USGS heights) on the benchmark glacier's start outline: the current setup (DEM-grid
bed regridded) against glacier_rasters' flow-grid bed from Millan's reference survey (folder given)."""
import sys, tempfile
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
import numpy as np, rasterio, geopandas as gpd
from rasterio.features import geometry_mask
from glacier_cold_state import reproject_to_utm
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp').to_crs(32606)
for name, gl, year, dz in (('Gulkana', 'Gulkana Glacier', 2007, -16.1), ('Wolverine', 'Wolverine Glacier', 2006, -14.0)):
    A = f'{WF}/data/domain_{name}/attributes/elevation/dem/domain_{name}_'
    def old(k):
        with tempfile.TemporaryDirectory() as t:
            reproject_to_utm(A + f'{k}_elv.tif', f'{t}/x.tif', 32606)
            with rasterio.open(f'{t}/x.tif') as s: return s.read(1).astype(float)
    So, Bo = old('glacier'), old('bedrock')
    with rasterio.open(f'{sys.argv[1]}/gr_{name.lower()}/domain_{name}_glacier_elv_utm.tif') as s: Sn, tr = s.read(1).astype(float), s.transform
    with rasterio.open(f'{sys.argv[1]}/gr_{name.lower()}/domain_{name}_bedrock_elv_utm.tif') as s: Bn = s.read(1).astype(float)
    on = geometry_mask(list(u[(u.Glacier == gl) & (u.Year == year)].geometry), Sn.shape, tr, invert=True)
    Ho, Hn = (So - Bo)[on], (Sn - Bn)[on]; Z = np.floor((Sn[on] - dz) / 100) * 100
    print(f'\n{name} {year} outline: volume old {Ho.sum()*51**2/1e9:.3f} km3, new {Hn.sum()*51**2/1e9:.3f}')
    print(' band   km2  old H  new H  bed change')
    for z in np.unique(Z):
        k = Z == z
        if k.sum() * 51**2 / 1e6 >= 0.1:
            print(f' {z:5.0f} {k.sum()*51**2/1e6:5.2f} {np.median(Ho[k]):6.1f} {np.median(Hn[k]):6.1f} {np.median((Bn[on]-Bo[on])[k]):+8.1f}')
