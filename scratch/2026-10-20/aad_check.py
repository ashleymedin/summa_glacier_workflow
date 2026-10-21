"""USGS AAD rows against each survey outline binned on the start survey's DEM, and the model cold state's bands."""
import numpy as np, pandas as pd, geopandas as gpd, rasterio, rasterio.mask, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
for name, dem, y0, ys, case in (('Gulkana', 'Deltas_20070811_DEM', 2007, (2007, 2016, 2021), 'gulkana_corrected'),
                                ('Wolverine', 'EasternKenai_20060808_DEM', 2006, (2006, 2016, 2020), 'wolverine_corrected')):
    aad = pd.read_csv(f'{WF}/data/domain_{name}/USGSweatherData/{name}/Input_{name}_Area_Altitude_Distribution.csv', index_col='Year')
    c = aad.columns.astype(float)
    out = {}
    with rasterio.open(f'{WF}/GlacierDEM/{dem}/{dem}.tif') as src:
        px = abs(src.res[0] * src.res[1]) / 1e6
        for y in ys:
            g = u[(u.Glacier == f'{name} Glacier') & (u.Year == y)].to_crs(src.crs)
            z, _ = rasterio.mask.mask(src, g.geometry, crop=True, filled=False)
            z = z.compressed(); z = z[z > 0]
            out[f'usgs_{y}'] = aad.loc[y].values
            out[f'outline{y}_on_dem{y0}'] = [((z >= b - 50) & (z < b + 50)).sum() * px for b in c]
    ins = f'{WF}/runs/{case}/summa_inputs_flow'
    with nc4.Dataset(f'{ins}/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float); nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
        dx = float(np.asarray(d['dx'][:]).flat[0])
    g = int(np.argmax(nx * ny))
    with nc4.Dataset(f'{ins}/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]
    s = s0[(s0 - bed[:ny[g], :nx[g], g]) > 0.1]
    out['model_cold'] = [((s >= b - 50) & (s < b + 50)).sum() * dx * dx / 1e6 for b in c]
    t = pd.DataFrame(out, index=c.astype(int)); t.loc['total'] = t.sum()
    print(name); print(t.round(3).to_string())
