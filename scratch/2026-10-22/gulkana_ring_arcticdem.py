"""Gulkana: ArcticDEM 2 m strip heights over each strip USGS dropped between outlines, relative to stable ground.
Debris-covered ice left out of an outline keeps lowering; ground whose ice melted out does not."""
import json, ssl, sys, urllib.request
import certifi
import numpy as np, geopandas as gpd, rasterio, rasterio.mask
from rasterio.windows import Window, from_bounds
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
OUT = f'{WF}/scratch/2026-10-22/gulkana_ring_arcticdem.npz'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
g = u[u.Glacier == 'Gulkana Glacier'].to_crs(3413).set_index('Year').geometry
from shapely.geometry import box as sbox
tongue = gpd.GeoSeries([sbox(577300, 7014000, 580300, 7017600)], crs=32606).to_crs(3413).iloc[0].envelope  # UTM 6N
zones = {f'{a}-{b}': g[a].difference(g[b]).intersection(tongue) for a, b in ((1993, 2005), (2005, 2014), (2014, 2016), (2016, 2021))}
zones['2021 ice'] = g[2021].intersection(tongue)
stable = tongue.difference(g[1957].buffer(100))
zones['stable'] = stable
box = tuple(2 * round(b / 2) for b in tongue.bounds)  # on the 2 m strip grid

q = dict(collections=['arcticdem-strips-s2s041-2m'], bbox=list(gpd.GeoSeries([tongue], crs=3413).to_crs(4326).total_bounds), limit=200)
req = urllib.request.Request('https://stac.pgc.umn.edu/api/v1/search', json.dumps(q).encode(), {'Content-Type': 'application/json'})
items = json.load(urllib.request.urlopen(req, context=ssl.create_default_context(cafile=certifi.where())))['features']
items = [i for i in items if int(i['properties']['datetime'][5:7]) in (8, 9)]  # snow-free season
items = list({i['properties']['datetime'][:4]: i for i in sorted(items, key=lambda i: i['properties']['datetime'])}.values())  # latest each year
rows = []
for it in sorted(items, key=lambda i: i['properties']['datetime']):
    href = it['assets']['dem']['href']
    try:
        with rasterio.open(href) as s:
            w = from_bounds(*box, s.transform).round_offsets().round_lengths()
            r0, c0 = int(w.row_off), int(w.col_off)
            ri, ci = max(r0, 0), max(c0, 0)
            rw = Window(ci, ri, min(c0 + w.width, s.width) - ci, min(r0 + w.height, s.height) - ri)
            z = np.full((int(w.height), int(w.width)), np.nan)
            if rw.width > 0 and rw.height > 0:
                a = s.read(1, window=rw).astype(float); a[a == s.nodata] = np.nan
                z[ri - r0:ri - r0 + a.shape[0], ci - c0:ci - c0 + a.shape[1]] = a
            t = s.window_transform(w)
    except Exception as e:
        print(it['id'], 'skip', e, file=sys.stderr); continue
    from rasterio.features import geometry_mask
    med, cov = {}, {}
    for k, geom in zones.items():
        m = ~geometry_mask([geom], z.shape, t)
        v = z[m]; cov[k] = np.isfinite(v).mean() if v.size else 0; med[k] = np.nanmedian(v) if np.isfinite(v).any() else np.nan
    rows.append((it['properties']['datetime'][:10], med, cov))
    np.save(f'{WF}/scratch/2026-10-22/arcticdem/{rows[-1][0]}.npy', z.astype('float32'))
    T = t
    print(rows[-1][0], ' '.join(f'{k}:{med[k] - med["stable"]:7.1f}({cov[k]:.0%})' for k in zones if k != 'stable'), flush=True)
np.savez(OUT, rows=np.array(rows, dtype=object), transform=np.array(T)[:6], allow_pickle=True)
